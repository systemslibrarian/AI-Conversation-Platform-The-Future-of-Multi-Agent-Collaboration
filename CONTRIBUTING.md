# Contributing

Thanks for helping improve the AI Conversation Platform!

## Getting Started
1. Clone and create a venv:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```
2. Run tests and lint:
   ```bash
   pytest -q
   ruff check .
   black .
   ```

## Commit Style
- Use conventional commits where possible, e.g., `feat:`, `fix:`, `chore:`.

## Pull Requests
- Include tests for new features and bug fixes.
- Keep PRs focused and small.