ARG TARGET=dev

# Value comes from .python-version (default avoids InvalidDefaultArgInFrom).
ARG PYTHON_VERSION=3.15.1

FROM ghcr.io/astral-sh/uv:0.13.5-trixie-slim AS builder
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
FROM ghcr.io/astral-sh/uv:0.13.5-trixie-slim@sha256:95611d89b7324e0517fe7257bb00979cf1f68461e5fb2b2d027d039da054bc07 AS release-lock
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv export --locked --no-dev --extra server --no-emit-project \
    --output-file /constraints.txt

FROM ghcr.io/astral-sh/uv:0.13.5-trixie-slim@sha256:95611d89b7324e0517fe7257bb00979cf1f68461e5fb2b2d027d039da054bc07 AS release-build
ARG PYTHON_VERSION
ARG WHEEL
ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_LINK_MODE=copy
ENV PATH="/venv/bin:$PATH"
RUN uv python install "${PYTHON_VERSION}" && \
    uv venv --python "${PYTHON_VERSION}" /venv
RUN python -c "import sys; assert sys.version.split()[0] == '${PYTHON_VERSION}'"
RUN --mount=type=bind,source=dist,target=/dist,ro \
    --mount=type=bind,from=release-lock,source=/constraints.txt,target=/constraints.txt \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /venv/bin/python --compile-bytecode --require-hashes \
    --requirement /constraints.txt && \
    uv pip install --python /venv/bin/python --compile-bytecode --no-deps /dist/${WHEEL}[server]
# The managed interpreter includes pip and an ensurepip wheel with vendored
# dependencies. Neither is needed after installing the application with uv.
RUN find /python -depth \( -name pip -o -name 'pip-*.dist-info' -o \
    -name 'pip3*' -o -name ensurepip \) -exec rm -rf {} +

# Ship only the interpreter and installed application, without package installers.
FROM debian:trixie-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4 AS release
RUN apt-get update && \
    apt-get install --no-install-recommends --yes adduser ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --gecos "" aipscan
COPY --from=release-build /python /python
COPY --from=release-build /venv /venv
ENV PATH="/venv/bin:$PATH"
ENV FLASK_APP=AIPscan:create_app
COPY .init-scripts/entrypoint.sh /
USER aipscan
ENTRYPOINT ["/entrypoint.sh"]

FROM ${TARGET}
