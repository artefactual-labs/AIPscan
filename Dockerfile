FROM ghcr.io/astral-sh/uv:trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_PYTHON_PREFERENCE=only-managed
COPY .python-version .
RUN uv python install
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM node:22 AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm clean-install
COPY . .
RUN npx vite build -c build_config/base.config.js && \
    npx vite build -c build_config/report_base.config.js && \
    npx vite build -c build_config/chart_formats_count.config.js && \
    npx vite build -c build_config/plot_formats_count.config.js && \
    cp node_modules/plotly.js-dist/plotly.js AIPscan/static/dist/plot_formats_count

FROM debian:trixie-slim
COPY --from=builder --chown=python:python /python /python
COPY --from=builder --chown=app:app /app /app
COPY --from=frontend --chown=app:app /app/AIPscan/static/dist /app/AIPscan/static/dist
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY .init-scripts/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
