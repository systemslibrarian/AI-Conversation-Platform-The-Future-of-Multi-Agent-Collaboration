from core.common import add_jitter, mask_api_key, sanitize_content, simple_similarity


def test_mask_api_key():
    s = "here is a key sk-ant-12345678901234567890 and another sk-abcdefghijklmnopqrstu"
    m = mask_api_key(s)
    assert "[ANTHROPIC_KEY]" in m or "[OPENAI_KEY]" in m


def test_sanitize_content():
    val = "<div><script>evil()</script>ok</div>"
    cleaned = sanitize_content(val)
    assert "[FILTERED]" in cleaned


def test_simple_similarity_range():
    v = simple_similarity("hello world", "hello brave new world")
    assert 0.0 <= v <= 1.0


def test_add_jitter_nonnegative():
    assert add_jitter(1.0) > 0.0
