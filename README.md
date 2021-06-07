[![GitHub CI](https://github.com/artefactual-labs/AIPscan/actions/workflows/test.yml/badge.svg)](https://github.com/artefactual-labs/AIPscan/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/artefactual-labs/AIPscan/branch/main/graph/badge.svg?token=2RRFAM8P89)](https://codecov.io/gh/artefactual-labs/AIPscan)


# About

AIPscan was developed to provide a more in-depth reporting solution for Archivematica users. It crawls METS files from AIPs in the Archivematica Storage Service to generate tabular and visual reports about repository holdings. It is designed to run as a stand-alone add-on to Archivematica. It only needs a valid Storage Service API key to fetch source data.

# License

[Apache License Version 2.0](LICENSE)  
Copyright Artefactual Systems Inc (2021)

# Contents
* [Screenshots](#screenshots)
* [Installation](#installation)
* [Usage](#usage)

## Screenshots

### AIPScan fetch job

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

AIPscan is a web-based application that is built using the Python [Flask](https://pypi.org/project/Flask/) micro-framework. Below are the developer quickstart instructions. See [INSTALL](INSTALL.md) for production deployment instructions.

## AIPScan Flask server

* Clone files and cd to directory:  `git clone https://github.com/artefactual-labs/AIPscan && cd AIPscan`
* Set up virtualenv in the project root directory: `virtualenv venv`
* Activate virtualenv: `source venv/bin/activate`
* Install requirements (this includes Flask & Celery): `pip install -r requirements/base.txt`
* Enable DEBUG mode if desired for development: `export FLASK_CONFIG=dev`
* In a terminal window, start the Flask server: `python run.py`
* Confirm that the Flask server and AIPscan application are up and running at [`localhost:5000`][usage-1] in your browser.. You should see a blank AIPscan page like this:

![screencap5](screencaps/aipscan_hello_world.png)


## Background workers
Crawling and parsing many Archivematica AIP METS xml files at a time is resource intensive. Therefore, AIPscan uses the [RabbitMQ][rabbit-MQ1] message broker and the [Celery][celery-1] task manager to coordinate this activity as background worker tasks. **Both RabbitMQ and Celery must be running properly before attempting a METS fetch job.**


## RabbitMQ
You can downnload and install RabbitMQ server directly on your local or cloud machine or you can run it in either location from a Docker container.


### Docker installation


  ```
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
* AIPScan connects to the RabbitMQ queue on port `:5672`.


## Celery
Celery is installed as a Python module dependency during the initial AIPscan requirements import command: `pip install -r requirements.txt`

To start up Celery workers that are ready to receive tasks from RabbitMQ:
* Open a new terminal tab or window.
* Navigate to the AIPscan root project directory.
* Activate the Python virtualenv in the AIPscan project directory so that the Celery dependency gets automatically loaded: 
  `source venv/bin/activate`
* Enter the following command:  
  `celery worker -A AIPscan.worker.celery --loglevel=info`
* You should see terminal output similar to this to indicate that the Celery task queu is ready:

![screencap6](screencaps/aipscan_celery_hello_world.png)

# Usage

* Ensure that the Flask Server, RabbitMQ server, and Celery worker queue are up and running.
* Go to [`localhost:5000`][usage-1] in your browser.
* Select "New Storage Service"
* Add an Archivematica Storage Service record, including API Key, eg.
`https://amdemo.artefactual.com:8000`
* Select "New Fetch Job"
* Check the black and green terminal to confirm that AIPscan successfully connected to the Archivematica Storage Service, that it received the lists of available packages from Archivematica, and that it has begun downloading and parsing the AIP METS files.
* This could take a while (i.e. a few hours) depending on the total number of AIPs in your Storage Service and the size of your METS xml files. Therefore, if you have the option, it is recommended that you test AIPscan on a smaller subset of your full AIP holdings first. This should help you estimate the total time to run AIPscan against all packages in your Storage Service.
* When the Fetch Job completes, select "View AIPs" button, "AIPs" menu, or "Reports" menu to view all the interesting information about your Archivematica content in a variety of layouts.

[am-1]: https://archivematica.org
[rabbit-MQ1]: https://www.rabbitmq.com/
[celery-1]: https://docs.celeryproject.org/en/stable/getting-started/introduction.html
[rabbit-MQ2]: http://localhost:15672/
[rabbit-MQ3]: https://www.rabbitmq.com/download.html
[usage-1]: http://localhost:5000
