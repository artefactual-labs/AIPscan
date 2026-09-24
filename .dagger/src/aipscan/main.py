"""Run the real Archivematica-to-AIPscan reporting workflow."""

from typing import Annotated

import dagger
from dagger import dag


@dagger.object_type
class Aipscan:
    @dagger.function
    async def test_end_to_end(
        self,
        source: Annotated[
            dagger.Directory,
            dagger.DefaultPath("/"),
            dagger.Ignore(
                [
                    ".git",
                    ".venv",
                    ".tox",
                    "node_modules",
                    "output",
                    ".dagger/sdk",
                    ".mypy_cache",
                    ".ruff_cache",
                    "dist",
                    "AIPscan/static/dist",
                ]
            ),
        ],
    ) -> str:
        """Import modern and production legacy AIPs, then check reports and charts."""
        node_version = (await source.file(".node-version").contents()).strip()
        frontend = (
            dag.container()
            .from_(f"node:{node_version}")
            .with_workdir("/app")
            .with_file("package.json", source.file("package.json"))
            .with_file("package-lock.json", source.file("package-lock.json"))
            .with_exec(["npm", "ci"])
            .with_directory("/app", source)
            .with_exec(["npm", "run", "build"])
        )
        mysql = (
            dag.container()
            .from_("percona/percona-server:8.4.11-11.1")
            .with_env_variable("MYSQL_ROOT_PASSWORD", "12345")
            .with_mounted_temp("/var/lib/mysql", size=1024 * 1024 * 1024)
            .with_user("root")
            .with_directory(
                "/docker-entrypoint-initdb.d", source.directory(".init-scripts/mysql")
            )
            .with_exposed_port(3306)
            .as_service(
                args=[
                    "bash",
                    "-ec",
                    "chown mysql:mysql /var/lib/mysql; exec /docker-entrypoint.sh mysqld --user=mysql",
                ]
            )
        )
        rabbitmq = (
            dag.container()
            .from_("rabbitmq:4.3.6-management")
            # Celery control queues still use transient non-exclusive queues.
            .with_new_file(
                "/etc/rabbitmq/conf.d/20-aipscan.conf",
                "deprecated_features.permit.transient_nonexcl_queues = true\n",
            )
            .with_exposed_port(5672)
            .as_service()
        )
        ambox = (
            dag.container()
            .from_("ghcr.io/sevein/ambox:1.2.1")
            .with_file(
                "/legacy.xml",
                source.file(
                    "AIPscan/Aggregator/tests/fixtures/legacy_mets/production-aip-mets-file.xml"
                ),
            )
            .with_file("/create_legacy.py", source.file("tests/e2e/create_legacy.py"))
            .with_exec(["python3", "/create_legacy.py"])
            .with_new_file(
                "/home/archivematica/transfers/aipscan-e2e/hello.txt",
                "AIPscan end-to-end test.\n",
                owner="1000:1000",
            )
            .with_new_file(
                "/etc/ambox/config.yaml",
                "version: v1\nprocessing:\n  configs:\n    - name: automated\n"
                "      extends: automated\n      config:\n"
                "        normalize: do_not_normalize\n        virus_scanning: false\n",
            )
            .with_exposed_port(64080)
            .with_exposed_port(64081)
            .as_service(no_init=True)
        )
        dependencies = (
            dag.container()
            .from_("ghcr.io/astral-sh/uv:0.12.21-python3.14-trixie-slim")
            .with_workdir("/app")
            .with_env_variable("HATCH_BUILD_NO_HOOKS", "1")
            .with_env_variable("SETUPTOOLS_SCM_PRETEND_VERSION", "1.0.0dev")
            .with_env_variable("UV_PROJECT_ENVIRONMENT", "/venv")
            .with_env_variable("PATH", "/venv/bin:$PATH", expand=True)
            .with_file("pyproject.toml", source.file("pyproject.toml"))
            .with_file("uv.lock", source.file("uv.lock"))
            .with_file(".python-version", source.file(".python-version"))
            .with_exec(
                [
                    "uv",
                    "sync",
                    "--locked",
                    "--no-dev",
                    "--extra",
                    "server",
                    "--no-install-project",
                ]
            )
        )
        application = (
            dependencies.with_directory("/app", source)
            .with_exec(["uv", "sync", "--locked", "--no-dev", "--extra", "server"])
            .with_directory(
                "/app/AIPscan/static/dist",
                frontend.directory("/app/AIPscan/static/dist"),
            )
            .with_env_variable("FLASK_APP", "AIPscan:create_app")
        )
        app = (
            application.with_service_binding("mysql", mysql)
            .with_service_binding("rabbitmq", rabbitmq)
            .with_service_binding("ambox", ambox)
            .with_env_variable("FLASK_CONFIG", "dev")
            .with_env_variable(
                "SQLALCHEMY_DATABASE_URI", "mysql+pymysql://aipscan:demo@mysql/aipscan"
            )
            .with_env_variable(
                "CELERY_RESULT_BACKEND", "db+mysql+pymysql://aipscan:demo@mysql/celery"
            )
            .with_env_variable("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq//")
            .with_env_variable("AGGREGATOR_DOWNLOAD_ROOT", "/downloads")
        )
        # Web and worker share the download directory, as in the Compose stack.
        # Initialize the database at service startup: cached build steps cannot
        # preserve side effects in the database service's temporary filesystem.
        service = app.with_exposed_port(5000).as_service(
            args=["bash", "tests/e2e/start.sh"]
        )
        return await (
            dependencies.with_exec(
                [
                    "uv",
                    "sync",
                    "--locked",
                    "--no-dev",
                    "--extra",
                    "server",
                    "--group",
                    "e2e",
                    "--no-install-project",
                ]
            )
            .with_exec(["playwright", "install", "--with-deps", "chromium"])
            .with_directory("/e2e", source.directory("tests/e2e"))
            .with_service_binding("aipscan", service)
            .with_service_binding("ambox", ambox)
            .with_exec(["python", "-u", "/e2e/run.py"])
            .stdout()
        )
