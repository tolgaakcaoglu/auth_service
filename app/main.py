from fastapi import FastAPI
import logging
import os
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from contextlib import asynccontextmanager

from . import db
from .api.v1 import auth as auth_router
from .api.v1 import health as health_router
from .limiter import limiter
from .request_id import request_id_middleware
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Başlangıçta veritabanı tablolarını oluştur
    db.init_db()
    yield


app = FastAPI(title="Auth Service", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.middleware("http")(request_id_middleware)
if settings.log_file:
    log_dir = os.path.dirname(settings.log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
handlers = [
    logging.StreamHandler(),
    logging.FileHandler(settings.log_file) if settings.log_file else None,
]
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s %(name)s %(message)s",
    handlers=[handler for handler in handlers if handler is not None],
)

# API router'larını kaydet
app.include_router(auth_router.router)
app.include_router(health_router.router)
