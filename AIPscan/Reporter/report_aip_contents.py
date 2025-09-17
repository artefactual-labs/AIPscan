from operator import itemgetter

from flask import render_template
from flask import request

from AIPscan.Data import data
from AIPscan.Data import fields
from AIPscan.helpers import parse_bool
from AIPscan.helpers import parse_datetime_bound
from AIPscan.Reporter import download_csv
from AIPscan.Reporter import format_size_for_csv
from AIPscan.Reporter import get_display_end_date
from AIPscan.Reporter import reporter
from AIPscan.Reporter import request_params
from AIPscan.Reporter import translate_headers

CSV_HEADERS = [
    fields.FIELD_UUID,
    fields.FIELD_AIP_NAME,
    fields.FIELD_CREATED_DATE,
    fields.FIELD_SIZE,
    fields.FIELD_FORMATS,
]

TABLE_HEADERS = [
    fields.FIELD_AIP_NAME,
    fields.FIELD_CREATED_DATE,
    fields.FIELD_SIZE,
    fields.FIELD_FORMATS,
]


def _create_aip_formats_string_representation(aips, separator="<br>"):
    """Return data prepared for CSV file.

    :param aips: AIPS data returned by data.aip_file_format_overview
        endpoint (list of dicts)

    :returns: Input data with each AIP's formats value formatted as a string
        (list of dicts)
    """
    for aip in aips:
        formats = []
        aip_formats = _create_aip_formats_list_sorted_by_count(
            aip.get(fields.FIELD_FORMATS)
        )
        for format_ in aip_formats:
            plural = ""
            count = format_.get(fields.FIELD_COUNT)
            if count > 1:
                plural = "s"
            format_string = f"{format_.get(fields.FIELD_PUID)} ({format_.get(fields.FIELD_FORMAT)}): {count} file{plural}"
            formats.append(format_string)
        aip[fields.FIELD_FORMATS] = f"{separator}".join(
            [format_ for format_ in formats]
        )
    return aips


def _create_aip_formats_list_sorted_by_count(formats):
    """Return list of AIP format dicts sorted by count from input dict.

    The dict returned for each AIP in fields.FIELD_FORMATS by the data module's
    aip_file_format_overview endpoint is difficult to sort, as it is a dict of
    dicts with an unpredictable key (PUID or format name) for each child
    dict. This function transforms this into an easier to parse list of dicts,
    sorted descending by count.

    :param formats: Dict of dicts returned by data.aip_file_format_overview for
        each aip (dict)

    :returns: Input data transformed into a sorted list of dicts.
    """
    formats_list = []
    for key, values in formats.items():
        format_info = {}
        format_info[fields.FIELD_PUID] = key
        format_info[fields.FIELD_FORMAT] = values.get(fields.FIELD_NAME)
        if values.get(fields.FIELD_VERSION):
            format_info[fields.FIELD_FORMAT] = (
                f"{values.get(fields.FIELD_NAME)} {values.get(fields.FIELD_VERSION)}"
            )
        format_info[fields.FIELD_COUNT] = values.get(fields.FIELD_COUNT)
        formats_list.append(format_info)
    return sorted(formats_list, key=itemgetter(fields.FIELD_COUNT), reverse=True)


@reporter.route("/aip_contents/", methods=["GET"])
def aip_contents():
    """Return AIP contents organized by format."""
    storage_service_id = request.args.get(request_params.STORAGE_SERVICE_ID)
    storage_location_id = request.args.get(request_params.STORAGE_LOCATION_ID)
    start_date = parse_datetime_bound(request.args.get(request_params.START_DATE))
    end_date = parse_datetime_bound(
        request.args.get(request_params.END_DATE), upper=True
    )
    csv = parse_bool(request.args.get(request_params.CSV), default=False)

    aip_data = data.aip_file_format_overview(
        storage_service_id=storage_service_id,
        start_date=start_date,
        end_date=end_date,
        storage_location_id=storage_location_id,
    )

    if csv:
        headers = translate_headers(CSV_HEADERS, True)

        filename = "aip_contents.csv"
        aips = _create_aip_formats_string_representation(
            aip_data.get(fields.FIELD_AIPS), separator="|"
        )
        csv_data = format_size_for_csv(aips)
        return download_csv(headers, csv_data, filename)

    aips = _create_aip_formats_string_representation(aip_data.get(fields.FIELD_AIPS))

    headers = translate_headers(TABLE_HEADERS)

    return render_template(
        "report_aip_contents.html",
        storage_service=storage_service_id,
        storage_service_name=aip_data.get(fields.FIELD_STORAGE_NAME),
        storage_location_description=aip_data.get(fields.FIELD_STORAGE_LOCATION),
        columns=headers,
        aips=aip_data.get(fields.FIELD_AIPS),
        start_date=start_date,
        end_date=get_display_end_date(end_date),
    )
