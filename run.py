import os

from AIPscan import create_app

if __name__ == "__main__":
    id = 3
    print(id)
    bob = "hey"
    print(bob)
    config_name = os.environ.get("FLASK_CONFIG", "default")
    app = create_app(config_name)
    app.run(host="0.0.0.0")
