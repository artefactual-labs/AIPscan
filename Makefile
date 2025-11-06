SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: *

DBG_MAKEFILE ?=
ifeq ($(DBG_MAKEFILE),1)
    $(warning ***** starting Makefile for goal(s) "$(MAKECMDGOALS)")
    $(warning ***** $(shell date))
else
    # If we're not debugging the Makefile, don't echo recipes.
    MAKEFLAGS += -s
endif

.uv: ## Check that uv is installed
	@uv --version >/dev/null 2>&1 || { \
		echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'; \
		exit 1; \
	}

build: # @HELP An alias for build-frontend-assets (for backward compatibility).
build: build-frontend-assets

build-frontend-assets: # @HELP Build frontend assets (JS/CSS) using npm.
build-frontend-assets:
	npm clean-install
	npm run build

build-release-image: # @HELP Build release image `aipscan-release-test` for local testing.
build-release-image: AIPSCAN_VERSION=1.0.0.dev1
build-release-image: IMAGE_TAG=aipscan-release-test:$(AIPSCAN_VERSION)
build-release-image: PYTHON_VERSION=$(shell tr -d '\n' < $(CURDIR)/.python-version)
build-release-image: .uv
	echo "[build-release-image] Building ${IMAGE_TAG} image with Python ${PYTHON_VERSION}..."
	SETUPTOOLS_SCM_PRETEND_VERSION=${AIPSCAN_VERSION} uv build
	docker build \
		--target=release \
		--tag=${IMAGE_TAG} \
		--build-arg=PYTHON_VERSION=${PYTHON_VERSION} \
		--build-arg=WHEEL=aipscan-${AIPSCAN_VERSION}-py3-none-any.whl \
			.
	docker images ${IMAGE_TAG}
	echo "To test, run:"
	echo "  docker run --rm ${IMAGE_TAG}"

lint: # @HELP Run linters.
lint: .uv
	uv run tox -e linting -- $(ARGS)

schema-docs: IMAGE ?= schemaspy/schemaspy:7.0.2
schema-docs: NETWORK ?= default
schema-docs: DB_HOST ?= aipscan-mysql
schema-docs: DB_PORT ?= 3306
schema-docs: DB_NAME ?= aipscan
schema-docs: DB_USER ?= aipscan
schema-docs: DB_PASS ?= demo
schema-docs: # @HELP Generate database schema documentation using SchemaSpy.
schema-docs:
	mkdir -p output
	chmod a+w output
	docker run --rm --network $(NETWORK) --volume "$(CURDIR)/output:/output" $(IMAGE) \
		--database-type mysql --host $(DB_HOST) --port $(DB_PORT) \
		--user $(DB_USER) --password $(DB_PASS) \
		--database-name $(DB_NAME) --schema $(DB_NAME) \
		--output /output --catalog aipscan

test: # @HELP Run tests.
test: TOXENV ?=
test: LABEL ?= test
test: PYTESTARGS ?= -x
test: .uv
	if [ -z "$(TOXENV)" ]; then \
		uv run tox -m "$(LABEL)" -- $(PYTESTARGS); \
	else \
		uv run tox -e "$(TOXENV)" -- $(PYTESTARGS); \
	fi

help: # @HELP Print this message.
help:
	echo "TARGETS:"
	grep -E '^.*: *# *@HELP' Makefile             \
	    | awk '                                   \
	        BEGIN {FS = ": *# *@HELP"};           \
	        { printf "  %-30s %s\n", $$1, $$2 };  \
	    '
