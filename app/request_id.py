import logging
import time
import uuid

from fastapi import Request


async def request_id_middleware(request: Request, call_next):
    logger = logging.getLogger("app.request")
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    service_id = getattr(request.state, "service_id", None)
    service = getattr(request.state, "service", None)
    service_name = getattr(service, "name", None) if service else None
    logger.info(
        "%s %s %s %.2fms request_id=%s service_id=%s service_name=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
        service_id,
        service_name,
    )
    return response
