ARG TARGET=dev

# Value comes from .python-version (default avoids InvalidDefaultArgInFrom).
ARG PYTHON_VERSION=3.14.7

FROM ghcr.io/astral-sh/uv:0.12.21-trixie-slim AS builder
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
FROM ghcr.io/astral-sh/uv:0.12.21-trixie-slim@sha256:0b4686f3d71340b38a02d2b73b17620fe18d5c82c0f1c3c3a59996ed6e8e5b98 AS release-lock
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv export --locked --no-dev --extra server --no-emit-project \
    --output-file /constraints.txt

FROM python:${PYTHON_VERSION}-slim-trixie@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS release
ARG PYTHON_VERSION
ARG WHEEL
RUN python -c "import sys; assert sys.version.split()[0] == '${PYTHON_VERSION}', 'Update the pinned release Python image'"
RUN adduser --disabled-password --gecos "" aipscan
RUN --mount=type=bind,source=dist,target=/dist,ro \
    --mount=type=bind,from=release-lock,source=/constraints.txt,target=/constraints.txt \
    --mount=type=cache,target=/root/.cache/pip \
    pip install --root-user-action=ignore --compile --require-hashes \
    --requirement /constraints.txt && \
    pip install --root-user-action=ignore --compile --no-deps /dist/${WHEEL}[server]
ENV FLASK_APP=AIPscan:create_app
COPY .init-scripts/entrypoint.sh /
USER aipscan
ENTRYPOINT ["/entrypoint.sh"]

FROM ${TARGET}
