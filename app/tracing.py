import logging
from contextlib import nullcontext
from typing import Any

import mlflow

logger = logging.getLogger(__name__)

_tracing_enabled = False


def setup_tracing(tracking_uri: str, experiment_name: str) -> None:
    """Configure MLflow and enable autologging for all LLM providers."""
    global _tracing_enabled
    mlflow.set_tracking_uri(tracking_uri)
    if experiment_name:
        mlflow.set_experiment(experiment_name)
    mlflow.anthropic.autolog()
    mlflow.openai.autolog()
    _tracing_enabled = True
    logger.info("MLflow tracing enabled (tracking URI: %s)", tracking_uri)


def span(name: str, attributes: dict[str, Any] | None = None):
    """Return an MLflow span context manager, or a no-op if tracing is disabled."""
    if not _tracing_enabled:
        return nullcontext()
    return mlflow.start_span(name, attributes=attributes)
