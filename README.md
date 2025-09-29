[![PyPI version](https://badge.fury.io/py/aipscan.svg)](https://badge.fury.io/py/aipscan)
[![GitHub CI](https://github.com/artefactual-labs/AIPscan/actions/workflows/test.yml/badge.svg)](https://github.com/artefactual-labs/AIPscan/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/artefactual-labs/AIPscan/branch/main/graph/badge.svg?token=2RRFAM8P89)](https://codecov.io/gh/artefactual-labs/AIPscan)

# About

AIPscan was developed to provide a more in-depth reporting solution for
Archivematica users. It crawls METS files from AIPs in the Archivematica
Storage Service to generate tabular and visual reports about repository
holdings. It is designed to run as a stand-alone add-on to Archivematica. It
only needs a valid Storage Service API key to fetch source data.

# License

[Apache License Version 2.0](LICENSE)
Copyright Artefactual Systems Inc (2021)

# Contents

* [Screenshots](#screenshots)
* [Installation](#installation)
* [Usage](#usage)

## Screenshots

### AIPscan fetch job

![screencap1](screencaps/aipscan_fetch_job.png)

### Finding an AIP

![screencap2](screencaps/aipscan_find_aip.png)

### Viewing an AIP

![screencap3](screencaps/aipscan_view_aip.png)

### Selecting a report

![screencap4](screencaps/aipscan_select_report.png)

### Example: pie chart "format types" report

![screencap5](screencaps/aipscan_piechart_report.png)

### Example: tabular "largest files" report

![screencap6](screencaps/aipscan_tabular_report.png)

# Installation

AIPscan is a web-based application that is built using the Python [Flask](https://pypi.org/project/Flask/)
micro-framework. Below are the developer quickstart instructions. See [INSTALL](INSTALL.md)
for production deployment instructions. See [CONTRIBUTING](CONTRIBUTING.md) for
guidelines on how to contribute to the project, including how to create a new
AIPscan report.

## AIPscan Flask server

* Install [uv] if it's not already available
* Clone files and cd to directory:
  `git clone https://github.com/artefactual-labs/AIPscan && cd AIPscan`
* Install all project dependencies (including development extras): `uv sync`
* Bundle static assets: `npm run build`
* Enable DEBUG mode if desired for development: `export FLASK_CONFIG=dev`
* In a terminal window, start the Flask server: `uv run python -m AIPscan.run`
* Confirm that the Flask server and AIPscan application are up and running at
  [`localhost:5000`][usage-1] in your browser.. You should see a blank AIPscan
  page like this:

![screencap5](screencaps/aipscan_hello_world.png)

### Typesense integration

AIPscan can optionally be run using Typesense as a report data source,
potentially reducing the time to generate reports. If Typesense is installed
and enabled then AIPscan data will be automatically indexed after each fetch
job and report queries will pull data from Typesense rather than the
application's database.

Typesense can be installed a variety of ways
[detailed on their website](https://typesense.org/docs/guide/install-typesense.html).

#### Configuration

Typesense configuration is done using the following environment variables:

* Typesense API key (required): `TYPESENSE_API_KEY`
* Typesense host: `TYPESENSE_HOST` (default "localhost")
* Typesense port: `TYPESENSE_PORT` (default "8108")
* Typesense URL protocol: `TYPESENSE_PROTOCOL` (default "http")
* Typesense timeout (in seconds): `TYPESENSE_TIMEOUT_SECONDS` (default "30")
* Typesense collection prefix: `TYPESENSE_COLLECTION_PREFIX` (default "aipscan_")

Typesense support is enabled by the setting of `TYPESENSE_API_KEY`.

Here's an example:

  ```bash
  TYPESENSE_API_KEY="xOxOxOxO" python -m AIPscan.run
  ```

#### Related CLI tools

Two CLI tools exist to manually indexed AIPscan's database and to see a
summary of the Typesense index.

* Index AIPscan data: `tools/index-refresh`
* Display a summary of the Typesense index: `tools/index-summary`

## Background workers

Crawling and parsing many Archivematica AIP METS xml files at a time is
resource intensive. Therefore, AIPscan uses the [RabbitMQ][rabbit-MQ1] message
broker and the [Celery][celery-1] task manager to coordinate this activity as
background worker tasks. **Both RabbitMQ and Celery must be running properly
before attempting a METS fetch job.**

## RabbitMQ

You can downnload and install RabbitMQ server directly on your local or cloud
machine or you can run it in either location from a Docker container.

### Docker installation

  ```shell
  docker run --rm \
    -it \
    --hostname my-rabbit \
    -p 15672:15672 \
    -p 5672:5672 rabbitmq:3-management
  ```

### Download and install

* [Download][rabbit-MQ3] RabbitMQ installer.
* In another terminal window, start RabbitMQ queue manager:

  ```bash
  export PATH=$PATH:/usr/local/sbin
  sudo rabbitmq-server
  ```

### RabbitMQ dashboard

* The RabbitMQ dashboard is available at [`http://localhost:15672/`][rabbit-MQ2]
* username: `guest` / password: `guest`
* AIPscan connects to the RabbitMQ queue on port `:5672`.

## Celery

Celery is installed when you run `uv sync`.

To start up Celery workers that are ready to receive tasks from RabbitMQ:

* Open a new terminal tab or window.
* Navigate to the AIPscan root project directory.
* Install dependencies if you have not already (`uv sync`).
* Enter the following command:
  `uv run celery -A AIPscan.worker.celery worker --loglevel=info`
* You should see terminal output similar to this to indicate that the Celery
  task queue is ready:

![screencap6](screencaps/aipscan_celery_hello_world.png)

# Development

Requires [Docker CE](https://www.docker.com/community-edition) and [Docker Compose](https://docs.docker.com/compose/).

Clone the repository and go to its directory:

```shell
git clone https://github.com/artefactual-labs/AIPscan
cd AIPscan
```

Build images, initialize services, etc.:

```shell
docker-compose up -d
```

Optional: attach AIPscan to the Docker Archivematica container network directly:

```shell
docker-compose -f docker-compose.yml -f docker-compose.am-network.yml up -d
```

In this case, the AIPscan Storage Service record's URL field can be set with the
Storage Service container name:

```shell
http://archivematica-storage-service:8000
```

Access the logs:

```shell
docker-compose logs -f aipscan rabbitmq celery-worker
```

Shut down the AIPscan Docker containers:

```shell
docker-compose down
```

Shut down the AIPscan Docker containers and remove the rabbitmq volumes:

```shell
docker-composer down --volumes
```

## Production deployments

For production deployments, it's recommended to use MySQL instead of SQLite.
This can be achieved by exporting an environment variable named
```SQLALCHEMY_DATABASE_URI```  for celery and AIPscan services, that points to
MySQL using the format ```mysql+pymysql://user:pass@host/db```.

When the `SQLALCHEMY_DATABASE_URI` environment variable is set the value of it
will be output during startup of both AIPscan and Celery workers.

SQLite databases can be migrated using ```sqlite3mysql```:

```shell
uv tool install sqlite3-to-mysql
sqlite3mysql -f aipscan.db -d <mysql database name> -u<mysql database user> ----mysql-password <mysql database password>
```

## Tools

The `tools` directory contains scripts that can be run by developers and system
adminsitrators.

### Test data generator

The test data generator, `tools/generate-test-data`, tool populates
AIPscan's databse with randomly generated example data.

### Fetch script

The AIP fetch tool, `tools/fetch_aips`, allows all, or a subset, of a storage
service's packages to be fetched by AIPscan. Any AIPs not yet fetched by
AIPscan will be added but no duplicates will be added if an AIP has already
been fetched. Any AIPs that have been newly marked as deleted will be removed
from AIPscan.

When using the script the storage service's list of packages can optionally be
grouped into "pages" with each "page" containing a number of packages
(specified by a command-line argument). So, for example, packages on a storage
service with 150 packages on it could be fetched by fetching three pages of 50
packages. Likewise if the storage service has anything from 101 to 149 packages
on it it could also be fetched by fetching three pages of 50 packages.

If using `cron`, or some other scheduler, to automatically fetch AIPs using
this tool consider using the `--lockfile` option to prevent overlapping
executions of the tool.

#### Cached package list

A storage service's list of packages is downloaded by the script and is cached
so paging, if used, will remain consistent between script runs. The cache of a
particular cached list of packages is identified by a "session descriptor". A
session descriptor is specified by whoever runs the script and can be any
alphanumeric identifier without spaces or special characters. It's used to name
the directory in which fetch-related files are created.

Below is what the directory structure would end up looking like if the session
identifier "somedescriptor" was used, showing where the `packages.json` file,
containing the list of a storage service's packages, would be put.

```text
AIPscan/Aggregator/downloads/somedescriptor
├── mets
│   └── batch
└── packages
    └── packages.json
```

**NOTE:** Each run of the script will generate a new fetch job database entry.
These individual fetch jobs shouldn't be deleted, via the AIPscan web UI,
until all fetch jobs (for each "page") have run. Otherwise the cached list of
packages will be deleted and the package list will have to be downloaded again.

### Running tools

These should be run using the same system user and virtual environment that
AIPscan is running under.

Here's how you would run the `generate-test-data` tool, for example:

```shell
cd <path to AIPscan base directory>
sudo -u <AIPscan system user> /bin/bash
source <path to AIPscan virtual environment>/bin/activate
./tools/generate-test-data
```

In order to display a tool's CLI arguments and options, enter `<path to tool>
--help`.

#### Database documentation generator

To generate database documentation, using Schemaspy run via Docker, enter the
following:

```shell
sudo make schema-docs
```

Database documentation will be output to the `output` directory and viewable
by a web browser by opening `index.html`.

# Usage

* Ensure that the Flask Server, RabbitMQ server, and Celery worker queue are up
  and running.
* Go to [`localhost:5000`][usage-1] in your browser.
* Select "New Storage Service"
* Add an Archivematica Storage Service record, including API Key, eg.
`https://amdemo.artefactual.com:8000`
* Select "New Fetch Job"
* Check the black and green terminal to confirm that AIPscan successfully
  connected to the Archivematica Storage Service, that it received the lists of
  available packages from Archivematica, and that it has begun downloading and
  parsing the AIP METS files.
* This could take a while (i.e. a few hours) depending on the total number of
  AIPs in your Storage Service and the size of your METS xml files. Therefore,
  if you have the option, it is recommended that you test AIPscan on a smaller
  subset of your full AIP holdings first. This should help you estimate the
  total time to run AIPscan against all packages in your Storage Service.
* When the Fetch Job completes, select "View AIPs" button, "AIPs" menu, or
  "Reports" menu to view all the interesting information about your
  Archivematica content in a variety of layouts.

[uv]: https://docs.astral.sh/uv/getting-started/installation/
[rabbit-MQ1]: https://www.rabbitmq.com/
[celery-1]: https://docs.celeryproject.org/en/stable/getting-started/introduction.html
[rabbit-MQ2]: http://localhost:15672/
[rabbit-MQ3]: https://www.rabbitmq.com/download.html
[usage-1]: http://localhost:5000
