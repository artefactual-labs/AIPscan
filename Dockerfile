ARG TARGET=dev

FROM ghcr.io/astral-sh/uv:trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV UV_PYTHON_PREFERENCE=only-managed
ENV HATCH_BUILD_NO_HOOKS=1
ENV SETUPTOOLS_SCM_PRETEND_VERSION=1.0.0dev
COPY .python-version .
RUN uv python install
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --extra server
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra server

FROM node:24 AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm clean-install
COPY . .
RUN npm run build

FROM debian:trixie-slim AS dev
COPY --from=builder --chown=python:python /venv /venv
COPY --from=builder --chown=python:python /python /python
COPY --from=builder --chown=app:app /app /app
COPY --from=frontend --chown=app:app /app/AIPscan/static/dist /app/AIPscan/static/dist
ENV PATH="/venv/bin:$PATH"
WORKDIR /app
COPY .init-scripts/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]

FROM ghcr.io/astral-sh/uv:trixie-slim AS release
ARG WHEEL
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_PREFERENCE=only-managed
RUN --mount=type=bind,source=.python-version,target=/.python-version,ro \
    uv python install
RUN uv venv /venv
ENV PATH="/venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=dist,target=/dist,ro \
    uv pip install /dist/${WHEEL}[server]
COPY .init-scripts/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]

FROM ${TARGET}
