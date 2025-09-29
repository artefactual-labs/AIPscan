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

schema-docs: # @HELP Generate database schema documentation using SchemaSpy.
schema-docs:
	mkdir -p output   # Create output directory
	chmod a+w output  # Allow Docker image user to write to directory
	docker build \
		-t schemaspy-sqlite3 \
		https://github.com/artefactual-labs/docker-schemaspy-sqlite3.git
	docker run \
		-v "./aipscan.db:/aipscan.db" \
		-v "./output:/output" \
		schemaspy-sqlite3:latest \
		-t sqlite-xerial \
		-db "/aipscan.db" \
		-imageformat png \
		-u schemaspy.u \
		-cat aipscan \
		-s aipscan \
		-debug

help: # @HELP Print this message.
help:
	echo "TARGETS:"
	grep -E '^.*: *# *@HELP' Makefile             \
	    | awk '                                   \
	        BEGIN {FS = ": *# *@HELP"};           \
	        { printf "  %-30s %s\n", $$1, $$2 };  \
	    '
