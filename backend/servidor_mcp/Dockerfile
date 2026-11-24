FROM python:3.13.9-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY acesso ./acesso
COPY consultas ./consultas
COPY servidor_mcp ./servidor_mcp

EXPOSE 8001
CMD ["python", "-m", "servidor_mcp"]
