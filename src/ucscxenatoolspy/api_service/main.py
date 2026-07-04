"""FastAPI service for TCGA differential expression, correlation, and survival."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from functools import partial
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from ucscxenatoolspy.api_service.analysis import (
    corr_analysis,
    diff_expr_analysis,
    get_available_cancers,
    survival_analysis,
)

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_csv(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


API_KEYS = set(_env_csv("UCSCXENA_API_KEYS"))
API_KEY_HEADER = os.getenv("UCSCXENA_API_KEY_HEADER", "X-API-Key")
ENABLE_DOCS = _env_bool("UCSCXENA_ENABLE_DOCS", default=True)
TRUST_PROXY_HEADERS = _env_bool("UCSCXENA_TRUST_PROXY_HEADERS", default=False)
ANALYSIS_CONCURRENCY = max(1, _env_int("UCSCXENA_ANALYSIS_CONCURRENCY", 4))
ANALYSIS_TIMEOUT_SECONDS = max(1, _env_int("UCSCXENA_ANALYSIS_TIMEOUT_SECONDS", 120))
CORS_ORIGINS = _env_csv("UCSCXENA_CORS_ORIGINS") or ["*"]
RATE_LIMIT_STORAGE_URI = os.getenv("UCSCXENA_RATE_LIMIT_STORAGE_URI")

_analysis_executor = ThreadPoolExecutor(
    max_workers=ANALYSIS_CONCURRENCY,
    thread_name_prefix="tcga-analysis",
)


def _client_ip(request: Request) -> str:
    """Return the rate-limit identity, optionally honoring trusted proxy headers."""
    if TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_client_ip,
    storage_uri=RATE_LIMIT_STORAGE_URI,
)

app = FastAPI(
    title="TCGA Analysis API",
    description=(
        "Differential expression, gene correlation, and survival analysis "
        "for TCGA cancers using tcga_RSEM_gene_tpm."
    ),
    version="0.1.0",
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = rid
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        logger.info(
            "request_id=%s method=%s path=%s status=%s elapsed_ms=%.1f client=%s",
            rid,
            request.method,
            request.url.path,
            response.status_code,
            (time.monotonic() - started) * 1000,
            _client_ip(request),
        )
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not API_KEYS or request.url.path == "/health":
            return await call_next(request)
        supplied = request.headers.get(API_KEY_HEADER, "")
        if supplied not in API_KEYS:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid API key"},
            )
        return await call_next(request)


app.add_middleware(APIKeyMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*", API_KEY_HEADER],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


GENE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9@._-]{0,29}$"


def GeneQuery(**kwargs):
    """Factory for gene parameter Query with validation."""
    return Query(
        ...,
        min_length=1,
        max_length=30,
        pattern=GENE_PATTERN,
        description="Gene symbol or identifier, e.g. TP53, HER2, 7157, ENSG00000141510",
        **kwargs,
    )


CANCER_QUERY = Query(
    ...,
    min_length=2,
    max_length=10,
    description="TCGA cancer abbreviation, e.g. LUAD, BRCA, KIRC",
)


def _sanitize(error: Exception) -> str:
    """Strip internal details from errors before returning them to clients."""
    msg = str(error)
    msg = re.sub(r"https?://\S+", "[redacted]", msg)
    msg = re.sub(r"after \d+ attempts", "after retries", msg)
    return msg


async def _run_analysis(func: Callable[..., Any], **kwargs: Any) -> Any:
    """Run blocking analysis behind concurrency and wall-time guards."""
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(_analysis_executor, partial(func, **kwargs))
    try:
        return await asyncio.wait_for(future, timeout=ANALYSIS_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise TimeoutError("Analysis timed out") from exc


def _value_error_status(error: ValueError, bad_request_markers: tuple[str, ...]) -> int:
    message = str(error)
    return 400 if any(marker in message for marker in bad_request_markers) else 404


def _error_response(status_code: int, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": _sanitize(error)})


V1 = "/api/v1"


@app.get("/health")
async def health():
    """Health check for container/monitor probes."""
    return {"status": "ok"}


@app.get("/")
@limiter.limit("60/minute")
async def root(request: Request):
    """API information."""
    return {
        "service": "TCGA Analysis API",
        "version": "0.1.0",
        "endpoints": {
            "/api/v1/cancers": "List all available cancer types with sample counts",
            "/api/v1/diff-expr": "Differential expression analysis (gene + cancer)",
            "/api/v1/corr": "Spearman correlation between two genes in primary tumors",
            "/api/v1/survival": "Survival analysis: gene expression vs survival (log-rank)",
        },
        "docs": "/docs" if ENABLE_DOCS else None,
    }


@app.get(f"{V1}/cancers")
@limiter.limit("60/minute")
async def list_cancers(request: Request):
    """Return all available TCGA cancer types with tumor/normal sample counts."""
    cancers = get_available_cancers()
    return {
        "count": len(cancers),
        "cancers": cancers,
    }


@app.get(f"{V1}/diff-expr")
@limiter.limit("10/minute")
async def diff_expr(
    request: Request,
    gene: str = GeneQuery(),
    cancer: str = CANCER_QUERY,
):
    """Differential expression: tumor vs normal."""
    try:
        return await _run_analysis(diff_expr_analysis, gene=gene, cancer=cancer)
    except ValueError as e:
        return _error_response(_value_error_status(e, ("only", "Insufficient")), e)
    except RuntimeError as e:
        return _error_response(404, e)
    except TimeoutError as e:
        return _error_response(504, e)


@app.get(f"{V1}/corr")
@limiter.limit("10/minute")
async def corr(
    request: Request,
    gene1: str = GeneQuery(),
    gene2: str = GeneQuery(),
    cancer: str = CANCER_QUERY,
):
    """Spearman correlation between two genes in primary tumor samples."""
    try:
        return await _run_analysis(corr_analysis, gene1=gene1, gene2=gene2, cancer=cancer)
    except ValueError as e:
        return _error_response(_value_error_status(e, ("Insufficient", "only")), e)
    except RuntimeError as e:
        return _error_response(404, e)
    except TimeoutError as e:
        return _error_response(504, e)


@app.get(f"{V1}/survival")
@limiter.limit("5/minute")
async def survival(
    request: Request,
    gene: str = GeneQuery(),
    cancer: str = CANCER_QUERY,
):
    """Survival analysis: gene expression vs patient survival."""
    try:
        return await _run_analysis(survival_analysis, gene=gene, cancer=cancer)
    except ValueError as e:
        return _error_response(_value_error_status(e, ("only", "Need")), e)
    except RuntimeError as e:
        return _error_response(404, e)
    except TimeoutError as e:
        return _error_response(504, e)


