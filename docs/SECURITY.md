# Security Policy

## 🔒 Overview

The AI Conversation Platform takes security seriously. This document outlines our security practices, how to report vulnerabilities, and security best practices for users.

---

## 🚨 Reporting a Vulnerability

### Preferred Method: GitHub Security Advisories

We strongly prefer vulnerability reports through **[GitHub Security Advisories](https://github.com/systemslibrarian/ai-conversation-platform/security/advisories)**:

1. Navigate to the Security tab
2. Click "Report a vulnerability"
3. Fill out the advisory form
4. Submit privately

**Benefits:**
- Private disclosure until patch is ready
- Coordinated disclosure timeline
- Credit in security advisories
- Potential CVE assignment

### Alternative Contact Methods

If GitHub Security Advisories are not suitable:
- **Email**: security@[your-domain] *(Update with your actual email)*
- **PGP Key**: [Link to PGP key] *(Optional but recommended)*

### What to Include

Please provide:
- **Description**: Clear description of the vulnerability
- **Impact**: Potential security impact
- **Steps to Reproduce**: Detailed reproduction steps
- **Proof of Concept**: Code or screenshots (if applicable)
- **Affected Versions**: Which versions are vulnerable
- **Suggested Fix**: If you have ideas (optional)

**Example:**
```
Title: SQL Injection in Queue System
Impact: High - allows arbitrary database access
Affected: v5.0.0
Steps:
1. Create conversation with malicious topic: `"; DROP TABLE messages; --`
2. Topic is not sanitized before SQL query
3. Database tables are dropped
```

### What NOT to Do

- ❌ **Do not** open public GitHub issues for security vulnerabilities
- ❌ **Do not** disclose vulnerabilities publicly before patch
- ❌ **Do not** exploit vulnerabilities beyond proof-of-concept
- ❌ **Do not** access other users' data

---

## ⏱️ Response Timeline

We aim to respond promptly to security reports:

| Stage | Timeline |
|-------|----------|
| **Initial Response** | Within 7 days |
| **Triage & Assessment** | Within 14 days |
| **Fix Development** | Within 30 days (severity dependent) |
| **Patch Release** | Within 45 days (severity dependent) |
| **Public Disclosure** | After patch is released + 7-14 days |

**Note**: Timelines may vary based on:
- Severity (critical issues prioritized)
- Complexity of fix
- Coordination with dependencies

---

## 🎯 Scope

### In Scope

Security issues in the following are **in scope** for reports:

✅ **Core Platform**
- Agent implementations (`agents/`)
- Queue system (`core/queue.py`)
- Configuration handling (`core/config.py`)
- Web UI (`web/app.py`)
- CLI (`cli/`)

✅ **Security Features**
- Path traversal vulnerabilities
- Input validation bypasses
- API key exposure in logs
- Authentication/authorization issues
- XSS in web interface
- SQL injection (SQLite)
- Command injection
- Dependency vulnerabilities

✅ **Infrastructure**
- Docker container security
- GitHub Actions workflow vulnerabilities
- Environment variable leakage

### Out of Scope

The following are **out of scope**:

❌ **External Services**
- Vulnerabilities in AI provider APIs (Anthropic, OpenAI, etc.)
- Third-party dependencies (report to maintainers directly)
- Prometheus, Grafana, Redis vulnerabilities

❌ **Non-Security Issues**
- Feature requests
- Performance issues
- Bugs without security impact
- Documentation errors

❌ **Expected Behavior**
- Rate limiting by AI providers
- API key requirements
- File system permissions (user-controlled)

---

## 🛡️ Security Features

### Current Security Measures

#### 1. **Input Validation**
```python
# Path traversal prevention
def validate_db_path(db_file: str) -> Path:
    allowed_dir = Path(config.DATA_DIR).resolve()
    db_path = Path(db_file).resolve()
    db_path.relative_to(allowed_dir)  # Raises if outside allowed dir
```

#### 2. **Output Sanitization**
```python
# XSS prevention in web UI
import bleach
clean_content = bleach.clean(content, tags=[], attributes={}, strip=True)
```

#### 3. **API Key Management**
- Never logged in plain text
- Pattern-based masking in logs
- Environment variable storage only
- No hardcoded credentials

#### 4. **LLM Guard Integration** (Optional)
- Prompt injection detection
- Harmful content filtering
- Configurable security scanners

#### 5. **Concurrency Control**
- FileLock for SQLite (prevents race conditions)
- Atomic operations in Redis
- Circuit breaker pattern (prevents DoS)

#### 6. **Configuration Validation**
- Pydantic-based validation
- Type checking with mypy
- Range validation for sensitive settings

#### 7. **Rate Limiting**
- Exponential backoff with jitter
- Circuit breaker (5 failures → open)
- Configurable thresholds

---

## 📋 Supported Versions

We provide security updates for the following versions:

| Version | Supported          | End of Life |
| ------- | ------------------ | ----------- |
| 5.0.x   | ✅ Yes             | TBD         |
| 4.x     | ⚠️ Limited (90 days) | 2025-02-01 |
| < 4.0   | ❌ No              | 2024-11-01  |

**Note**: We strongly recommend upgrading to the latest version for security fixes.

---

## 🔐 Security Best Practices

### For Users

#### 1. **API Key Management**
```bash
# ✅ GOOD: Use environment variables
export ANTHROPIC_API_KEY=sk-ant-xxxxx

# ✅ GOOD: Use .env file (never commit!)
echo ".env" >> .gitignore
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-xxxxx
EOF

# ❌ BAD: Hardcode in scripts
api_key = "sk-ant-xxxxx"  # NEVER DO THIS
```

#### 2. **File Permissions**
```bash
# Restrict .env file permissions
chmod 600 .env

# Restrict log directory
chmod 700 logs/

# Restrict database files
chmod 600 *.db
```

#### 3. **Network Security**
```bash
# Use TLS for Redis
REDIS_URL=rediss://localhost:6379/0  # Note: rediss:// not redis://

# Bind Prometheus to localhost only (unless needed externally)
PROMETHEUS_PORT=8000
# Use firewall to restrict access
```

#### 4. **Input Validation**
```python
# Always validate user input
from core.config import config

# ✅ GOOD: Validate file paths
db_path = validate_db_path(user_input)

# ✅ GOOD: Limit message length
if len(message) > config.MAX_MESSAGE_LENGTH:
    raise ValueError("Message too long")
```

#### 5. **Dependency Updates**
```bash
# Keep dependencies updated
uv sync --upgrade

# Check for vulnerabilities
uv run pip-audit

# Or use GitHub Dependabot (already configured)
```

### For Developers

#### 1. **Secure Coding**
```python
# ✅ GOOD: Use parameterized queries
cursor.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))

