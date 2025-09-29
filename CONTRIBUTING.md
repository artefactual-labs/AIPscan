# Contributing

Thank you for considering a contribution to AIPscan!
AIPscan is a work-in-progress and does not yet have a formal
contribution process. Bug reports and feature requests are welcome as
issues in the AIPscan GitHub repository. Pull requests with community
code contributions are similarly welcome but should typically be
submitted after filing an issue and discussing the proposed approach.

In general, follow code style guidelines from the Archivematica
project's [CONTRIBUTING](https://github.com/artefactual/archivematica/blob/HEAD/CONTRIBUTING.md)
to the greatest degree possible.

## Preparing a release

Before running the release workflow, confirm that `.python-version` reflects the
Python release you want baked into the Docker images; update it to a recent
supported version if needed. Run the release process with an alpha or release
candidate tag first to shake out issues, using e.g.
`gh workflow run release.yml --ref main -f version=0.9.0a2`. When everything
looks good, repeat the same command with the final version number to cut the
official release (the workflow handles building, tagging, and publishing).

## Writing a new AIPscan report

Creating a new report in AIPscan is a multi-step process, comprising:

* [Creating a new Data endpoint](#creating-a-new-data-endpoint)
* [Creating a new API endpoint](#creating-a-new-api-endpoint)
* [Creating a new view and template](#creating-a-new-view-and-template)
* [Integrating the new report to the Reports selection screen](#integrating-the-new-report-to-the-reports-selection-screen)

All new Data endpoints and reports must have appropriate test coverage.
In addition, new reports should support CSV export as well as filtering
by Storage Service, Storage Location, and start and end dates.

### Creating a new Data endpoint

The first step when creating a new AIPscan report is to implement a new
endpoint for the report's data.

AIPscan implements [Flask blueprints](https://flask.palletsprojects.com/en/1.1.x/blueprints/)
to separate code into discrete sections by function. The `Data`
blueprint is home to the `data` and `report_data` Python modules, which
contain all of the application's data endpoints. Endpoints that expose
overview information can be found in `AIPscan/Data/data.py`. Endpoints
which expose data particular to a report are in
`AIPscan/Data/report_data.py` - this is typically where the Data
endpoint for a new report should be added.

Data endpoints are Python functions which take parameters such as
`storage_service_id`, `start_date`, `end_date`, and
`storage_location_id` as input (`start_date` and `end_date` are
`datetime.datetime` objects, which should always be created by passing
YYYY-MM-DD string inputs through the
[parse_datetime_bound](https://github.com/artefactual-labs/AIPscan/blob/main/AIPscan/helpers.py#L14-L45)
helper). Each report returns a dictionary containing the name of the
queried Storage Service and Storage Location and the output data. The
structure of these dictionaries can be explored via the API endpoints,
which present the data returned by `Data` endpoints as JSON.

Data endpoints will typically rely on database queries using
[SQLAlchemy](https://www.sqlalchemy.org/) to fetch and shape data
efficiently.

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

All new Data endpoints must have proper test coverage. Examples can
be found in `AIPscan/Data/tests`. Integration tests which use a test
database rely heavily on [pytest](https://docs.pytest.org) fixtures in
AIPscan's
[project-wide conftest module](https://github.com/artefactual-labs/AIPscan/blob/main/AIPscan/conftest.py).

### Creating a new API endpoint

Each new Data endpoint should have a corresponding API endpoint. These
are not used to serve data within the AIPscan application, but serve to
allow flexible uses of data gathered by AIPscan.

All API code can be found in the `API` blueprint. AIPscan uses the
[Flask-RESTX](https://flask-restx.readthedocs.io/en/latest/) library to
provide API functionality and API documentation using Swagger.

API endpoints in AIPscan are thin wrappers around their corresponding
`Data` endpoints. These can be found in the `namespace_data` and
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

The API endpoints can be very useful during the development process, as
they provide increased visibility into the data being returned from a
Data endpoint.

### Creating a new view and template

Once a Data endpoint has been created and tested, it is time to
create a new report in the GUI. Each report in AIPscan is a web page
with a corresponding view and template in the `Reporter` blueprint.
Reports with multiple representations (for example, a tabular report
and a pie chart) will have a separate view function and template for
each representation.

Each report's views are contained within a separate module, which is
subsequently imported into `AIPscan/Reporter/views.py`.  All views
related to a report should be contained within the same module.
Common request parameters are defined as constants in
`AIPscan/Reporter/request_params.py`.

For example, the `report_format_versions_count()` tabular view is
defined in `AIPscan/Reporter/report_format_versions_count.py`:

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

CSV downloads are handled by the `Reporter` blueprint's
[download_csv
helper](https://github.com/artefactual-labs/AIPscan/blob/main/AIPscan/Reporter/helpers.py#L100-L116).
Report data is also formatted using the `format_size_for_csv` helper,
which converts sizes in bytes to human-readable values.

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

Each Flask view has a corresponding
[jinja2 template](https://flask.palletsprojects.com/en/1.1.x/templating/)
within `AIPscan/Reporter/templates`. Each template extends from a base
template defined in `AIPscan/templates/report_base.html`.

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

A template partial is utilized for the "Download CSV" and "Print"
buttons to ensure consistency between all reports.

At this point, you can verify that your report is working as expected
by manually entering the URL specified by the view into your browser.

New reports in the `Reporter` endpoint should have accompanying tests
in `Reporter/tests`. This should include at least one test to ensure
that the view returns the correct page as expected, and at least one
test to verify the contents of a CSV export.

### Integrating the new report to the Reports selection screen

Finally, once a Data endpoint, API endpoint, and report view and
template have been created, it is time to add your new report to the
Reports selection screen template
`AIPscan/Reporter/templates/reports.html`.

First, add your new report to the reports table. Each report should
have a title, description (including available filters), and one or
more buttons in the "Format" column. Additional parameter dropdown
selectors can be added to the "Report" column under the report's title
as needed. Be sure to give each button in the "Format" column a
readable and semantically meaningful ID.

Finally, add an event handler for each button in the template's
JavaScript, which uses jQuery.

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
