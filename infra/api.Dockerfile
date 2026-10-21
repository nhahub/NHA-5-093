FROM ghcr.io/astral-sh/uv:0.10.10 AS uv
FROM python:3.11.14-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY . .
RUN uv sync --locked --all-packages --no-dev
ENV HG_PROVIDER_MODE=mock HG_DB_URL=sqlite:////data/hireguard.db UV_NO_SYNC=1
ENV PATH="/app/.venv/bin:${PATH}"
RUN useradd --create-home hireguard && mkdir /data && chown hireguard /data
USER hireguard
# M3 registers its approved single-worker command in infra/handoffs.json.
CMD ["/app/.venv/bin/python", "scripts/dev.py", "backend"]
