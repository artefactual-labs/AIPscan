import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Run npm build steps so static assets are packaged.

        Build frontend assets only when producing wheels; the sdist already
        includes prebuilt files.
        """
        if self.target_name != "wheel":
            return

        self._run_npm("clean-install")
        self._run_npm("run", "build")

    def _run_npm(self, *args: str) -> None:
        subprocess.run(["npm", *args], check=True, cwd=self.root)
