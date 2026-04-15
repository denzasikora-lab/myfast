import asyncio

from fastapi import FastAPI, Depends, status, Header
from contextlib import asynccontextmanager

from src.db import engine, async_session_maker
from src.models import Base
from uuid import UUID
from src.deps import get_payment_service, require_api_key
from src.services import PaymentService
from src.schemas import PaymentCreate, PaymentResponse, PaymentCreateResponse
from src.outbox import OutboxDispatcher
from src.broker import broker


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    for i in range(10):
        try:
            await broker.start()
            break
        except Exception:
            print(f"Rabbit not ready (api), retry {i}...")
            await asyncio.sleep(2)
    else:
        raise RuntimeError("API failed to connect to RabbitMQ")

    dispatcher = OutboxDispatcher(async_session_maker, broker=broker)
    task = asyncio.create_task(dispatcher.start())

    yield

    dispatcher.stop()
    await task

    await broker.close()
    await engine.dispose()


app = FastAPI(title="Payments Async Service", summary="Lunamary", version="0.1.0", lifespan=lifespan)


@app.post("/api/v1/payments",
    response_model=PaymentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)]
)
async def create_payment(
    data: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: PaymentService = Depends(get_payment_service),
):
    payment = await service.create_payment(data, idempotency_key)

    return {
        "payment_id": str(payment.id),
        "status": payment.status,
        "created_at": payment.created_at,
    }


@app.get(
    "/api/v1/payments/{payment_id}",
    response_model=PaymentResponse,
)
async def get_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_payment_service),
):
    payment = await service.get_payment(payment_id)
    return PaymentResponse.model_validate(payment)