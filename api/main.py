"""Run: python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log"""
import logging
import sqlite3
from time import monotonic
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from citizen.config import database_path
from citizen.database import Registry, NewMatchesError, DuplicatePhoneError
from citizen.service import duplicate_response
from .models import CustomerInput, DuplicateResult, RegistrationResult
from .security import require_api_key

logger = logging.getLogger("citizen.api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
MAX_BODY_BYTES = 8192
ROUTES = {"/api/v1/health", "/api/v1/duplicates/check", "/api/v1/customers/register", "/docs", "/openapi.json", "/docs/oauth2-redirect"}


class RequestBoundary:
    """Limit actual streamed bytes, not just Content-Length. Never log inputs."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        start, status = monotonic(), 500
        path = scope.get("path", "")
        method = scope.get("method", "")
        async def tracked_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] += [(b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff")]
            await send(message)
        try:
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    return await JSONResponse({"detail": "Request body exceeds 8192 bytes."}, 413)(scope, receive, tracked_send)
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()
            await self.app(scope, replay, tracked_send)
        finally:
            logger.info("method=%s route=%s status=%s duration_ms=%s",
                        method if method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "other",
                        path if path in ROUTES else "unmatched", status, round((monotonic()-start)*1000))


def create_app(db_path=None):
    app = FastAPI(title="CitizenCheck local API", version="1.0.0", redoc_url=None)
    app.add_middleware(RequestBoundary)

    def registry():
        return Registry(db_path if db_path is not None else database_path())

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # Pydantic's default errors can echo raw names, addresses or a malformed body.
        return JSONResponse({"detail": "Invalid request. Supply full_name, dob (YYYY-MM-DD), phone and address as valid strings; no extra fields."}, 422)

    @app.exception_handler(ValueError)
    async def invalid_values(request: Request, exc: ValueError):
        return JSONResponse({"detail": "Invalid customer details."}, 422)

    @app.exception_handler(sqlite3.Error)
    @app.exception_handler(OSError)
    async def unavailable(request: Request, exc: Exception):
        return JSONResponse({"detail": "Registry temporarily unavailable. No success is confirmed; retry after checking service status."}, 503)

    @app.get("/api/v1/health")
    def health():
        # Liveness only, not an authentication or database-readiness probe.
        return {"status": "ok", "service": "citizencheck", "version": "1.0.0"}

    @app.post("/api/v1/duplicates/check", response_model=DuplicateResult, dependencies=[Depends(require_api_key)])
    def check(customer: CustomerInput):
        store = registry()
        result = duplicate_response(store.check(customer.model_dump()))
        result["phone_number_exists"] = store.phone_exists(customer.phone)
        if result["phone_number_exists"]:
            result["recommended_next_step"] = "review"
        return result

    @app.post("/api/v1/customers/register", response_model=RegistrationResult, responses={201: {"model": RegistrationResult}, 409: {"model": RegistrationResult}}, dependencies=[Depends(require_api_key)])
    def register(customer: CustomerInput, response: Response):
        try:
            record_id = registry().register(customer.model_dump())
        except DuplicatePhoneError:
            response.status_code = 409
            return {**duplicate_response([]), "status": "phone_duplicate", "detail": "Phone number already exists.",
                    "phone_number_exists": True, "recommended_next_step": "review"}
        except NewMatchesError as exc:
            response.status_code = 409
            return {**duplicate_response(exc.matches), "status": "review_required", "record_id": None}
        response.status_code = 201
        return {**duplicate_response([]), "status": "registered", "record_id": record_id}

    return app


app = create_app()
