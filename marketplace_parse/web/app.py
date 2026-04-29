from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from marketplace_parse.core.config import settings
from marketplace_parse.web.api import auth, crud, parsing


app = FastAPI(title="marketplace-parse (dev)")
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

app.include_router(auth.router)
app.include_router(crud.router)
app.include_router(parsing.router)
