from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.utils.init_db import init_db


def create_application() -> FastAPI:
    allowed_origins = [
        settings.CLIENT_URL,
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ]
    for origin in settings.CORS_ORIGINS_LIST:
        if origin not in allowed_origins:
            allowed_origins.append(origin)
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="AI-powered predictive analytics platform for student retention.",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        auth_limit=settings.AUTH_RATE_LIMIT_REQUESTS,
        auth_window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
        auth_path_prefix=f"{settings.API_PREFIX}/auth",
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS_LIST or ["*"])
    if settings.FORCE_HTTPS:
        app.add_middleware(HTTPSRedirectMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        if settings.APP_ENV.lower() != "production" and settings.RUN_STARTUP_DB_INIT:
            init_db()

    @app.get(f"{settings.API_PREFIX}/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router, prefix=settings.API_PREFIX)
    return app


app = create_application()
