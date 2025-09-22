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

.PHONY: schema-docs
