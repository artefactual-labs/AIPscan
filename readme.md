# AIPscan
Collect repository-wide info about [Archivematica](https://archivematica.org) Archival Information Packages (AIPs)

![screencap1](screencaps/aipscan_fetch_job.png)

![screencap2](screencaps/aipscan_view_aip.png)

![screencap3](screencaps/aipscan_select_report.png)

![screencap4](screencaps/aipscan_piechart_report.png)


# Installation

* Clone files and cd to directory:  
  `git clone https://github.com/peterVG/AIPscan && cd AIPscan`  
* Set up virtualenv in the project root directory:  
  `virtualenv venv`  
* Activate virtualenv:  
  `source venv/bin/activate`  
* Install requirements (this includes Flask & Celery)  
  `pip install -r requirements.txt`   
* Create database:  
  `python create_aipscan_db.py`      
* In a terminal window, start the Flask server:  
  `python run.py`
* In another terminal window, from the same root directory, start a Celery worker:  
  `celery -A AIPscan.Aggregator.tasks worker --loglevel=info`  
* Download and install RabbitMQ queue manager:  
  https://www.rabbitmq.com/download.html
* In another terminal window, start RabbitMQ queue manager  
  `export PATH=$PATH:/usr/local/sbin`  
  `sudo rabbitmq-server`
* To see RabbitMQ dashboard visit:  
  http://localhost:15672/  
  un: guest, pw: guest

* Go to `localhost:5000` in browser.
* Select "New Storage Service"  
* Add an Archivematica Storage Service record, including API Key, eg.  
 `https://amdemo.artefactual.com:8000`
* Select "New Fetch Job"
* When Fetch Job completes, select "View AIPs"
