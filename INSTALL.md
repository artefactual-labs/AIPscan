# AIPscan production installation

AIPscan is deployed as a small distributed system centred on a Python Flask web
application. A production deployment combines the following services:

- **Web application service** – The Flask app runs under Gunicorn, with Nginx
  terminating TLS, proxying HTTP traffic, and serving static assets to end
  users.
- **Background worker service** – A dedicated Celery worker processes
  harvesting, indexing, and reporting tasks asynchronously so the web layer
  stays responsive.
- **Message broker** – RabbitMQ coordinates task distribution between the web
  service and Celery worker, providing durable queues and predictable
  throughput.
- **Database backend** – MySQL stores all AIPscan state while also acting as the
  Celery result backend, ensuring a single authoritative datastore.
- **Optional search accelerator** – Typesense can be enabled to index report
  data after each fetch, allowing the application to produce complex reports
  without stressing MySQL.

While other technologies could theoretically replace individual components
(e.g., Redis instead of RabbitMQ, or a different SQL engine), these combinations
are not part of our test matrix. For predictable upgrades and support, we
strongly recommend adhering to the reference architecture described above.

## Reference deployment

The supported reference deployment is managed through Ansible. For detailed
configuration guidance and environment-specific variables, consult the official
[AIPscan Ansible role].

We don't currently maintain a production-ready container-orchestrated deployment
(e.g., Kubernetes). However, the repository's [docker-compose.yml] defines our
standard development stack and can serve as a useful reference when planning
your own containerized setup.

## Recommended practices

- Treat the [published AIPscan wheel](https://pypi.org/project/aipscan/) as the
  authoritative distribution. Install the package from PyPI when bootstrapping
  your Python environment.
- Expect occasional breaking changes while the project remains in the 0.x
  series. For example, version 0.9.0 removes SQLite support even though it had
  previously been the default database backend.

## Troubleshooting

### Workers are using too much memory and being terminated

Please review the [Celery Workers Guide] for tuning options that help keep
AIPscan workers stable in production.The `--max-memory-per-child` flag is often
helpful for recycling workers once they reach a specified memory limit. For
instance, `--max-memory-per-child 1048576` will recycle a worker after it uses
about 1 GB of RAM (Celery expects the value in kilobytes, so 1024 × 1024 =
1048576 KB).

[AIPscan Ansible role]: https://github.com/artefactual-labs/ansible-aipscan
[docker-compose.yml]: ./docker-compose.yml
[Celery Workers Guide]: https://docs.celeryproject.org/en/stable/userguide/workers.html#worker-concurrency
