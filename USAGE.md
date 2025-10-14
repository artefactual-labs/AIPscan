# Using AIPscan

AIPscan was developed to provide a more in-depth reporting solution for
Archivematica users. It crawls METS files from AIPs in the Archivematica Storage
Service to generate tabular and visual reports about repository holdings. It is
designed to run as a stand-alone add-on to Archivematica. It only needs a valid
Storage Service API key to fetch source data.

## Web application workflow

1. Confirm the application is installed and running (see `INSTALL.md` for
   deployment guidance).
2. Open the web UI at `http://localhost:5000` or the host you configured.
3. Choose **New Storage Service** and enter the Archivematica Storage Service
   credentials, including the API key (e.g.,
   `https://amdemo.artefactual.com:8000`).
4. Trigger **New Fetch Job** to populate AIPscan with data. Larger repositories
   take longer to fetch and process, so starting with a small subset can help
   estimate runtime.
5. After the fetch completes, explore the holdings via **View AIPs** or the
   **Reports** menu. The interface provides tabular and chart-based reports that
   can also be exported as CSV files.

## Command-line tools

The `tools` directory contains scripts intended for developers and system
administrators. Run them with the same system user and virtual environment that
hosts AIPscan.

### Test data generator

`tools/generate-test-data` seeds the database with randomly generated example
data.

Example invocation:

```bash
cd <path to AIPscan base directory>
sudo -u <AIPscan system user> /bin/bash
source <path to AIPscan virtual environment>/bin/activate
./tools/generate-test-data
```

### Fetch script

`tools/fetch_aips` fetches all or a subset of packages from an Archivematica
Storage Service. Newly deleted AIPs are removed from AIPscan, and previously
fetched AIPs are not duplicated.

The script can fetch packages in "pages" defined by the `--per-page` argument.
For example, a storage service with 150 packages can be fetched as three pages
of 50. When using schedulers such as `cron`, combine the command with the
`--lockfile` option to prevent overlapping runs.

#### Cached package list

Package listings are cached between runs. The cache is keyed by a session
descriptor you provide—an alphanumeric identifier without spaces or special
characters. Each descriptor maps to a directory like the following:

```text
AIPscan/Aggregator/downloads/somedescriptor
├── mets
│   └── batch
└── packages
    └── packages.json
```

Each run creates a new fetch job entry in the database. Leave those entries in
place until every paged fetch completes; deleting one prematurely forces the
script to download the package list again.

### Inspecting CLI options

Append `--help` to any script path to review its arguments and options.