# ❌ BAD: String interpolation
cursor.execute(f"SELECT * FROM messages WHERE id = {msg_id}")
```

#### 2. **Secrets in Code**
```bash
# Scan for secrets before commit
git secrets --scan

# Use pre-commit hooks
pre-commit install
```

#### 3. **Code Review**
- All changes require review
- Security-sensitive changes require 2 reviews
- Run CI/CD checks before merge

#### 4. **Testing**
```bash
# Test with malicious input
pytest tests/security/

# Fuzz testing (if available)
pytest tests/fuzz/
```

---

## 🏆 Security Hall of Fame

We recognize security researchers who help improve our security:

| Researcher | Vulnerability | Date | Severity |
|------------|---------------|------|----------|
| *Your name could be here!* | - | - | - |

**How to be listed:**
1. Report a valid security vulnerability
2. Follow responsible disclosure
3. Wait for patch to be released
4. Get credited in security advisory and here

---

## 📜 Security Advisories

Published security advisories:

- **None yet** - This is a good thing! 🎉

When published, advisories will be listed at:
https://github.com/systemslibrarian/ai-conversation-platform/security/advisories

---

## 🔍 Security Audits

| Date | Auditor | Scope | Report |
|------|---------|-------|--------|
| 2025-11-03 | Internal | Code review | [Link] |
| TBD | External | Full audit | Planned |

---

## 📞 Contact

- **Security Email**: security@[your-domain] *(Update this)*
- **GitHub Security**: [Security Advisories](https://github.com/systemslibrarian/ai-conversation-platform/security/advisories)
- **General Issues**: [GitHub Issues](https://github.com/systemslibrarian/ai-conversation-platform/issues) (non-security only)
- **Discussions**: [GitHub Discussions](https://github.com/systemslibrarian/ai-conversation-platform/discussions)

---

## 🙏 Acknowledgments

We thank the following for making the platform more secure:

- **Security Community**: For responsible disclosure practices
- **GitHub**: For Security Advisories platform
- **Dependabot**: For automated dependency updates
- **CodeQL**: For static security analysis
- **Contributors**: For security-conscious code reviews

---

## 📚 Additional Resources

### Security Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

### Our Security Practices
- [Architecture](docs/ARCHITECTURE.md) - Security architecture
- [Contributing](CONTRIBUTING.md) - Security in development
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community standards

### Tools We Use
- **Static Analysis**: CodeQL, Ruff, mypy
- **Dependency Scanning**: Dependabot, pip-audit
- **Secret Scanning**: GitHub secret scanning
- **Container Scanning**: Docker Scout (planned)

---

## 📝 Policy Changes

This security policy may be updated from time to time. Major changes will be announced via:
- GitHub Releases
- Security advisories (if relevant)
- CHANGELOG.md

**Last Updated**: 2025-11-03  
**Version**: 5.0.0

---

## ⚖️ Legal

### Responsible Disclosure

We follow **responsible disclosure** practices:
- We will not pursue legal action against researchers who:
  - Follow this policy
  - Make good faith efforts to avoid harm
  - Do not access other users' data
  - Report vulnerabilities promptly

### Safe Harbor

We consider security research conducted under this policy to be:
- Authorized under the Computer Fraud and Abuse Act (CFAA)
- Exempt from DMCA anti-circumvention provisions
- Protected under our Responsible Disclosure policy

**Note**: This safe harbor applies to security research only, not to attacks, denial of service, or data exfiltration.

---

**Thank you for helping keep AI Conversation Platform secure!** 🔒

---

<div align="center">

**To God be the glory**

Made with ❤️ by Paul Clark (@systemslibrarian)

[⬆ Back to Main README](README.md)

</div>
