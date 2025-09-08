"""Distributed tracing configuration with OpenTelemetry."""
import os

import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings

logger = structlog.get_logger()


def setup_tracing(app):
    """Set up distributed tracing for the application."""
    if not settings.tracing_enabled:
        logger.info("Tracing is disabled")
        return

    try:
        # Set up the tracer provider
        resource = Resource(
            attributes={
                SERVICE_NAME: settings.app_name,
                "service.version": settings.app_version,
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            }
        )

        trace.set_tracer_provider(TracerProvider(resource=resource))

        # Configure Jaeger exporter if endpoint is provided
        if settings.jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=settings.jaeger_endpoint.split("://")[1].split(":")[0],
                agent_port=int(settings.jaeger_endpoint.split(":")[-1].split("/")[0]),
            )

            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)

            logger.info("Jaeger tracing configured", endpoint=settings.jaeger_endpoint)
        else:
            logger.warning(
                "Jaeger endpoint not configured, traces will not be exported"
            )

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        # Instrument HTTP client
        HTTPXClientInstrumentor().instrument()

        # Instrument SQLAlchemy (will be applied to our database engine)
        SQLAlchemyInstrumentor().instrument()

        logger.info("Distributed tracing setup completed")

    except Exception as e:
        logger.error("Failed to setup tracing", error=str(e))
        # Don't fail the application if tracing setup fails


def get_tracer():
    """Get the application tracer."""
    return trace.get_tracer(__name__)


def trace_function(operation_name: str):
    """Decorator to trace function calls."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not settings.tracing_enabled:
                return func(*args, **kwargs)

            tracer = get_tracer()
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    # Add function metadata
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    result = func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result

                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("function.error", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


async def trace_async_function(operation_name: str):
    """Decorator to trace async function calls."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not settings.tracing_enabled:
                return await func(*args, **kwargs)

            tracer = get_tracer()
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    # Add function metadata
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)

                    result = await func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result

                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("function.error", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator
