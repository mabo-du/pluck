# Contributing to pluck

Thank you for your interest in contributing! This project helps users install software from any git hosting platform with zero friction.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone <YOUR_FORK_URL>`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Install dev dependencies: `pip install pytest ruff`
5. Run tests: `python -m pytest tests/ -v`
6. Run linter: `ruff check src/ tests/`

## Development Workflow

### Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. Run it before committing:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Testing

All changes should include tests. The test suite lives in `tests/`:

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test class
python -m pytest tests/test_gh_install.py::TestParseRepoUrl -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=gh_install --cov-report=term-missing
```

### Adding New Install Methods

To add support for a new install method:

1. Add detection logic to `detect_install_method()` in `src/gh_install.py`
2. Create an `install_<method>()` function that takes `(repo_path, install_dir)` and returns the installed path (or `None` on failure)
3. Wrap subprocess calls in try/except and return `None` on failure
4. Add the method to the `install_funcs` dict in `download_and_install()`
5. Add tests for detection in `tests/test_gh_install.py`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `test:` — Adding or updating tests
- `refactor:` — Code change that neither fixes a bug nor adds a feature
- `chore:` — Maintenance tasks

## Pull Requests

- Reference any related issues in the PR description
- Include a summary of changes
- Ensure all tests pass
- Ensure ruff passes with no errors

## Reporting Issues

When reporting a bug, please include:

- Operating system and version
- Python version
- The GitHub URL that caused the issue (if applicable)
- The full error output
- Steps to reproduce

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
