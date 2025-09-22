# AIPscan production installation

AIPscan is a Python [Flask][fla-1] application. The Flask Werkzeug development
server is not recommended for use in production. Instead, a WSGI and HTTP proxy
server should be used to serve the AIPscan application. We recommend
[Gunicorn][gun-1] and [Nginx][ngx-1] respectively. The following instructions
are for production deployment to an Ubuntu/Debian server. Other operating
systems and servers have not been tested.

## AIPScan Flask server

Install [uv] and [Node LTS] on the server before continuing.

* Move to project directory: `cd /usr/share/archivematica`
* Clone files to directory: `git clone https://github.com/artefactual-labs/AIPscan
  /usr/share/archivematica/AIPscan`
* Change into the project directory: `cd /usr/share/archivematica/AIPscan`
* Configure uv to use a shared virtual environment directory for AIPscan:
  `export UV_PROJECT_ENVIRONMENT=/usr/share/archivematica/virtualenvs/AIPscan`
  (re-export this variable in future shells when running `uv` commands)
* Install the runtime dependencies (uv will create the environment at that
  path if it does not already exist): `uv sync --no-dev --extra server`
* Bundle static assets: `npm run build`

## RabbitMQ

* [Install][rabbit-MQ1] the RabbitMQ package:

  ```bash
  sudo apt-get update -y
  sudo apt-get install -y rabbitmq-server
  ```

* Start the RabbitMQ service:

   ```bash
   sudo service rabbitmq-server start
   ```

* Check that it is running correctly:

   ```bash
   sudo service rabbitmq-server status
   ```

* You should see output that looks like this:

   ```bash
   Loaded: loaded (/lib/systemd/system/rabbitmq-server.service; enabled; vendor preset: enabled)
   Active: active (running) since Tue 2021-02-02 23:02:36 UTC; 6min ago
   Process: 3356 ExecStop=/bin/sh -c while ps -p $MAINPID >/dev/null 2>&1; do sleep 1; done (code=exited, status=0/SUCCESS)
   Process: 3208 ExecStop=/usr/lib/rabbitmq/bin/rabbitmqctl stop (code=exited, status=0/SUCCESS)
   Main PID: 3403 (beam.smp)
   Status: "Initialized"
   Tasks: 86 (limit: 4915)
   CGroup: /system.slice/rabbitmq-server.service
           ├─3403 /usr/lib/erlang/erts-9.2/bin/beam.smp -W w -A 64 -P 1048576 -t 5000000 -stbt db -zdbbl 128000 -K true -- -root /usr/lib/erlang -progname erl -- -home /var/lib/rabbitmq -- -pa /usr/lib/rabbitmq/lib/rabbitmq_server-3.6.16/ebin -noshell -noinput -s rabbit boot -sname rabbit@
           ├─3500 /usr/lib/erlang/erts-9.2/bin/epmd -daemon
           ├─3645 erl_child_setup 1024
           ├─3670 inet_gethost 4
           └─3671 inet_gethost 4

* If you need to stop it for any reason:

   ```bash
   sudo service rabbitmq-server stop
   ```

## Typesense (optional)

Typesense doesn't yet exist in major Linux distribution package repositories and
has to be installed manually.

Official installation instructions are available for [Ubuntu][1] and [Centos/RHEL][2].

[1]: https://typesense.org/docs/guide/install-typesense.html#deb-package-on-ubuntu-debian

[2]: https://typesense.org/docs/guide/install-typesense.html#rpm-package-on-centos-rhel

After installing Typesense the API key, needed to enable Typesense
functionality in AIPscan, can be found in the
`/etc/typesense/typesense-server.ini` file.

## Gunicorn service

* Create the following service file for Gunicorn:

```bash
sudo nano /etc/systemd/system/aipscan.service
```

* Add and save the following content to this file.

```bash
[Unit]
Description=Gunicorn instance to serve AIPscan
After=network.target

[Service]
User=archivematica
Group=archivematica
WorkingDirectory=/usr/share/archivematica/AIPscan
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/share/archivematica/virtualenvs/AIPscan/bin/gunicorn --preload --workers 3 --bind unix:aipscan.sock "AIPscan:create_app()"
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
PrivateTmp=true
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

If you wish to use Typesense with AIPscan, you'll need to define an environment variable
in the `[Service]` section of this file. For example:

```bash
Environment="TYPESENSE_API_KEY=1234"
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
           ├─25278 /usr/share/archivematica/virtualenvs/AIPscan/bin/python3 /usr/share/archivematica/virtualenvs/AIPscan/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
           ├─25301 /usr/share/archivematica/virtualenvs/AIPscan/bin/python3 /usr/share/archivematica/virtualenvs/AIPscan/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
           ├─26969 /usr/share/archivematica/virtualenvs/AIPscan/bin/python3 /usr/share/archivematica/virtualenvs/AIPscan/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
           └─26985 /usr/share/archivematica/virtualenvs/AIPscan/bin/python3 /usr/share/archivematica/virtualenvs/AIPscan/bin/gunicorn --workers 3 --bind unix:aipscan.sock -m 007 wsgi:app
```

## Nginx web server

* Install Nginx.

```bash
sudo apt update
sudo apt install nginx
```

* Configure a Nginx server block for the AIPscan application.

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
        proxy_pass http://unix:/usr/share/archivematica/AIPscan/aipscan.sock;
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

## Celery service

* AIPscan uses Celery workers, coordinated by RabbitMQ to run background jobs.
To run Celery as a persistent service, create the following file:

```bash
/etc/systemd/system/celery.service
```

* Add and save the following content:

```bash
[Unit]
Description=Celery worker service for AIPscan
After=network.target

[Service]
User=archivematica

WorkingDirectory=/usr/share/archivematica/AIPscan
ExecStart=/usr/share/archivematica/virtualenvs/AIPscan/bin/celery -A AIPscan.worker.celery worker
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
PrivateTmp=true
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

If you wish to use Typesense with AIPscan, you'll need to define an environment variable
in the `[Service]` section of this file. For example:

```bash
Environment="TYPESENSE_API_KEY=1234"
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
           ├─26842 /usr/share/archivematica/virtualenvs/AIPscan/bin/python3 /usr/share/archivematica/virtualenvs/AIPscan/bin/celery -A AIPscan.worker.celery worker
           ├─26860 /usr/share/archivematica/virtualenvs/AIPscan/bin/python3 /usr/share/archivematica/virtualenvs/AIPscan/bin/celery -A AIPscan.worker.celery worker
           └─26861 /usr/share/archivematica/virtualenvs/AIPscan/bin/python3 /usr/share/archivematica/virtualenvs/AIPscan/bin/celery -A AIPscan.worker.celery worker
```

## Conclusion

If all these steps were successful, you should now have a robust, production
ready AIPscan service running at `your.aipscan.server.ip`.

[uv]: (https://docs.astral.sh/uv/getting-started/installation/)
[Node LTS]: https://nodejs.org/en/download
[rabbit-MQ1]: https://www.rabbitmq.com/install-debian.html
[fla-1]: https://flask.palletsprojects.com
[gun-1]: https://gunicorn.org/
[ngx-1]: https://www.nginx.com/
[ufw-1]: https://wiki.ubuntu.com/UncomplicatedFirewall
