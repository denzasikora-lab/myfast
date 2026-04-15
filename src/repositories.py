import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, payment: Payment):
        self.session.add(payment)
        await self.session.flush()  # для id
        return payment

    async def get_all(self):
        result = await self.session.execute(select(Payment))
        return result.scalars().all()

    async def get_by_idempotency_key(self, key: str):
        result = await self.session.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, payment_id: uuid.UUID):
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()