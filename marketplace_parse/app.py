"""FastAPI application entry point.

Run as:
    uv run uvicorn marketplace_parse.app:app --reload

Serves a JSON API under /api/* for the React client at ./client/.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from marketplace_parse.api import admin, analytics, auth, marketplaces, parsing, products
from marketplace_parse.core.config import settings


app = FastAPI(title="marketplace-parse API")

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.add_middleware(
    CORSMiddleware,
    # In dev the React app runs on Vite at :3000 with a /api proxy to :8000,
    # so requests look same-origin to the browser (cookies just work, CORS
    # isn't needed). This config is a safety net for direct fetch from :3000
    # if the proxy is ever bypassed.
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(marketplaces.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(parsing.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
