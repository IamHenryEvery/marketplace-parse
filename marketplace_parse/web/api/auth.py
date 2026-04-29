from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select

from marketplace_parse.core.security import hash_password, verify_password
from marketplace_parse.db.enums import UserRole
from marketplace_parse.db.models import User
from marketplace_parse.db.session import async_session_maker
from marketplace_parse.web.api.deps import templates


router = APIRouter()


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register")
async def register(request: Request) -> Response:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    if not email or not password:
        return templates.TemplateResponse(
            request, "register.html",
            {"error": "Email и пароль обязательны."},
            status_code=400,
        )
    async with async_session_maker() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            return templates.TemplateResponse(
                request, "register.html",
                {"error": "Этот email уже занят."},
                status_code=400,
            )
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.user,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        request.session["user_id"] = user.user_id
    return RedirectResponse("/", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login(request: Request) -> Response:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Неверный email или пароль."},
            status_code=400,
        )
    request.session["user_id"] = user.user_id
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
async def logout(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
