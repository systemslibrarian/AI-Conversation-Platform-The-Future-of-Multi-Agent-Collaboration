# Contributing to AI Conversation Platform

Thank you for your interest in contributing to the AI Conversation Platform! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Testing Requirements](#testing-requirements)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

**Positive behaviors include:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors include:**
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of unacceptable behavior may be reported to the project team. All complaints will be reviewed and investigated promptly and fairly.

---

## Getting Started

### Prerequisites

1. **Python 3.11+** installed
2. **Git** for version control
3. **API keys** for at least one AI provider (for testing)
4. **Redis** (optional, for Redis queue tests)

### Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-conversation-platform.git
cd ai-conversation-platform

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/ai-conversation-platform.git
```

### Set Up Development Environment

```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install --system -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov ruff pre-commit bandit mypy

# Install pre-commit hooks
pre-commit install

# Set up API keys for testing
export ANTHROPIC_API_KEY="sk-ant-test-..."
export OPENAI_API_KEY="sk-test-..."
```

### Verify Setup

```bash
# Run tests to verify everything works
pytest

# Run linting
ruff check .

# Run formatting
ruff format --check .
```

---

## Development Process

### Branching Strategy

We use a simplified Git flow:

- `main` - Production-ready code
- `develop` - Integration branch (if used)
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical production fixes

### Creating a Feature Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### Making Changes

1. **Write code** following our [style guidelines](#code-style)
2. **Add tests** for new functionality (maintain 90%+ coverage)
3. **Update documentation** if needed
4. **Run tests** locally before committing
5. **Commit changes** with clear messages

### Commit Message Format

Use conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(agents): add support for Anthropic Claude Opus 4.1

Implements support for the new Claude Opus 4.1 model with
improved context window and performance.

Closes #123
```

```
fix(queue): resolve race condition in concurrent writes

Fixed race condition that could occur when multiple agents
write to the SQLite queue simultaneously. Added transaction
locking to ensure data consistency.

Fixes #456
```

```
docs(readme): update installation instructions

Added Docker installation instructions and clarified
environment variable requirements.
```

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Merge upstream main into your branch
git checkout main
git merge upstream/main

# Rebase your feature branch
git checkout feature/your-feature-name
git rebase main
```

---

## Testing Requirements

### Coverage Requirements

- **Minimum coverage**: 70% for all modules
- **Target coverage**: 90%+ for core modules
- **Critical paths**: 95%+ coverage required

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov=core --cov-report=term-missing

# Run specific test file
pytest tests/test_agents.py -v

# Run specific test class
pytest tests/test_agents.py::TestCircuitBreaker -v

# Run with verbose output
pytest -vv
```

### Writing Tests

**Test Structure:**
```python
class TestNewFeature:
    """Test description"""

    @pytest.mark.asyncio
    async def test_feature_basic_functionality(self, mock_queue, logger):
        """Test basic functionality works"""
        # Arrange
        feature = NewFeature(queue=mock_queue, logger=logger)
        
        # Act
        result = await feature.do_something()
        
        # Assert
        assert result is not None
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_feature_error_handling(self, mock_queue, logger):
        """Test error handling"""
        feature = NewFeature(queue=mock_queue, logger=logger)
        
        with pytest.raises(ValueError, match="Invalid input"):
            await feature.do_something(invalid_param=True)
```

**Test Requirements:**
- All new functions/methods must have tests
- Test happy path and error conditions
- Test edge cases and boundary values
- Use mocks for external dependencies
- Write clear, descriptive test names
- Add docstrings to test classes and methods

### Test Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=agents --cov=core --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### CI/CD Testing

All pull requests automatically run:
1. **Ruff linting and formatting**
2. **Full test suite with coverage**
3. **CodeQL security analysis**

Ensure your changes pass CI before requesting review.

---

## Code Style

### Python Style Guide

We follow PEP 8 with Ruff enforcement.

**Key Guidelines:**
- **Line length**: 100 characters (soft limit)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings, single for dict keys when clearer
- **Imports**: Absolute imports, grouped (stdlib, third-party, local)
- **Naming**:
  - Classes: `PascalCase`
  - Functions/methods: `snake_case`
  - Constants: `UPPER_CASE`
  - Private: `_leading_underscore`

### Type Hints

**Always use type hints:**
```python
from typing import List, Dict, Optional, Tuple

def process_messages(
    messages: List[Dict[str, str]],
    max_count: Optional[int] = None
) -> Tuple[str, int]:
    """Process messages and return summary."""
    ...
```

### Docstrings

**Use Google-style docstrings:**
```python
def complex_function(param1: str, param2: int = 0) -> bool:
    """Short description of function.

    Longer description if needed. Explain what the function does,
    any important details, and usage notes.

    Args:
        param1: Description of param1
        param2: Description of param2. Defaults to 0.

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is not an integer

    Examples:
        >>> complex_function("test", 42)
        True
    """
    ...
```

### Code Formatting

**Use Ruff for automatic formatting:**
```bash
# Check formatting
ruff format --check .

# Apply formatting
ruff format .

# Fix linting issues
ruff check . --fix
```

### Import Organization

```python
# Standard library imports
import asyncio
import logging
from typing import List, Dict, Optional

# Third-party imports
import pytest
from anthropic import Anthropic

# Local imports
from agents.base import BaseAgent
from core.queue import QueueInterface
from core.config import config
```

### Async Best Practices

**Use async/await properly:**
```python
# ✓ CORRECT
async def fetch_data():
    result = await some_async_function()
    return result

# ✗ WRONG - Don't mix sync and async
async def bad_function():
    result = some_sync_function()  # Should use run_in_executor
    return result
```

**Use asyncio.gather for concurrent operations:**
```python
# ✓ CORRECT
async def run_agents():
    results = await asyncio.gather(
        agent1.run(),
        agent2.run(),
        return_exceptions=True
    )
    return results
```

---

## Pull Request Process

### Before Submitting

**Checklist:**
- [ ] Code follows style guidelines
- [ ] All tests pass locally
- [ ] New tests added (90%+ coverage maintained)
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow format
- [ ] No merge conflicts with main
- [ ] Pre-commit hooks pass

### Creating a Pull Request

1. **Push your branch:**
```bash
git push origin feature/your-feature-name
```

2. **Create PR on GitHub:**
   - Use a clear, descriptive title
   - Fill out the PR template completely
   - Reference related issues (`Fixes #123`, `Closes #456`)
   - Add appropriate labels

3. **PR Template:**
```markdown
## Description
Brief description of changes

## Motivation and Context
Why is this change needed? What problem does it solve?

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist
- [ ] My code follows the code style of this project
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings

## Screenshots (if applicable)
Add screenshots here

## Related Issues
Fixes #(issue number)
```

### Review Process

**What to expect:**
1. **Automated checks** run (CI/CD pipeline)
2. **Code review** by maintainers (usually within 48 hours)
3. **Feedback** may request changes
4. **Approval** once all checks pass and review is positive
5. **Merge** by maintainers

**Review criteria:**
- Code quality and style
- Test coverage
- Documentation completeness
- No breaking changes (unless discussed)
- Performance implications
- Security considerations

### Responding to Feedback

- **Be respectful** and constructive
- **Address all comments** or explain why not
- **Push updates** to the same branch
- **Request re-review** when ready

### After Merge

```bash
# Update your local repository
git checkout main
git pull upstream main

# Delete feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

---

## Reporting Bugs

### Before Submitting a Bug Report

1. **Check existing issues** - it may already be reported
2. **Test with latest version** - bug may be fixed
3. **Gather information** - logs, error messages, reproduction steps

### Bug Report Template

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. With configuration '...'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Logs/Error Messages**
```
Paste relevant logs here
```

**Environment:**
- OS: [e.g., Ubuntu 22.04, Windows 11]
- Python version: [e.g., 3.11.5]
- Package version: [e.g., 5.0.0]
- Dependencies: [relevant package versions]

**Additional context**
Add any other context about the problem here.
```

### Security Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Instead:
1. Email security@example.com
2. Include detailed description
3. Provide reproduction steps
4. Suggest fixes if possible

We will respond within 48 hours.

---

## Suggesting Enhancements

### Enhancement Template

```markdown
**Is your feature request related to a problem?**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Use cases**
Describe specific use cases for this feature.

**Additional context**
Add any other context or screenshots about the feature request here.

**Are you willing to implement this?**
- [ ] Yes, I can submit a PR
- [ ] No, but I can help with testing
- [ ] No, just suggesting
```

---

## Additional Resources

### Documentation
- [README.md](./README.md) - Project overview
- [TESTING.md](./TESTING.md) - Comprehensive testing guide
- [API Documentation](./docs/API.md) - API reference

### Community
- GitHub Discussions: [Link to discussions]
- Issue Tracker: [Link to issues]
- Project Board: [Link to project board]

### Development Tools
- [Ruff](https://github.com/astral-sh/ruff) - Fast Python linter
- [pytest](https://pytest.org/) - Testing framework
- [pre-commit](https://pre-commit.com/) - Git hook framework
- [mypy](https://mypy.readthedocs.io/) - Static type checker

---

## Recognition
To God be the Glory

Contributors are recognized in:
- [CONTRIBUTORS.md](./CONTRIBUTORS.md) - List of all contributors
- GitHub Insights - Contribution graphs
- Release Notes - Feature credits

Thank you for contributing to the AI Conversation Platform!

---

**Last Updated**: 2025-01-06  
**Version**: 5.0
