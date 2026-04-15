from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from src.schemas import PaymentCreate
from src.models import Payment
from uuid import UUID
from fastapi import HTTPException
from src.models import OutboxEvent

class PaymentService:
    def __init__(self, uow):
        self.uow = uow

    async def create_payment(self, data: PaymentCreate, key: str):
        async with self.uow as uow:
            payment = Payment(
                amount=data.amount.quantize(Decimal("0.01")),
                currency=data.currency,
                description=data.description,
                metadata_=data.metadata,
                webhook_url=str(data.webhook_url) if data.webhook_url else None,
                idempotency_key=key,
            )

            try:
                await uow.payments.add(payment)

                event = OutboxEvent(
                    event_type="payment.created",
                    payload={
                        "payment_id": str(payment.id),
                        "amount": str(payment.amount),
                        "currency": payment.currency.value,
                    },
                )
                uow.session.add(event)

                return payment
            except IntegrityError:
                await uow.session.rollback()

                existing = await uow.payments.get_by_idempotency_key(key)
                if existing:
                    return existing
                raise

    async def get_payment(self, payment_id: UUID):
        async with self.uow as uow:
            payment = await uow.payments.get_by_id(payment_id)

            if not payment:
                raise HTTPException(status_code=404, detail="Payment not found")

            return payment