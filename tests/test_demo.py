# tests/test_demo.py

"""
Tests for the web demo security features:
- Security headers on all responses
- Rate limiting helper
- Session TTL / stale session cleanup
- Max sessions cap
- Routes return expected status codes
"""

import time

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_demo_globals():
    """Reset module-level globals between tests."""
    from web import demo

    demo._sessions.clear()
    demo._rate_limits.clear()
    yield
    demo._sessions.clear()
    demo._rate_limits.clear()


@pytest.fixture
def app():
    from web.demo import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    def test_index_has_security_headers(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp

    def test_api_route_has_security_headers(self, client):
        """Even error responses must carry security headers."""
        response = client.post(
            "/api/start",
            json={},
            content_type="application/json",
        )
        # Will be 400 because of missing fields, but headers should still be set
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_404_has_security_headers(self, client):
        response = client.get("/nonexistent-route")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_within_limit_returns_true(self):
        from web.demo import _check_rate_limit

        assert _check_rate_limit("10.0.0.1") is True

    def test_exceeds_limit_returns_false(self):
        from web.demo import RATE_LIMIT_MAX_REQUESTS, _check_rate_limit

        ip = "10.0.0.2"
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            assert _check_rate_limit(ip) is True
        # Next request should be blocked
        assert _check_rate_limit(ip) is False

    def test_old_entries_are_pruned(self):
        from web.demo import RATE_LIMIT_MAX_REQUESTS, _check_rate_limit, _rate_limits

        ip = "10.0.0.3"
        # Fill up the limit
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            _check_rate_limit(ip)

        assert _check_rate_limit(ip) is False

        # Backdate all entries beyond the window
        _rate_limits[ip] = [time.time() - 120 for _ in _rate_limits[ip]]

        # Now it should be allowed again
        assert _check_rate_limit(ip) is True

    def test_separate_ips_have_independent_limits(self):
        from web.demo import RATE_LIMIT_MAX_REQUESTS, _check_rate_limit

        ip_a, ip_b = "10.0.0.4", "10.0.0.5"
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            _check_rate_limit(ip_a)
        assert _check_rate_limit(ip_a) is False
        # ip_b should still be allowed
        assert _check_rate_limit(ip_b) is True


# ---------------------------------------------------------------------------
# Session cleanup
# ---------------------------------------------------------------------------


class TestSessionCleanup:
    def test_stale_sessions_are_removed(self):
        from web.demo import SESSION_TTL, _cleanup_stale_sessions, _sessions

        # Create a stale session (started long ago)
        _sessions["old-session"] = {
            "started_at": time.time() - SESSION_TTL - 10,
            "stop_requested": False,
        }
        # Create a fresh session
        _sessions["new-session"] = {
            "started_at": time.time(),
            "stop_requested": False,
        }

        _cleanup_stale_sessions()

        assert "old-session" not in _sessions
        assert "new-session" in _sessions

    def test_stale_session_gets_stop_requested(self):
        from web.demo import SESSION_TTL, _cleanup_stale_sessions, _sessions

        session_data = {
            "started_at": time.time() - SESSION_TTL - 1,
            "stop_requested": False,
        }
        _sessions["doomed"] = session_data

        _cleanup_stale_sessions()

        # Session was popped and stop_requested was set before removal
        assert "doomed" not in _sessions
        assert session_data["stop_requested"] is True

    def test_fresh_sessions_not_removed(self):
        from web.demo import _cleanup_stale_sessions, _sessions

        _sessions["fresh"] = {
            "started_at": time.time(),
            "stop_requested": False,
        }

        _cleanup_stale_sessions()

        assert "fresh" in _sessions


# ---------------------------------------------------------------------------
# Max sessions cap (tested via /api/start route)
# ---------------------------------------------------------------------------


class TestMaxSessions:
    def test_start_rejected_when_max_sessions_reached(self, client):
        from web.demo import MAX_SESSIONS, _sessions

        # Fill up to max
        for i in range(MAX_SESSIONS):
            _sessions[f"sess-{i}"] = {"started_at": time.time()}

        response = client.post(
            "/api/start",
            json={
                "agent1": "chatgpt",
                "agent2": "gemini",
                "topic": "test",
            },
            content_type="application/json",
        )
        assert response.status_code == 503
        data = response.get_json()
        assert "capacity" in data.get("error", "").lower()


# ---------------------------------------------------------------------------
# Route smoke tests
# ---------------------------------------------------------------------------


class TestRoutes:
    def test_index_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_start_missing_fields_returns_400(self, client):
        response = client.post(
            "/api/start",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_stop_unknown_session_returns_404(self, client):
        response = client.post("/api/stop/nonexistent-id")
        assert response.status_code == 404
