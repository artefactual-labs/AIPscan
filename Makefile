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

build:
	# Install Node modules
	npm install

	# Bundle vendor assets
	npx vite build -c build_config/base.config.js
	npx vite build -c build_config/report_base.config.js
	npx vite build -c build_config/chart_formats_count.config.js
	npx vite build -c build_config/plot_formats_count.config.js

	# Directly copy Javascript from packages not easily handled by Vite
	cp node_modules/plotly.js-dist/plotly.js AIPscan/static/dist/plot_formats_count

test:
	python3 -m pytest
