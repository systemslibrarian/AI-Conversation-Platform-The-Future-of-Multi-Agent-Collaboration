# tests/test_view_conversation.py

"""
Tests for view_conversation.py:
- Parameterized SQL queries (no SQL injection via limit)
- view_conversation() and view_summary() output
- Missing database handling
"""

import sqlite3

import pytest

from view_conversation import view_conversation, view_summary

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_db(tmp_path):
    """Create a minimal SQLite DB matching the app schema."""
    db_path = tmp_path / "test_conversation.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE messages ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  sender TEXT NOT NULL,"
        "  content TEXT NOT NULL,"
        "  timestamp TEXT DEFAULT (datetime('now'))"
        ")"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS metadata ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT"
        ")"
    )

    # Insert sample messages
    messages = [
        ("ChatGPT", "Hello, let's discuss AI safety."),
        ("Claude", "Great topic! AI safety is crucial."),
        ("ChatGPT", "I agree. Let's start with alignment."),
        ("Claude", "Alignment is a key challenge."),
        ("ChatGPT", "What about interpretability?"),
    ]
    for sender, content in messages:
        cursor.execute(
            "INSERT INTO messages (sender, content) VALUES (?, ?)",
            (sender, content),
        )

    cursor.execute(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        ("termination_reason", "max_turns_reached"),
    )
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def empty_db(tmp_path):
    """Create a DB with the schema but no messages."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE messages ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  sender TEXT NOT NULL,"
        "  content TEXT NOT NULL,"
        "  timestamp TEXT DEFAULT (datetime('now'))"
        ")"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS metadata ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT"
        ")"
    )
    conn.commit()
    conn.close()
    return str(db_path)


# ---------------------------------------------------------------------------
# view_conversation tests
# ---------------------------------------------------------------------------

class TestViewConversation:
    def test_displays_all_messages(self, sample_db, capsys):
        view_conversation(db_path=sample_db)
        captured = capsys.readouterr()
        assert "5 of 5 total" in captured.out
        assert "AI safety" in captured.out
        assert "interpretability" in captured.out

    def test_limit_restricts_output(self, sample_db, capsys):
        view_conversation(db_path=sample_db, limit=2)
        captured = capsys.readouterr()
        assert "2 of 5 total" in captured.out
        # Should show the first 2 messages
        assert "AI safety" in captured.out

    def test_parameterized_limit_prevents_injection(self, sample_db):
        """
        Passing a non-integer limit must raise an error (int() cast),
        NOT be interpolated into SQL.
        """
        with pytest.raises((ValueError, TypeError)):
            view_conversation(db_path=sample_db, limit="1; DROP TABLE messages;--")

    def test_missing_db_prints_error(self, capsys):
        view_conversation(db_path="/nonexistent/path/db.sqlite")
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "❌" in captured.out

    def test_empty_db_prints_no_messages(self, empty_db, capsys):
        view_conversation(db_path=empty_db)
        captured = capsys.readouterr()
        assert "No messages found" in captured.out

    def test_shows_termination_reason(self, sample_db, capsys):
        view_conversation(db_path=sample_db)
        captured = capsys.readouterr()
        assert "max_turns_reached" in captured.out


# ---------------------------------------------------------------------------
# view_summary tests
# ---------------------------------------------------------------------------

class TestViewSummary:
    def test_displays_summary_stats(self, sample_db, capsys):
        view_summary(db_path=sample_db)
        captured = capsys.readouterr()
        assert "CONVERSATION SUMMARY" in captured.out
        assert "ChatGPT" in captured.out
        assert "Claude" in captured.out
        # Should show message counts
        assert "3 messages" in captured.out  # ChatGPT has 3
        assert "2 messages" in captured.out  # Claude has 2

    def test_shows_termination_status(self, sample_db, capsys):
        view_summary(db_path=sample_db)
        captured = capsys.readouterr()
        assert "max_turns_reached" in captured.out

    def test_missing_db_prints_error(self, capsys):
        view_summary(db_path="/nonexistent/path/db.sqlite")
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "❌" in captured.out

    def test_in_progress_when_no_termination(self, empty_db, capsys):
        """DB without termination_reason should show 'In progress'."""
        # Add a message so we don't hit the "no messages" branch
        conn = sqlite3.connect(empty_db)
        conn.execute(
            "INSERT INTO messages (sender, content) VALUES (?, ?)",
            ("Agent", "Hello"),
        )
        conn.commit()
        conn.close()

        view_summary(db_path=empty_db)
        captured = capsys.readouterr()
        assert "In progress" in captured.out
