# AIPscan
Collect and view repository-wide info about Archivematica AIPs

* Clone files and cd to directory:  
  `git clone https://github.com/peterVG/AIPscan && cd AIPscan`  
* Set up virtualenv:  
  `virtualenv venv`  
* Activate virtualenv:  
  `source venv/bin/activate`  
* Install requirements:  
  `pip install -r requirements.txt`   
* Create database:  
  `python create_db.py`      
* In a terminal window, run
  `export FLASK_APP=run.py`  
  `flask run`  
* In another terminal window, start a Celery worker
  `celery -A AIPscan.tasks worker`
* In another terminal window, start RabbitMQ queue manager
  `export PATH=$PATH:/usr/local/sbin`
  `rabbitmq-server`

* Go to `localhost:5000` in browser.
* Select "New Storage Service"  
* Add an Archivematica Storage Service record, including API Key, eg.  
`https://amdemo.artefactual.com:8000`
* Select "New Fetch Job"
* Select "View AIPs"
