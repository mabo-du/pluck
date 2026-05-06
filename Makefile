# Makefile for gh-install development and installation
# SPDX-License-Identifier: MIT

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
DOCDIR ?= $(PREFIX)/share/man/man1
PYTHON ?= python3

.PHONY: all install uninstall test lint clean

all: test lint

# Install gh-install system-wide
install:
	@echo "Installing gh-install to $(PREFIX)..."
	$(PYTHON) -m pip install -e .
	@echo "Installing man page..."
	@mkdir -p "$(DOCDIR)"
	cp man/gh-install.1 "$(DOCDIR)/"
	@echo "Installed! Run: gh-install help"
	@echo ""
	@echo "Quick test: gh-install doctor"

# Uninstall gh-install
uninstall:
	@echo "Removing gh-install..."
	-$(PYTHON) -m pip uninstall gh-install -y
	-rm -f "$(DOCDIR)/gh-install.1"
	@echo "Done."

# Run test suite
test:
	$(PYTHON) -m pytest tests/ -v

# Run linter
lint:
	ruff check src/ tests/

# Auto-fix lint issues
lint-fix:
	ruff check --fix src/ tests/

# Clean up Python caches and build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache/ .ruff_cache/
	rm -rf .coverage coverage.xml htmlcov/
