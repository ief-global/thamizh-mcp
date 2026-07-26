# THAMIZH MCP — container for the web/REST head and the MCP server (see thamizh-mcp-hosting-plan.md).
#   docker build -t thamizh-mcp .
#   docker run --rm -p 8080:8080 thamizh-mcp           # web UI  → http://localhost:8080
#   docker run --rm -i thamizh-mcp thamizh-mcp         # MCP server over stdio
FROM python:3.12-slim

# `foma` — NOT `foma-bin`, which is an empty transitional package (see CLAUDE.md gotchas).
RUN apt-get update && apt-get install -y --no-install-recommends foma \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system --no-cache ".[web]"

# Pinned anchor data: FST models, equivalents lists, curated paradigms (pins in data/PINS.md).
COPY data ./data
COPY schemas ./schemas

ENV THAMIZH_WEB_HOST=0.0.0.0 THAMIZH_WEB_PORT=8080
EXPOSE 8080
CMD ["thamizh-web"]
