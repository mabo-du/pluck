# Makefile for pluck development and installation
# SPDX-License-Identifier: MIT

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
DOCDIR ?= $(PREFIX)/share/man/man1
PYTHON ?= python3

.PHONY: all install uninstall test lint clean

all: test lint

# Install pluck system-wide
install:
	@echo "Installing pluck to $(PREFIX)..."
	$(PYTHON) -m pip install -e .
	@echo "Installing man page..."
	@mkdir -p "$(DOCDIR)"
	cp man/pluck.1 "$(DOCDIR)/"
	@echo "Installed! Run: pluck help"
	@echo ""
	@echo "Quick test: pluck doctor"

# Uninstall pluck
uninstall:
	@echo "Removing pluck..."
	-$(PYTHON) -m pip uninstall pluck -y
	-rm -f "$(DOCDIR)/pluck.1"
	rm -f "$(DOCDIR)/gh-install.1"   # legacy
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
