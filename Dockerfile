ARG TARGET=dev

# Value comes from .python-version (default avoids InvalidDefaultArgInFrom).
ARG PYTHON_VERSION=3.15.0

FROM ghcr.io/astral-sh/uv:0.13.0-trixie-slim AS builder
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

FROM node:26 AS frontend
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

# Keep the runtime dependency versions aligned with the reviewed uv lock.
FROM ghcr.io/astral-sh/uv:0.13.0-trixie-slim@sha256:11bee95ce27982f00acb0c85aa1b5ee6203a9bb958b7def6f27ead851d454e8d AS release-lock
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv export --locked --no-dev --extra server --no-emit-project \
    --output-file /constraints.txt

FROM ghcr.io/astral-sh/uv:0.13.0-trixie-slim@sha256:11bee95ce27982f00acb0c85aa1b5ee6203a9bb958b7def6f27ead851d454e8d AS release
ARG PYTHON_VERSION
ARG WHEEL
ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_LINK_MODE=copy
ENV PATH="/venv/bin:$PATH"
RUN uv python install "${PYTHON_VERSION}" && \
    uv venv --python "${PYTHON_VERSION}" /venv
RUN python -c "import sys; assert sys.version.split()[0] == '${PYTHON_VERSION}'"
RUN apt-get update && \
    apt-get install --no-install-recommends --yes adduser && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --gecos "" aipscan
RUN --mount=type=bind,source=dist,target=/dist,ro \
    --mount=type=bind,from=release-lock,source=/constraints.txt,target=/constraints.txt \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /venv/bin/python --compile-bytecode --require-hashes \
    --requirement /constraints.txt && \
    uv pip install --python /venv/bin/python --compile-bytecode --no-deps /dist/${WHEEL}[server]
ENV FLASK_APP=AIPscan:create_app
COPY .init-scripts/entrypoint.sh /
USER aipscan
ENTRYPOINT ["/entrypoint.sh"]

FROM ${TARGET}
