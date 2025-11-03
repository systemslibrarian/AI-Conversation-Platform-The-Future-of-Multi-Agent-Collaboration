from core import metrics


def test_metrics_record_functions():
    metrics.record_call("Test", "Model")
    metrics.record_latency("Test", "Model", 0.42)
    metrics.record_tokens("Test", "Model", 10, 20)
    metrics.record_error("Test", "api_error")
    metrics.increment_conversations()
    metrics.decrement_conversations()
    assert True
