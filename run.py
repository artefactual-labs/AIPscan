import os

from AIPscan.application import create_app


if __name__ == "__main__":
    config_name = os.environ.get("FLASK_CONFIG", "default")
    app = create_app(config_name)
    app.run(host="0.0.0.0")
