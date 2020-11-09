# AIPscan production installation

AIPscan is a Python [Flask][fla-1] application. The Flask Werkzeug development
server is not recommended for use in production. Instead, a WSGI and HTTP proxy
server should be used to serve the AIPscan application. We recommend
[Gunicorn][gun-1] and [Nginx][ngx-1] respectively. The following instructions
are for production deployment to an Ubuntu/Debian server. Other operating
systems and servers have not been tested.

### AIPScan Flask server

* Clone files and cd to directory:  `git clone https://github.com/artefactual-labs/AIPscan && cd AIPscan`
* Set up virtualenv in the project root directory: `virtualenv venv`
* Activate virtualenv: `source venv/bin/activate`
* Install requirements (this includes Flask, Celery, and Gunicorn): `pip install -r requirements/base.txt`
* Create AIPscan and Celery databases: `python create_aipscan_db.py`

### RabbitMQ

* [Install][rabbit-MQ1] the RabbitMQ package:

  ```bash
  sudo apt-get update -y
  sudo apt-get install -y rabbitmq-server
  ```

### Gunicorn service

* Create the following service file for Gunicorn:

```bash
sudo nano /etc/systemd/system/aipscan.service
```

* Add and save the following content to this file. Replace the
`home/artefactual/AIPscan` paths to match the directory where you have
installed AIPscan (e.g. `/home/ubuntu/AIPscan`).

```bash
[Unit]
Description=Gunicorn instance to serve AIPscan
After=network.target

[Service]
User=artefactual
Group=www-data

WorkingDirectory=/home/artefactual/AIPscan
Environment="PATH=/home/artefactual/AIPscan/venv/bin"
ExecStart=/home/artefactual/AIPscan/venv/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
```

* Start the new AIPscan Gunicorn service:

```bash
sudo systemctl start aipscan
sudo systemctl enable aipscan
```

* Check that it is running correctly:

```bash
sudo systemctl status aipscan
```
* You should see output that looks like:

```bash
● aipscan.service - Gunicorn instance to serve AIPscan
   Loaded: loaded (/etc/systemd/system/aipscan.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2020-11-04 21:18:30 UTC; 3h 4min ago
 Main PID: 25278 (gunicorn)
    Tasks: 4 (limit: 4915)
   CGroup: /system.slice/aipscan.service
           ├─25278 /home/artefactual/AIPscan/venv/bin/python3 /home/artefactual/AIPscan/venv/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
           ├─25301 /home/artefactual/AIPscan/venv/bin/python3 /home/artefactual/AIPscan/venv/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
           ├─26969 /home/artefactual/AIPscan/venv/bin/python3 /home/artefactual/AIPscan/venv/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
           └─26985 /home/artefactual/AIPscan/venv/bin/python3 /home/artefactual/AIPscan/venv/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
```

### Nginx web server

* Install Nginx.

```bash
sudo apt update
sudo apt install nginx
```

* Configure a Nginx server block for the AIPscan application. Again, replace
the `/home/artefactual/AIPscan/aipscan.sock` path with the path to your
AIPscan root directory (e.g. `/home/ubuntu/AIPscan/aipscan.sock`).

```bash
sudo nano /etc/nginx/sites-available/aipscan
```

* Add the following content to this file and save.

```bash
server {
    listen 80;
    server_name your.aipscan.server.ip.here;

    location / {
        satisfy all;

        include proxy_params;
        proxy_pass http://unix:/home/artefactual/AIPscan/aipscan.sock;
    }
}
```

* Create the symlink to enable this Nginx configuration:

```bash
sudo ln -s /etc/nginx/sites-available/aipscan /etc/nginx/sites-enabled
```

* Confirm that the Nginx configuration is correct:

```bash
sudo nginx -t
```

* You should see:

```bash
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

* Don't forget to [enable your firewall][ufw-1] to protect the application:

```bash
sudo ufw status
```

* Also, be sure to restart Nginx anytime you make any changes to the server
block:

```bash
sudo systemctl restart nginx
```

### Celery service

* AIPscan uses Celery workers, coordinated by RabbitMQ to run background jobs.
To run Celery as a persistent service, create the following file:

```bash
/etc/systemd/system/celery.service
```

* Add and save the following content, again replacing the 
`/home/artefactual/AIPscan` path to match the root directory of your AIPscan
installation (e.g. `/home/ubuntu/AIPscan/`)

```bash
[Unit]
Description=Celery worker service for AIPscan
After=network.target

[Service]
User=artefactual

WorkingDirectory=/home/artefactual/AIPscan
Environment="PATH=/home/artefactual/AIPscan/venv/bin"
ExecStart=/home/artefactual/AIPscan/venv/bin/celery -A AIPscan.Aggregator.tasks worker

[Install]
WantedBy=multi-user.target
```

* Start the Celery service:

```bash 
sudo systemctl start celery
sudo systemctl enable celery
```

* Confirm that the service is working correctly:

```bash
sudo systemctl status celery
```

* You should output like this:

```bash
● celery.service - Celery worker service for AIPscan
   Loaded: loaded (/etc/systemd/system/celery.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2020-11-04 22:52:50 UTC; 1h 51min ago
 Main PID: 26842 (celery)
    Tasks: 3 (limit: 4915)
   CGroup: /system.slice/celery.service
           ├─26842 /home/artefactual/AIPscan/venv/bin/python3 /home/artefactual/AIPscan/venv/bin/celery -A AIPscan.Aggregator.tasks worker
           ├─26860 /home/artefactual/AIPscan/venv/bin/python3 /home/artefactual/AIPscan/venv/bin/celery -A AIPscan.Aggregator.tasks worker
           └─26861 /home/artefactual/AIPscan/venv/bin/python3 /home/artefactual/AIPscan/venv/bin/celery -A AIPscan.Aggregator.tasks worker
```

### Conclusion
If all these steps were successful, you should now have a robust, production
ready AIPscan service running at `your.aipscan.server.ip`.

[rabbit-MQ1]: https://www.rabbitmq.com/install-debian.html
[usage-1]: http://localhost:5000
[fla-1]: https://flask.palletsprojects.com
[gun-1]: https://gunicorn.org/
[ngx-1]: https://www.nginx.com/
[ufw-1]: https://wiki.ubuntu.com/UncomplicatedFirewall