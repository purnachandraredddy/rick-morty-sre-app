"""Prometheus metrics for monitoring."""
import time
from functools import wraps
from typing import Any, Callable

import structlog
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

from app.config import settings

logger = structlog.get_logger()

# Application info
app_info = Info("app_info", "Application information")
app_info.info(
    {
        "name": settings.app_name,
        "version": settings.app_version,
    }
)

# Request metrics
request_count = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

request_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

# Rick and Morty API metrics
rick_morty_api_requests = Counter(
    "rick_morty_api_requests_total",
    "Total number of requests to Rick and Morty API",
    ["endpoint", "status"],
)

rick_morty_api_duration = Histogram(
    "rick_morty_api_request_duration_seconds",
    "Rick and Morty API request duration in seconds",
    ["endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

rick_morty_api_errors = Counter(
    "rick_morty_api_errors_total",
    "Total number of Rick and Morty API errors",
    ["endpoint", "error_type"],
)

# Database metrics
database_connections = Gauge(
    "database_connections_active", "Number of active database connections"
)

database_query_duration = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

database_errors = Counter(
    "database_errors_total",
    "Total number of database errors",
    ["operation", "error_type"],
)

# Cache metrics
cache_hits = Counter(
    "cache_hits_total", "Total number of cache hits", ["cache_key_pattern"]
)

cache_misses = Counter(
    "cache_misses_total", "Total number of cache misses", ["cache_key_pattern"]
)

cache_operations = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    ["operation", "status"],
)

cache_duration = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
)

# Business metrics
characters_processed = Counter(
    "characters_processed_total", "Total number of characters processed", ["source"]
)

characters_in_database = Gauge(
    "characters_in_database", "Number of characters currently in database"
)

api_sync_duration = Histogram(
    "api_sync_duration_seconds",
    "Duration of API sync operations",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
)

api_sync_errors = Counter(
    "api_sync_errors_total", "Total number of API sync errors", ["error_type"]
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["service"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total number of circuit breaker failures",
    ["service"],
)


def track_request_metrics(func: Callable) -> Callable:
    """Decorator to track HTTP request metrics."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request info
        request = kwargs.get("request") or (args[0] if args else None)
        if not request:
            return await func(*args, **kwargs)

        method = request.method
        endpoint = request.url.path

        # Track request in progress
        request_in_progress.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        status_code = 200

        try:
            response = await func(*args, **kwargs)
            if hasattr(response, "status_code"):
                status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            logger.error("Request failed", endpoint=endpoint, error=str(e))
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            request_count.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()
            request_duration.labels(method=method, endpoint=endpoint).observe(duration)
            request_in_progress.labels(method=method, endpoint=endpoint).dec()

    return wrapper


def track_database_operation(operation: str):
    """Decorator to track database operation metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                database_query_duration.labels(operation=operation).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                database_query_duration.labels(operation=operation).observe(duration)
                database_errors.labels(
                    operation=operation, error_type=type(e).__name__
                ).inc()
                raise

        return wrapper

    return decorator


def track_cache_operation(operation: str):
    """Decorator to track cache operation metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                cache_duration.labels(operation=operation).observe(duration)
                cache_operations.labels(operation=operation, status=status).inc()
                return result
            except Exception as e:
                status = "error"
                duration = time.time() - start_time
                cache_duration.labels(operation=operation).observe(duration)
                cache_operations.labels(operation=operation, status=status).inc()
                raise

        return wrapper

    return decorator


def track_rick_morty_api_call(endpoint: str):
    """Decorator to track Rick and Morty API calls."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                rick_morty_api_duration.labels(endpoint=endpoint).observe(duration)
                rick_morty_api_requests.labels(endpoint=endpoint, status=status).inc()
                return result
            except Exception as e:
                status = "error"
                duration = time.time() - start_time
                rick_morty_api_duration.labels(endpoint=endpoint).observe(duration)
                rick_morty_api_requests.labels(endpoint=endpoint, status=status).inc()
                rick_morty_api_errors.labels(
                    endpoint=endpoint, error_type=type(e).__name__
                ).inc()
                raise

        return wrapper

    return decorator


async def get_metrics() -> tuple[str, str]:
    """Get Prometheus metrics in text format."""
    try:
        metrics_data = generate_latest()
        return metrics_data.decode("utf-8"), CONTENT_TYPE_LATEST
    except Exception as e:
        logger.error("Failed to generate metrics", error=str(e))
        return "# Error generating metrics\n", "text/plain"


def update_business_metrics(characters_count: int):
    """Update business-specific metrics."""
    characters_in_database.set(characters_count)
