ARG TARGET=dev

# Value comes from .python-version (default avoids InvalidDefaultArgInFrom).
ARG PYTHON_VERSION=3.14

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
ENV FLASK_APP=AIPscan:create_app
WORKDIR /app
COPY .init-scripts/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]

FROM python:${PYTHON_VERSION}-slim-trixie AS release
ARG WHEEL
RUN adduser --disabled-password --gecos "" aipscan
RUN --mount=type=bind,source=dist,target=/dist,ro \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --root-user-action=ignore --compile /dist/${WHEEL}[server]
ENV FLASK_APP=AIPscan:create_app
COPY .init-scripts/entrypoint.sh /
USER aipscan
ENTRYPOINT ["/entrypoint.sh"]

FROM ${TARGET}
