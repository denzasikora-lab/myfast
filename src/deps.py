from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Header, HTTPException, status
from src.db import get_session, async_session_maker
from src.services import PaymentService
from src.uow import UnitOfWork
from src.settings import get_settings

settings = get_settings()
SessionDep = Annotated[AsyncSession, Depends(get_session)]

def get_uow() -> UnitOfWork:
    return UnitOfWork(async_session_maker)

def get_payment_service(uow: UnitOfWork = Depends(get_uow)) -> PaymentService:
    return PaymentService(uow)

async def require_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )