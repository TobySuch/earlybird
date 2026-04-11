import logging

import mlflow

logger = logging.getLogger(__name__)


def setup_tracing(tracking_uri: str, experiment_name: str) -> None:
    """Configure MLflow and enable autologging for all LLM providers."""
    mlflow.set_tracking_uri(tracking_uri)
    if experiment_name:
        mlflow.set_experiment(experiment_name)
    mlflow.anthropic.autolog()
    mlflow.openai.autolog()
    logger.info("MLflow tracing enabled (tracking URI: %s)", tracking_uri)
