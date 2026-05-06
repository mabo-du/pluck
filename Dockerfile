FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git make && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/gh_install.py /app/src/
COPY pyproject.toml /app/
COPY README.md /app/
COPY LICENSE /app/

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["gh-install"]
CMD ["help"]
