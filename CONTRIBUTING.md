# Contributing

Thank you for considering a contribution to AIPscan! AIPscan is a
work-in-progress and does not yet have a formal contribution process. Bug
reports and feature requests are welcome as issues in the AIPscan GitHub
repository. Pull requests with community code contributions are similarly
welcome but should typically be submitted after filing an issue and discussing
the proposed approach.

In general, follow code style guidelines from the Archivematica project's
[CONTRIBUTING.md] to the greatest degree possible.

## Development environment

- Install Docker CE, Docker Compose and [uv].

- Clone the repository:

  ```sh
  git clone https://github.com/artefactual-labs/AIPscan
  ```

- Change your working directory:

  ```sh
  cd AIPscan
  ```

- Start the application services:

  ```sh
  docker compose up --detach --wait
  ```

- Access the web app at <http://localhost:5000>.

- Access logs for running services:

  ```sh
  docker compose logs -f
  ```

- Shut down the stack when finished:

  ```sh
  docker compose down
  ```

- Remove all volumes when you need a clean slate:

  ```sh
  docker compose down --volumes
  ```

### Archivematica network

The Archivematica network is optional. Use it when you want AIPscan containers
to talk directly to an Archivematica development environment.

Populate the `.env` file with the following contents:

```sh
  COMPOSE_FILE=./docker-compose.yml:./docker-compose.am-network.yml
```

Then start the services:

```sh
  docker compose up --detach --wait
```

This expects an external Docker network named `am_default`, usually created by
the Archivematica development environment. The regular test suite does not need
this network.

## Running tests

The pytest suite needs MySQL, but it does not need the full application stack,
RabbitMQ, Typesense, Celery workers, or an Archivematica development
environment.

Start only the MySQL service:

```sh
COMPOSE_FILE=./docker-compose.yml docker compose up --detach --wait --no-deps aipscan-mysql
```

Run the Python test environments:

```sh
uv run tox -m test
```

Use `uv run tox list` to find the configured environment names, then select a
single environment with tox's `-e` option.

To pass arguments through to pytest:

```sh
uv run tox -m test -- -x AIPscan/tests/test_app.py
```

To run the linting environment:

```sh
uv run tox -e linting
```

The default `uv run tox` command runs every environment in `pyproject.toml`,
including linting. Use `uv run tox -m test` when you only want the test matrix.

To match CI more closely, run:

```sh
COMPOSE_FILE=./docker-compose.yml docker compose up --detach --wait --no-deps aipscan-mysql
make test PYTESTARGS="--cov AIPscan --cov-config .coveragerc --cov-report xml:coverage.xml"
make lint
COMPOSE_FILE=./docker-compose.yml docker compose run --rm --no-deps aipscan-migrate bash -c "flask db upgrade && flask db check"
```

When finished, stop the test database and remove volumes:

```sh
COMPOSE_FILE=./docker-compose.yml docker compose down --volumes
```

### Acceptance tests

The Dagger module starts isolated ambox, MySQL, RabbitMQ, and AIPscan services.
It ingests a real transfer with Archivematica, registers production legacy METS
fixtures as stored archives, and fetches their metadata through Celery. Tests
observe HTTP responses, CSV reports, persisted job durations, and Chromium UI
behavior. No existing Archivematica installation or host ports are needed.

By default, the suite builds a wheel with its frontend assets and installs it in
the release Dockerfile target. The application runs as its non-root user with
production settings. Runtime dependencies come from `uv.lock` and their hashes
are checked during image installation. The web server and worker share the
download directory, and migrations run at service startup.

With Docker and Dagger installed, run:

```sh
bash tests/e2e/check.sh
bash tests/e2e/check.sh --indexed=true
```

The second command starts a real Typesense service. An SQL app instance under
`/sql` reads the same database, so indexed exports can be compared with SQL
without a second application container. Each command exports JUnit, pytest logs,
and failed-case HTTP history to a new directory under `output/e2e`. Browser
failures also save screenshots and Playwright traces. The script prints the
artifact path and returns the pytest exit status. View a saved trace with
`uv run --group e2e playwright show-trace path/to/trace.zip`.

For source development, or to check an already-built release wheel:

```sh
bash tests/e2e/check.sh --release=false
bash tests/e2e/check.sh --distribution=dist
```

