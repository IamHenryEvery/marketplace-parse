from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from marketplace_parse.core.config import settings
from marketplace_parse.web.api import auth, crud, parsing


STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="marketplace-parse (dev)")
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(crud.router)
app.include_router(parsing.router)
