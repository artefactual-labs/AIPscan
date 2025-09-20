all: build

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

test:
	python3 -m pytest

requirements:
	# Fail if the lockfile is missing or needs to be updated.
	uv lock --locked
	uv export --frozen --format requirements.txt --no-header --no-hashes --no-dev --output-file $(CURDIR)/requirements/base.txt
	uv export --frozen --format requirements.txt --no-header --no-hashes --dev --output-file $(CURDIR)/requirements/test.txt

.PHONY: schema-docs build test requirements