The supplied directory must contain exactly one wheel. Release CI restores the
built distribution and checks it on native amd64 and arm64 runners before PyPI
publication, tag creation, or Docker image publication can proceed. Docker
publication later rebuilds the release recipe from that same wheel.

The suite is also registered with Dagger's native checks:

```sh
dagger --lock=frozen check -l
dagger --lock=frozen check test-end-to-end
dagger --lock=frozen check test-indexed-reports
```

Checks report failures through Dagger. Use `check.sh` when you also want
artifacts exported to the host. On machines with limited Docker disk space, run
the two checks sequentially; `dagger check` runs registered checks concurrently.

#### Add a scenario

Gherkin features live in `tests/e2e/features`. Each Python test module uses
`pytest_bdd.scenarios()` to collect its feature and defines steps through normal
pytest fixtures. Shared browser, artifact, and imported-repository fixtures live
in `conftest.py`. To inspect the collection without starting services:

```sh
uv run --group e2e pytest --collect-only tests/e2e
```

Keep scenarios independent of execution order. The main corpus stays unchanged:
it includes modern and Archivematica 1.6 METS, PREMIS 2.2, missing file dates,
and an unidentified original. Package listing uses one package per page. A
separate HTTP Storage Service boundary fixture covers changed METS, deletion,
malformed XML, missing downloads, failed listing recovery, missing file sizes,
and mixed image formats with preservation files. It also supplies 1,200 files
with varied sizes to exercise index batches and exact byte totals. A parseable
METS with a missing event agent checks that a persistence failure is reported
and a later fetch can recover after the document is corrected. Imports retain
their existing commit boundaries, so these cases do not guarantee that a failed
replacement preserves the previous metadata. These cases run through the real
worker and database, but do not validate an archival ingest or preservation
normalization.

Browser checks cover pie, scatter, ingest timeline, and storage time-series
charts as separate cases. Indexed checks compare counts, sizes, largest items,
format versions, and date/location filters with SQL. Upgrade cases remove the
new format facets from the real index and verify SQL fallback before rebuilding
it through the application. The regular Python suite remains independent of
ambox and Dagger. After upgrading the indexed format fields, format reports use
SQL until the existing Typesense index is refreshed from the Storage Service
page. This keeps reports available during an upgrade.

Package listing can run as long as it keeps downloading pages. The coordinator
fails after 600 seconds without progress; set
`PACKAGE_LIST_IDLE_TIMEOUT_SECONDS` to change this limit for a slower Storage
Service.

#### Caching and image updates

Test functions use session caching. A fresh run identity prevents a previous
result from skipping tests and keeps concurrent service stacks separate. Build
layers still reuse unchanged dependency and asset inputs. uv and npm downloads
use cache volumes; virtual environments and `node_modules` are build outputs.
The wheel builder does not install runtime dependencies, and the browser runner
installs only the acceptance dependency group.

The generated `.dagger/lock` pins image lookups for both Linux architectures.
`check.sh` uses frozen lookups and fails if a needed pin is missing. Refresh
existing pins with Dagger, then review the lockfile diff:

```sh
dagger lock update
```

Dockerfile `FROM` lookups are outside the Dagger lockfile. The release stages
pin their uv base by digest so verification and publication use the same base.
Update these Dockerfile digests when updating uv. Python is installed by uv from
the version in `.python-version`, passed as a build argument. The image build
checks that the installed runtime matches that version.

When adding a new lookup, discover it by running the relevant variant live:

```sh
DAGGER_LOCK_MODE=live bash tests/e2e/check.sh --indexed=true
```

Dagger's cache is subject to garbage collection and available disk space.
Package cache volumes do not guarantee that build layers will stay resident.
Repeated downloads can indicate disk pressure; inspect engine logs and Docker's
available storage before changing retention settings. Avoid routine pruning as a
speed optimization. Increasing Docker disk capacity or freeing unused data
requires a separate decision about the machine's other projects.

GitHub-hosted runners start with a fresh engine. Cache reuse is limited to work
within each runner. See the upstream
[function caching documentation][dagger-cache] and
[lockfile documentation][dagger-locks] for the two caching layers and lock
modes. Optional engine resource limits can be introduced if measured resource
contention requires them.

## Upgrading dependencies

If you want to update Python:

