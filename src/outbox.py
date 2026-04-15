import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.broker import payments_queue, dlq_queue
from src.models import OutboxStatus, OutboxEvent
from src.schemas import PaymentEvent

logger = logging.getLogger(__name__)


class OutboxDispatcher:
    def __init__(self, session_factory: async_sessionmaker, broker) -> None:
        self.session_factory = session_factory
        self.broker = broker
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        while not self._stopped.is_set():
            try:
                async with self.session_factory() as session:

                    result = await session.execute(
                        select(OutboxEvent)
                        .where(
                            OutboxEvent.status == OutboxStatus.pending,
                            OutboxEvent.next_retry_at <= datetime.utcnow(),
                        )
                        .order_by(OutboxEvent.created_at)
                        .limit(50)
                        .with_for_update(skip_locked=True)
                    )

                    rows = result.scalars().all()

                    if not rows:
                        await asyncio.sleep(1)
                        continue

                    for row in rows:
                        try:
                            event = PaymentEvent.model_validate(row.payload)

                            await self.broker.publish(
                                event.model_dump(mode="json"),
                                queue=payments_queue,
                            )

                            row.status = OutboxStatus.sent
                            row.sent_at = datetime.utcnow()

                        except Exception as exc:
                            row.attempts += 1
                            row.last_error = str(exc)

                            if row.attempts >= 3:
                                await self.broker.publish(
                                    row.payload,
                                    queue=dlq_queue,
                                )
                                row.status = OutboxStatus.dlq
                                logger.exception("Outbox moved to DLQ")

                            else:
                                delay = 2 ** row.attempts
                                row.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                                row.status = OutboxStatus.pending
                                logger.exception("Outbox retry scheduled")

                    await session.commit()
            except Exception:
                logger.exception("Outbox dispatcher loop crashed")
                await asyncio.sleep(2)

    def stop(self) -> None:
        self._stopped.set()