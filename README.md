# AIPscan
View repository-wide info about Archivematica AIPs

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
* Run (on localhost, port 5000):  
  `export FLASK_APP=run.py`  
  `flask run`  
* Go to `localhost:5000` in browser.
* Select "New Storage Service"  
* Add an Archivematica Storage Service record, including API Key, eg.  
`https://amdemo.artefactual.com:8000`
* Select "New Fetch Job"
* See CLI for Fetch Job status
* See UI for new Fetch Job when complete
* Select "View AIPs"
