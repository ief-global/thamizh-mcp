# THAMIZH MCP — Cloud Run target (see thamizh-mcp-hosting-plan.md). Stub: build wired in Phase 3.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends foma-bin && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system --no-cache .
# TODO Phase 3: copy pinned FST models + anchor data into /app/data
# Streamable HTTP for remote serving (stdio is the local default)
CMD ["thamizh-mcp"]
