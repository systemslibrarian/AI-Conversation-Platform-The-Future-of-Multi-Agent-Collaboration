# Changelog

## [5.0.0] - 2025-11-02
### Added
- Async agents for ChatGPT, Claude, Gemini, Grok, Perplexity
- Prometheus metrics, OpenTelemetry tracing
- Streamlit UI with path validation and sanitization
- Redis/SQLite queue backends, file locking, atomic ops
- CLI starter with deterministic opener seeding

### Fixed
- Health check lock probe for `FileLock`
- Config-driven max message length
- Non-rate error backoff in agent loop
