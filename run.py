import os

from werkzeug.middleware.proxy_fix import ProxyFix


from AIPscan import create_app

if __name__ == "__main__":
    config_name = os.environ.get("FLASK_CONFIG", "default")
    app = create_app(config_name)

    # App is behind one proxy that sets the -For and -Host headers.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1, x_port=1)

    app.run(host="0.0.0.0")
