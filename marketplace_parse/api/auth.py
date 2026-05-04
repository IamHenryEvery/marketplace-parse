"""Auth: register, login, logout, /me, scheduler toggle."""
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select

from marketplace_parse.api.deps import CurrentUser
from marketplace_parse.api.schemas import (
    LoginRequest,
    RegisterRequest,
    SchedulerToggleResponse,
    UserOut,
)
from marketplace_parse.core.security import hash_password, verify_password
from marketplace_parse.db.enums import UserRole
from marketplace_parse.db.models import User
from marketplace_parse.db.session import async_session_maker


router = APIRouter()


@router.post("/auth/register", response_model=UserOut)
async def register(body: RegisterRequest, request: Request) -> UserOut:
    email = body.email.strip().lower()
    async with async_session_maker() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Этот email уже занят")
        user = User(
            email=email,
            password_hash=hash_password(body.password),
            role=UserRole.user,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    request.session["user_id"] = user.user_id
    return UserOut.model_validate(user)


@router.post("/auth/login", response_model=UserOut)
async def login(body: LoginRequest, request: Request) -> UserOut:
    email = body.email.strip().lower()
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    request.session["user_id"] = user.user_id
    return UserOut.model_validate(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(user: User = CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/scheduler/toggle", response_model=SchedulerToggleResponse)
async def toggle_scheduler(user: User = CurrentUser) -> SchedulerToggleResponse:
    async with async_session_maker() as session:
        u = await session.get(User, user.user_id)
        u.scheduler_enabled = not u.scheduler_enabled
        await session.commit()
        new_value = u.scheduler_enabled
    return SchedulerToggleResponse(scheduler_enabled=new_value)