- Update the `.python-version` file.
- Update the `PYTHON_VERSION` build argument in the `Dockerfile`.
- Update the CI matrix and the project classifiers.

If you want to update Node.js, there are two steps:

- Update the `.node-version` file.
- Update the base image used by the `frontend` in the `Dockerfile`.

Other dependencies:

```sh
# Python dependencies.
# Use `--dry-run` first to see what would be changed.
uv lock --upgrade

# pre-commit dependencies.
uv run prek autoupdate

# Node.js dependencies.
npx npm-check-updates --interactive
```

Prettier runs from the npm lockfile through a local prek hook, so run `npm ci`
before `make lint`. Update service image versions in both `docker-compose.yml`
and `.dagger/src/aipscan/main.py`, and keep the uv image versions and hook
aligned. The Dagger module has its own lockfile
(`uv lock --upgrade --directory .dagger`).

GitHub Actions use version tags with exact commits and repository identities in
`.github/workflows/actions.lock`. After adding or updating an action, regenerate
the lockfile with [gh actions-lock] and include it in the same commit:

```sh
gh extension install github/gh-actions-lock --pin v0.2.0
gh actions-lock
gh actions-lock --verify
```

CI verifies the lockfile without rewriting it. `gh actions-lock --verify-local`
also checks coverage offline, but does not verify the trustworthiness of pins.

## Preparing a release

Prerequisites:

- Make sure that all tests pass.
- Make sure that the dependencies are up to date (see above).

PyPI publication uses `uv publish` with required Trusted Publishing. The locked
`publish` dependency group generates attestations for the verified distribution
files before upload. The release workflow and `pypi` environment retain their
Trusted Publisher identity.

Run the release process with an alpha or release candidate tag first to shake
out issues. Remember to use the PEP 440 versioning scheme, e.g. `0.9.0a2`, using
the GitHub CLI:

```sh
gh workflow run release.yml --ref main -f version=0.9.0a2
```

Head to the Actions tab in GitHub and monitor the progress of the
[release workflow]. When everything looks good, repeat the same command with the
final version number to cut the official release (the workflow handles building,
tagging, and publishing).

## Database migrations

AIPscan now uses Alembic migrations managed through Flask-Migrate. We recommend
using the Docker Compose services so the app and migration commands share the
same configuration.

- Make sure that the development environment is running.

- Create a new migration when models change:

  ```sh
  docker compose run --rm aipscan-migrate flask db migrate -m "Describe change"
  ```

- Verify the migration applies cleanly:

  ```sh
  docker compose run --rm aipscan-migrate flask db upgrade
  ```

- Commit the generated revision(s) under `AIPscan/migrations` alongside your
  model changes. Regenerate the migration if follow-up edits change the schema.

## Generating database schema documentation

To generate database documentation using [SchemaSpy] run the following command:

```sh
make schema-docs
```

If you're using `docker-compose.am-network.yml`, then use this instead:

```sh
make schema-docs NETWORK=am_default
```

SchemaSpy writes its output to the `output` directory; open `output/index.html`
in a browser to review the results.

## Writing a new AIPscan report

Creating a new report in AIPscan is a multi-step process, comprising:

