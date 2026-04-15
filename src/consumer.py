import asyncio
import random
import logging
from datetime import datetime, timezone
import httpx
from src.db import async_session_maker
from src.models import Payment, PaymentStatus
from src.broker import broker, payments_queue, dlq_queue

logger = logging.getLogger(__name__)


@broker.subscriber(payments_queue)
async def process_payment(event: dict):
    await asyncio.sleep(random.randint(2, 5))

    success = random.random() < 0.9

    async with async_session_maker() as session:
        payment = await session.get(Payment, event["payment_id"])

        if not payment:
            return

        if success:
            payment.status = PaymentStatus.succeeded
        else:
            payment.status = PaymentStatus.failed

        payment.processed_at = datetime.now(timezone.utc)

        await session.commit()

        if payment.webhook_url:
            await send_webhook(payment)


async def send_webhook(payment: Payment):
    payload = {
        "payment_id": str(payment.id),
        "status": payment.status,
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(payment.webhook_url, json=payload, timeout=5)
                return
        except Exception:
            await asyncio.sleep(2 ** attempt)

    logger.exception("Webhook failed after retries")


@broker.subscriber(dlq_queue)
async def handle_dlq(event: dict):
    logger.error(f"DLQ event received: {event}")