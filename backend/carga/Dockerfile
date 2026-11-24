FROM python:3.13.9-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY carga ./carga
# O nome do banco e do papel da auditoria e os desfechos aceitos vêm do módulo `auditoria`, que
# depende de `acesso` e `consultas`.
COPY acesso ./acesso
COPY auditoria ./auditoria
COPY consultas ./consultas

CMD ["python", "-m", "carga"]