- [Creating a new Data endpoint](#creating-a-new-data-endpoint)
- [Creating a new API endpoint](#creating-a-new-api-endpoint)
- [Creating a new view and template](#creating-a-new-view-and-template)
- [Integrating the new report to the Reports selection screen](#integrating-the-new-report-to-the-reports-selection-screen)

All new Data endpoints and reports must have appropriate test coverage. In
addition, new reports should support CSV export as well as filtering by Storage
Service, Storage Location, and start and end dates.

### Creating a new Data endpoint

The first step when creating a new AIPscan report is to implement a new endpoint
for the report's data.

AIPscan implements [Flask blueprints] to separate code into discrete sections by
function. The `Data` blueprint is home to the `data` and `report_data` Python
modules, which contain all of the application's data endpoints. Endpoints that
expose overview information can be found in `AIPscan/Data/data.py`. Endpoints
which expose data particular to a report are in `AIPscan/Data/report_data.py` -
this is typically where the Data endpoint for a new report should be added.

Data endpoints are Python functions which take parameters such as
`storage_service_id`, `start_date`, `end_date`, and `storage_location_id` as
input (`start_date` and `end_date` are `datetime.datetime` objects, which should
always be created by passing YYYY-MM-DD string inputs through the
`parse_datetime_bound` helper). Each report returns a dictionary containing the
name of the queried Storage Service and Storage Location and the output data.
The structure of these dictionaries can be explored via the API endpoints, which
present the data returned by `Data` endpoints as JSON.

Data endpoints will typically rely on database queries using [SQLAlchemy] to
fetch and shape data efficiently.

For example:

```python
from AIPscan import db
from AIPscan.Data import (
    fields,
    get_storage_location_description,
    get_storage_service_name,
)
from AIPscan.models import AIP, File, FileType, StorageLocation, StorageService


def _formats_count_query(
    storage_service_id, start_date, end_date, storage_location_id=None
):
    """Fetch information from database on file formats.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)

    :returns: SQLAlchemy query results
    """
    FILE_FORMAT = "file_format"
    FILE_COUNT = "file_count"
    FILE_SIZE = "total_size"

    results = (
        db.session.query(
            File.file_format.label(FILE_FORMAT),
            db.func.count(File.id).label(FILE_COUNT),
            db.func.sum(File.size).label(FILE_SIZE),
        )
        .join(AIP)
        .join(StorageLocation)
        .join(StorageService)
        .filter(StorageService.id == storage_service_id)
        .filter(File.file_type == FileType.original.value)
        .filter(AIP.create_date >= start_date)
        .filter(AIP.create_date < end_date)
        .group_by(File.file_format)
        .order_by(db.func.count(File.id).desc(), db.func.sum(File.size).desc())
    )
    if storage_location_id:
        results = results.filter(StorageLocation.id == storage_location_id)
    return results


def formats_count(storage_service_id, start_date, end_date, storage_location_id=None):
    """Return a summary of file formats in Storage Service.

    :param storage_service_id: Storage Service ID (int)
    :param start_date: Inclusive AIP creation start date
        (datetime.datetime object)
    :param end_date: Inclusive AIP creation end date
        (datetime.datetime object)
    :param storage_location_id: Storage Location ID (int)

    :returns: "report" dict containing following fields:
        report["StorageName"]: Name of Storage Service queried
        report["Formats"]: List of results ordered desc by count and size
    """
    report = {}
    report[fields.FIELD_FORMATS] = []
    report[fields.FIELD_STORAGE_NAME] = get_storage_service_name(storage_service_id)
    report[fields.FIELD_STORAGE_LOCATION] = get_storage_location_description(
        storage_location_id
    )

    formats = _formats_count_query(
        storage_service_id, start_date, end_date, storage_location_id
    )

    for format_ in formats:
        format_info = {}

        format_info[fields.FIELD_FORMAT] = format_.file_format
        format_info[fields.FIELD_COUNT] = format_.file_count
        format_info[fields.FIELD_SIZE] = 0
        if format_.total_size is not None:
            format_info[fields.FIELD_SIZE] = format_.total_size

        report[fields.FIELD_FORMATS].append(format_info)

    return report
```

All new Data endpoints must have proper test coverage. Examples can be found in
`AIPscan/Data/tests`. Integration tests which use a test database rely heavily
on [pytest] fixtures in AIPscan's [project-wide conftest module].

### Creating a new API endpoint

Each new Data endpoint should have a corresponding API endpoint. These are not
used to serve data within the AIPscan application, but serve to allow flexible
uses of data gathered by AIPscan.

All API code can be found in the `API` blueprint. AIPscan uses the [Flask-RESTX]
library to provide API functionality and API documentation using Swagger.

API endpoints in AIPscan are thin wrappers around their corresponding `Data`
endpoints. These can be found in the `namespace_data` and
`namespace_report_data` modules within the `API` blueprint.

For example:

```python
from flask import request
from flask_restx import Namespace, Resource

from AIPscan.API import fields
from AIPscan.Data import report_data
from AIPscan.helpers import parse_datetime_bound

api = Namespace(
    "report-data", description="Retrieve data optimized for AIPscan reports"
)


@api.route("/format-version-count/<storage_service_id>")
class FormatVersionList(Resource):
    @api.doc(
        "list_format_versions",
        params={
            fields.FIELD_START_DATE: {
                "description": "AIP creation start date (inclusive, YYYY-MM-DD)",
                "in": "query",
                "type": "str",
            },
            fields.FIELD_END_DATE: {
                "description": "AIP creation end date (inclusive, YYYY-MM-DD)",
                "in": "query",
                "type": "str",
            },
            fields.FIELD_STORAGE_LOCATION: {
                "description": "Storage Location ID",
                "in": "query",
                "type": "int",
            },
        },
    )
    def get(self, storage_service_id):
        """List file format versions with file count and size"""
        start_date = parse_datetime_bound(request.args.get(fields.FIELD_START_DATE))
        end_date = parse_datetime_bound(
            request.args.get(fields.FIELD_END_DATE), upper=True
        )
        storage_location_id = request.args.get(fields.FIELD_STORAGE_LOCATION)

        return report_data.format_versions_count(
            storage_service_id=storage_service_id,
            start_date=start_date,
            end_date=end_date,
            storage_location_id=storage_location_id,
        )
```

The API endpoints can be very useful during the development process, as they
provide increased visibility into the data being returned from a Data endpoint.

### Creating a new view and template

Once a Data endpoint has been created and tested, it is time to create a new
report in the GUI. Each report in AIPscan is a web page with a corresponding
view and template in the `Reporter` blueprint. Reports with multiple
representations (for example, a tabular report and a pie chart) will have a
separate view function and template for each representation.

Each report's views are contained within a separate module, which is
subsequently imported into `AIPscan/Reporter/views.py`. All views related to a
report should be contained within the same module. Common request parameters are
defined as constants in `AIPscan/Reporter/request_params.py`.

For example, the `report_format_versions_count()` tabular view is defined in
`AIPscan/Reporter/report_format_versions_count.py`:

```python
from flask import render_template, request

from AIPscan.Data import fields, report_data
from AIPscan.helpers import parse_bool, parse_datetime_bound
from AIPscan.Reporter import (
    download_csv,
    format_size_for_csv,
    get_display_end_date,
    reporter,
    request_params,
    translate_headers,
)

HEADERS = [
    fields.FIELD_PUID,
    fields.FIELD_FORMAT,
    fields.FIELD_VERSION,
    fields.FIELD_COUNT,
    fields.FIELD_SIZE,
]


@reporter.route("/report_format_versions_count/", methods=["GET"])
def report_format_versions_count():
    """Return overview of format versions in Storage Service."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    version_data = report_data.format_versions_count(
        storage_service_id=storage_service_id,
        start_date=start_date,
        end_date=end_date,
        storage_location_id=storage_location_id,
    )
    versions = version_data.get(fields.FIELD_FORMAT_VERSIONS)

    if csv:
        # Using the translate_headers function's "True" argument will
        # have it automatically add an additional size column with the size
        # data left as the number of bytes, rather than a more human readable
        # description of the size, to make it easier to sort CSV rows by size
        headers = translate_headers(HEADERS, True)

        filename = "format_versions.csv"
        csv_data = format_size_for_csv(versions)
        return download_csv(headers, csv_data, filename)

    headers = translate_headers(HEADERS)

    return render_template(
        "report_format_versions_count.html",
        storage_service_id=storage_service_id,
        storage_service_name=version_data.get(fields.FIELD_STORAGE_NAME),
        storage_location_description=version_data.get(fields.FIELD_STORAGE_LOCATION),
        columns=translate_headers(headers),
        versions=versions,
        total_file_count=sum(
            version.get(fields.FIELD_COUNT, 0) for version in versions
        ),
        total_size=sum(version.get(fields.FIELD_SIZE, 0) for version in versions),
        puid_count=len(versions),
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )
```

CSV downloads are handled by the `Reporter` blueprint's `download_csv` helper.
Report data is also formatted using the `format_size_for_csv` helper, which
converts sizes in bytes to human-readable values.

The report module is then imported in `AIPscan/Reporter/views.py`:

```python
from AIPscan.Reporter import (  # noqa: F401
    report_aip_contents,
    report_aips_by_format,
    report_aips_by_puid,
    report_format_versions_count,
    report_formats_count,
    report_ingest_log,
    report_largest_files,
    report_preservation_derivatives,
    report_storage_locations,
    reporter,
    request_params,
    sort_puids,
)
```

Each Flask view has a corresponding [jinja2 template] within
`AIPscan/Reporter/templates`. Each template extends from a base template defined
in `AIPscan/templates/report_base.html`.

For example:

```jinja
{% extends "report_base.html" %}

{% block content %}

<div class="alert alert-secondary">

  {% include "report_buttons.html" %}

  <strong>Report:</strong> File format version count
  <br>
  <strong>Storage Service:</strong> {{ storage_service_name }}
  <br>
  {% if storage_location_description %}
    <strong>Location:</strong> {{ storage_location_description }}
    <br>
  {% endif %}
  {% if start_date and end_date %}
    {{ total_file_count }} original files ingested between {{ start_date.strftime('%Y-%m-%d') }} and {{ end_date.strftime('%Y-%m-%d') }}
  {% elif start_date %}
    {{ total_file_count }} original files ingested on and since {{ start_date.strftime('%Y-%m-%d') }}
  {% elif end_date %}
    {{ total_file_count }} original files ingested on and before {{ end_date.strftime('%Y-%m-%d') }}
  {% else %}
    {{ total_file_count }} original files
  {% endif %}
  <br>
  {{ puid_count }} different format versions totalling {{ total_size | filesizeformat }}
</div>

{% if versions %}
  <table id="formatversioncounts" class="table table-striped table-bordered">
    <thead>
      <tr>
        {% for column in columns %}
        <th><strong>{{ column }}</strong></th>
        {% endfor %}
      </tr>
    </thead>
    <tbody>
    {% for version in versions %}
      <tr>
        <td>{{ version["PUID"] }}</td>
        <td>{{ version["Format"] }}</td>
        <td>{{ version["Version"] }}</td>
        <td>{{ version["Count"] }}</td>
        <td>{{ version["Size"] | filesizeformat }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
{% else %}
  <p class="h4" style="margin-top:20px;">No file format versions to display.</p>
{% endif %}

{% endblock %}
```

A template partial is utilized for the "Download CSV" and "Print" buttons to
ensure consistency between all reports.

At this point, you can verify that your report is working as expected by
manually entering the URL specified by the view into your browser.

New reports in the `Reporter` endpoint should have accompanying tests in
`Reporter/tests`. This should include at least one test to ensure that the view
returns the correct page as expected, and at least one test to verify the
contents of a CSV export.

### Integrating the new report to the Reports selection screen

Finally, once a Data endpoint, API endpoint, and report view and template have
been created, it is time to add your new report to the Reports selection screen
template `AIPscan/Reporter/templates/reports.html`.

First, add your new report to the reports table. Each report should have a
title, description (including available filters), and one or more buttons in the
"Format" column. Additional parameter dropdown selectors can be added to the
"Report" column under the report's title as needed. Be sure to give each button
in the "Format" column a readable and semantically meaningful ID.

Finally, add an event handler for each button in the template's JavaScript,
which uses jQuery.

For example:

```javascript
$("#aipsByOriginalFormat").on("click", function() {
	var fileFormat = $('#originalFormatSelect').val();
	var url = (
	  window.location.origin +
	  '/reporter/aips_by_file_format/' +
	  '?amss_id=' +
	  storageServiceId +
	  '&storage_location=' +
	  storageLocationId +
	  '&file_format=' +
	  fileFormat +
	  '&original_files=True'
	);
	window.open(url);
	});
```

Congratulations! You've now added a new report to AIPscan.

[contributing.md]: https://github.com/artefactual/archivematica/blob/HEAD/CONTRIBUTING.md
[dagger-cache]: https://docs.dagger.io/extending/function-caching/
[dagger-locks]: https://docs.dagger.io/next/reference/cli/lockfiles/
[flask blueprints]: https://flask.palletsprojects.com/en/1.1.x/blueprints/
[flask-restx]: https://flask-restx.readthedocs.io/en/latest/
[gh actions-lock]: https://github.com/github/gh-actions-lock
[jinja2 template]: https://flask.palletsprojects.com/en/1.1.x/templating/
[project-wide conftest module]: https://github.com/artefactual-labs/AIPscan/blob/main/AIPscan/conftest.py
[pytest]: https://docs.pytest.org
[release workflow]: https://github.com/artefactual-labs/AIPscan/actions/workflows/release.yml
[schemaspy]: http://schemaspy.org/
[sqlalchemy]: https://www.sqlalchemy.org/
[uv]: https://docs.astral.sh/uv/getting-started/installation/
