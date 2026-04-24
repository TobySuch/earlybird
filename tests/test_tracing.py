from contextlib import nullcontext
from unittest.mock import MagicMock, patch


@patch("mlflow.openai.autolog")
@patch("mlflow.anthropic.autolog")
@patch("mlflow.set_experiment")
@patch("mlflow.set_tracking_uri")
def test_setup_tracing_configures_mlflow(mock_uri, mock_experiment, mock_anthropic, mock_openai):
    from app.tracing import setup_tracing

    setup_tracing("http://localhost:5000", "my-experiment")

    mock_uri.assert_called_once_with("http://localhost:5000")
    mock_experiment.assert_called_once_with("my-experiment")
    mock_anthropic.assert_called_once()
    mock_openai.assert_called_once()


@patch("mlflow.openai.autolog")
@patch("mlflow.anthropic.autolog")
@patch("mlflow.set_experiment")
@patch("mlflow.set_tracking_uri")
def test_setup_tracing_skips_experiment_when_empty(
    mock_uri, mock_experiment, mock_anthropic, mock_openai
):
    from app.tracing import setup_tracing

    setup_tracing("http://localhost:5000", "")

    mock_uri.assert_called_once_with("http://localhost:5000")
    mock_experiment.assert_not_called()
    mock_anthropic.assert_called_once()
    mock_openai.assert_called_once()


@patch("app.tracing.setup_tracing")
def test_setup_tracing_not_called_when_uri_empty(mock_setup, monkeypatch):
    """Tracing setup is skipped entirely when MLFLOW_TRACKING_URI is not configured."""
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "")
    monkeypatch.setenv("MLFLOW_EXPERIMENT_NAME", "")

    # Re-import settings with cleared cache so monkeypatched env is picked up

    import app.config as config_module

    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.mlflow_tracking_uri == ""
    mock_setup.assert_not_called()

    config_module.get_settings.cache_clear()


def test_span_returns_nullcontext_when_tracing_disabled():
    import app.tracing as tracing_module

    tracing_module._tracing_enabled = False
    ctx = tracing_module.span("test_span")
    assert isinstance(ctx, type(nullcontext()))


@patch("mlflow.start_span")
def test_span_returns_mlflow_span_when_tracing_enabled(mock_start_span):
    import app.tracing as tracing_module

    tracing_module._tracing_enabled = True
    mock_span = MagicMock()
    mock_start_span.return_value = mock_span

    ctx = tracing_module.span("test_span", attributes={"key": "value"})

    mock_start_span.assert_called_once_with("test_span", attributes={"key": "value"}, inputs=None)
    assert ctx is mock_span

    tracing_module._tracing_enabled = False  # restore


@patch("mlflow.start_span")
def test_span_passes_inputs_to_mlflow(mock_start_span):
    import app.tracing as tracing_module

    tracing_module._tracing_enabled = True
    mock_span = MagicMock()
    mock_start_span.return_value = mock_span

    ctx = tracing_module.span("test_span", inputs={"key": "value"})

    mock_start_span.assert_called_once_with("test_span", attributes=None, inputs={"key": "value"})
    assert ctx is mock_span

    tracing_module._tracing_enabled = False  # restore
