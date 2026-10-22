"""Run the real Archivematica-to-AIPscan reporting workflow."""

from typing import Annotated
from uuid import uuid4

import dagger
from dagger import dag

SOURCE = Annotated[
    dagger.Directory,
    dagger.DefaultPath("/"),
    dagger.Ignore(
        [
            ".git",
            ".venv",
            ".tox",
            "node_modules",
            "output",
            "tmp.ignored",
            ".dagger",
            ".env",
            ".env.*",
            ".uv-cache",
            ".vscode",
            "AIPscan/Aggregator/downloads",
            ".mypy_cache",
            ".ruff_cache",
            "**/.pytest_cache",
            "**/__pycache__",
            "**/*.pyc",
            "dist",
            "AIPscan/static/dist",
        ]
    ),
]


@dagger.object_type
class Aipscan:
    @dagger.function(cache="session")
    @dagger.check
    async def test_end_to_end(
        self,
        source: SOURCE,
        release: bool = True,
        distribution: dagger.Directory | None = None,
        indexed: bool = False,
    ) -> str:
        """Import modern and legacy AIPs, then verify reports and charts."""
        runner = await self._acceptance_runner(source, release, distribution, indexed)
        result = await runner.file("/artifacts/pytest.log").contents()
        if await runner.exit_code() != 0:
            raise RuntimeError(result)
        return result

    @dagger.function(cache="session")
    async def test_results(
        self,
        source: SOURCE,
        release: bool = True,
        distribution: dagger.Directory | None = None,
        indexed: bool = False,
    ) -> dagger.Directory:
        """Return logs, JUnit, and failed-browser traces, even when tests fail."""
        runner = await self._acceptance_runner(source, release, distribution, indexed)
        status = await runner.exit_code()
        return runner.directory("/artifacts").with_new_file("exit-code", str(status))

    @dagger.function(cache="session")
    @dagger.check
    async def test_indexed_reports(self, source: SOURCE) -> str:
        """Verify real Typesense indexing against SQL reports and browser charts."""
        return await self.test_end_to_end(source, indexed=True)

    async def _acceptance_runner(
        self,
        source: dagger.Directory,
        release: bool,
        distribution: dagger.Directory | None,
        indexed: bool,
    ) -> dagger.Container:
        run_id = uuid4().hex
        node_version = (await source.file(".node-version").contents()).strip()
        frontend = (
            dag.container()
            .from_(f"node:{node_version}")
            .with_workdir("/app")
            .with_file("package.json", source.file("package.json"))
            .with_file("package-lock.json", source.file("package-lock.json"))
            .with_mounted_cache("/root/.npm", dag.cache_volume("aipscan-npm"))
            .with_exec(["npm", "ci"])
            .with_directory("/app/build_config", source.directory("build_config"))
            .with_directory("/app/AIPscan/static", source.directory("AIPscan/static"))
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
            .with_env_variable("AIPSCAN_TEST_RUN", run_id)
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
            .from_("rabbitmq:4.4.0-management")
            .with_mounted_temp("/var/lib/rabbitmq", size=128 * 1024 * 1024)
            .with_env_variable("RABBITMQ_NODENAME", "rabbit@localhost")
            # Celery control queues still use transient non-exclusive queues.
            .with_new_file(
                "/etc/rabbitmq/conf.d/20-aipscan.conf",
                "deprecated_features.permit.transient_nonexcl_queues = true\n",
            )
            .with_env_variable("AIPSCAN_TEST_RUN", run_id)
            .with_exposed_port(5672)
            .as_service()
        )
        ambox_files = (
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
            .with_env_variable("AIPSCAN_TEST_RUN", run_id)
            .with_exposed_port(64080)
            .with_exposed_port(64081)
        )
        ambox = ambox_files.as_service(no_init=True)
        python_base = (
            dag.container()
            .from_("ghcr.io/astral-sh/uv:0.13.5-trixie-slim")
            .with_workdir("/app")
            .with_env_variable("HATCH_BUILD_NO_HOOKS", "1")
            .with_env_variable("SETUPTOOLS_SCM_PRETEND_VERSION", "1.0.0dev")
            .with_env_variable("UV_PROJECT_ENVIRONMENT", "/venv")
            .with_env_variable("PATH", "/venv/bin:$PATH", expand=True)
            .with_env_variable("UV_LINK_MODE", "copy")
            .with_mounted_cache("/root/.cache/uv", dag.cache_volume("aipscan-uv"))
            .with_file("pyproject.toml", source.file("pyproject.toml"))
            .with_file("uv.lock", source.file("uv.lock"))
            .with_file(".python-version", source.file(".python-version"))
            .with_exec(["uv", "venv", "--managed-python", "/venv"])
        )
        fault_storage = (
            python_base.with_file(
                "/fault_storage.py", source.file("tests/e2e/fault_storage.py")
            )
            .with_file(
                "/legacy.xml",
                source.file(
                    "AIPscan/Aggregator/tests/fixtures/legacy_mets/production-aip-mets-file.xml"
                ),
            )
            .with_file(
                "/images.xml",
                source.file("AIPscan/Aggregator/tests/fixtures/images_mets/images.xml"),
            )
            .with_env_variable("AIPSCAN_TEST_RUN", run_id)
            .with_exposed_port(8000)
            .as_service(args=["python", "/fault_storage.py"])
        )
        application = (
            python_base.with_directory(
                "/app",
                source,
                include=["AIPscan/**", "README.md", "LICENSE", "build.py"],
                exclude=["**/tests/**"],
            )
            .with_directory(
                "/app/AIPscan/static/dist",
                frontend.directory("/app/AIPscan/static/dist"),
            )
            .with_env_variable("FLASK_APP", "AIPscan:create_app")
        )
        if release:
            if distribution is None:
                distribution = application.with_exec(
                    ["uv", "build", "--wheel", "--out-dir", "/dist"]
                ).directory("/dist")
            wheels = await distribution.glob("*.whl")
            if len(wheels) != 1:
                raise ValueError(
                    "Provide a distribution directory with exactly one wheel"
                )
            python_version = (await source.file(".python-version").contents()).strip()
            application = (
                source.with_directory("dist", distribution)
                .docker_build(
                    target="release",
                    build_args=[
                        dagger.BuildArg(name="WHEEL", value=wheels[0]),
                        dagger.BuildArg(name="PYTHON_VERSION", value=python_version),
                    ],
                )
                .with_exec(
                    [
                        "python",
                        "-c",
                        "import AIPscan, os; assert os.getuid() != 0; "
                        "assert '/site-packages/' in AIPscan.__file__, AIPscan.__file__",
                    ]
                )
            )
        else:
            application = application.with_exec(
                ["uv", "sync", "--locked", "--no-dev", "--extra", "server"]
            )
        application = (
            application.with_file("/e2e/start.sh", source.file("tests/e2e/start.sh"))
            .with_file("/e2e/web.py", source.file("tests/e2e/web.py"))
            .with_directory(
                "/downloads",
                dag.directory().with_new_file(".keep", ""),
                owner="aipscan" if release else "root",
            )
            .with_mounted_temp("/tmp", size=256 * 1024 * 1024)
        )
        app = (
            application.with_service_binding("mysql", mysql)
            .with_service_binding("rabbitmq", rabbitmq)
            .with_service_binding("ambox", ambox)
            .with_service_binding("fault-storage", fault_storage)
            # Function caching and container-step caching are independent.
            # Keep builds reusable, but execute tests once per client session.
            .with_env_variable("AIPSCAN_TEST_RUN", run_id)
            .with_env_variable("FLASK_CONFIG", "default")
            .with_env_variable("SECRET_KEY", "acceptance-tests-only")
            .with_env_variable(
                "SQLALCHEMY_DATABASE_URI", "mysql+pymysql://aipscan:demo@mysql/aipscan"
            )
            .with_env_variable(
                "CELERY_RESULT_BACKEND", "db+mysql+pymysql://aipscan:demo@mysql/celery"
            )
            .with_env_variable("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq//")
            .with_env_variable("AGGREGATOR_DOWNLOAD_ROOT", "/downloads")
        )
        if indexed:
            typesense = (
                dag.container()
                .from_("typesense/typesense:30.2")
                .with_env_variable("TYPESENSE_API_KEY", "acceptance-tests-only")
                .with_env_variable("TYPESENSE_DATA_DIR", "/data")
                .with_env_variable("AIPSCAN_TEST_RUN", run_id)
                .with_mounted_temp("/data", size=256 * 1024 * 1024)
                .with_exposed_port(8108)
                .as_service()
            )
            app = (
                app.with_service_binding("typesense", typesense)
                .with_env_variable("TYPESENSE_HOST", "typesense")
                .with_env_variable("TYPESENSE_API_KEY", "acceptance-tests-only")
            )
        # Web and worker share the download directory, as in the Compose stack.
        # Initialize the database at service startup: cached build steps cannot
        # preserve side effects in the database service's temporary filesystem.
        service = app.with_exposed_port(5000).as_service(
            args=["/entrypoint.sh", "bash", "/e2e/start.sh"]
            if release
            else ["bash", "/e2e/start.sh"]
        )
        runner = (
            python_base.with_exec(
                [
                    "uv",
                    "sync",
                    "--locked",
                    "--only-group",
                    "e2e",
                    "--no-install-project",
                ]
            )
            .with_exec(
                ["playwright", "install", "--with-deps", "--only-shell", "chromium"]
            )
            .with_directory("/e2e", source.directory("tests/e2e"))
            .with_file(
                "/e2e/legacy-packages.json", ambox_files.file("/legacy-packages.json")
            )
            .with_service_binding("aipscan", service)
            .with_service_binding("ambox", ambox)
            .with_service_binding("fault-storage", fault_storage)
        )
        if indexed:
            runner = runner.with_service_binding("typesense", typesense)
        runner = (
            runner.with_env_variable("AIPSCAN_INDEXED", "1" if indexed else "0")
            .with_env_variable("AIPSCAN_ARTIFACTS", "/artifacts")
            .with_exec(["mkdir", "-p", "/artifacts"])
            .with_exec(
                [
                    "pytest",
                    "-v",
                    "/e2e",
                    "--rootdir=/e2e",
                    "--junitxml=/artifacts/junit.xml",
                ],
                expect=dagger.ReturnType.ANY,
                redirect_stdout="/artifacts/pytest.log",
                redirect_stderr="/artifacts/pytest-errors.log",
            )
        )
        return runner
