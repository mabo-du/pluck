FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git make && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy BOTH source files — gh_install.py is just `from pluck import *`,
# so pluck.py MUST be present or `pip install -e .` fails to find the
# `pluck` module declared in pyproject.toml's py-modules list.
COPY src/pluck.py src/gh_install.py /app/src/
COPY pyproject.toml /app/
COPY README.md /app/
COPY LICENSE /app/

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["pluck"]
CMD ["help"]
