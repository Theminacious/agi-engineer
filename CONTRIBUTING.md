# Contributing to AGI Engineer

Thank you for your interest in contributing to AGI Engineer! This guide explains how to contribute code, report bugs, and improve documentation.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**: `git clone https://github.com/YOUR-USERNAME/agi-engineer.git`
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Install development dependencies**: `pip install -e ".[dev]"` (when available)

## Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks (when available)
pre-commit install
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_rule_classifier.py

# Run with coverage
pytest tests/ --cov=agent --cov-report=html
```

## Code Style

- Follow **PEP 8** for Python code
- Use type hints where possible
- Add docstrings to functions and classes
- Run `ruff check` to lint your code

## Commit Messages

Use clear, descriptive commit messages:
- ✅ `fix: Handle rate limit edge case in UsageTracker`
- ✅ `feat: Add ESLint support for JavaScript analysis`
- ❌ `fixed stuff`
- ❌ `update`

## Pull Requests

1. **Describe what and why** – explain the changes and motivation
2. **Link related issues** – use `#123` to reference issues
3. **Add tests** – include unit tests for new features
4. **Update docs** – keep README and examples in sync
5. **Keep it focused** – one feature or bug fix per PR

## Reporting Bugs

Open an issue with:
- **Clear title** describing the problem
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Environment** (OS, Python version, etc.)
- **Error messages** or logs

Example:
```
Title: Rate limiter not persisting across runs

Steps:
1. Run `agi_engineer_v3.py . --ai --analyze-only`
2. Run again within 1 minute
3. Expected: rate limit message. Actual: API called again
```

## Documentation

- Update `README.md` for user-facing changes
- Add docstrings for new functions
- Create examples in `examples/` directory for new features

## Release Process

Maintainers will:
1. Update version in `setup.py` (when available)
2. Create release notes
3. Tag commit with version
4. Publish to PyPI (when available)

Thank you for contributing! 🚀
