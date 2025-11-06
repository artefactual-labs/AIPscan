# AIPscan

By [Artefactual]

[![PyPI version][badge-pypi]][pypi-release]
[![GitHub CI][badge-ci]][test-workflow]
[![codecov][badge-codecov]][codecov-report]

AIPscan provides an in-depth reporting solution for Archivematica users. It
crawls METS files from AIPs in the Archivematica Storage Service to generate
tabular and visual reports about repository holdings. It is designed to run as a
stand-alone add-on to Archivematica and requires only a valid Storage Service
API key to fetch source data.

## Screenshots

<details>
<summary>Running a fetch job</summary>

![AIPscan fetch job](screencaps/aipscan_fetch_job.png)
</details>

<details>
<summary>Finding an AIP</summary>

![Finding an AIP](screencaps/aipscan_find_aip.png)
</details>

<details>
<summary>Viewing an AIP</summary>

![Viewing an AIP](screencaps/aipscan_view_aip.png)
</details>

<details>
<summary>Selecting a report</summary>

![Selecting a report](screencaps/aipscan_select_report.png)
</details>

<details>
<summary>Example: pie chart "format types" report</summary>

![Pie chart "format types" report](screencaps/aipscan_piechart_report.png)
</details>

<details>
<summary>Example: tabular "largest files" report</summary>

![Tabular "largest files" report](screencaps/aipscan_tabular_report.png)
</details>

## Installation

AIPscan is a web-based application that is built using the Python [Flask]
micro-framework. See [INSTALL.md] for production deployment instructions. See
[CONTRIBUTING.md] for guidelines on how to contribute to the project, including
how to set up the development environment and create a new AIPscan report.

## Usage

Consult [USAGE.md] for a walkthrough of the web workflow and the helper scripts
in the `tools` directory. It covers verifying your deployment, running fetch
jobs, and seeding test data.

## Contributing

See [CONTRIBUTING.md] for full contribution guidelines and
development environment setup instructions.

## License

This project is licensed under the Apache-2.0 license ([LICENSE] or
<https://opensource.org/licenses/Apache-2.0>).

[badge-pypi]: https://badge.fury.io/py/aipscan.svg
[pypi-release]: https://badge.fury.io/py/aipscan
[badge-ci]: https://github.com/artefactual-labs/AIPscan/actions/workflows/test.yml/badge.svg
[test-workflow]: https://github.com/artefactual-labs/AIPscan/actions/workflows/test.yml
[badge-codecov]: https://codecov.io/gh/artefactual-labs/AIPscan/branch/main/graph/badge.svg
[codecov-report]: https://codecov.io/gh/artefactual-labs/AIPscan
[Artefactual]: https://www.artefactual.com/
[Flask]: https://pypi.org/project/Flask/
[LICENSE]: LICENSE
[INSTALL.md]: INSTALL.md
[CONTRIBUTING.md]: CONTRIBUTING.md
[USAGE.md]: USAGE.md
