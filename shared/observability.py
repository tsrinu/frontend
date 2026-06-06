"""Shared observability bootstrap — call init_observability(app, name) from each service.

Adds:
  - Sentry error tracking (only if SENTRY_DSN env is set)
  - Prometheus /metrics endpoint via prometheus-fastapi-instrumentator
  - Structured request logging

Skips gracefully if optional deps aren't installed (lets old deployments still boot).
"""
import os
import logging


def init_observability(app, service_name: str) -> None:
    _setup_logging(service_name)
    _setup_sentry(service_name)
    _setup_prometheus(app, service_name)


def _setup_logging(service_name: str) -> None:
    level = os.getenv("LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=f"%(asctime)s {service_name} %(levelname)s %(name)s: %(message)s",
    )


def _setup_sentry(service_name: str) -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(
            dsn=dsn,
            release=os.getenv("APP_VERSION", "dev"),
            environment=os.getenv("APP_ENV", "production"),
            integrations=[FastApiIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            send_default_pii=False,  # never send IPs, headers, body
            before_send=_scrub_pii,
        )
        sentry_sdk.set_tag("service", service_name)
        logging.getLogger().info("sentry initialised for %s", service_name)
    except ImportError:
        logging.getLogger().warning("sentry-sdk not installed; skipping")


def _scrub_pii(event, hint):
    """Strip emails, tokens, PINs from error events before they leave the box."""
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            for k in list(data.keys()):
                if k.lower() in ("password", "pin", "token", "refreshtoken", "accesstoken",
                                  "idtoken", "code", "_devcode", "secret"):
                    data[k] = "[REDACTED]"
    return event


def _setup_prometheus(app, service_name: str) -> None:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=False,
            excluded_handlers=["/healthz", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logging.getLogger().info("prometheus /metrics exposed for %s", service_name)
    except ImportError:
        logging.getLogger().warning("prometheus-fastapi-instrumentator not installed; skipping")
