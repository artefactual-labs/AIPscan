from AIPscan import create_app


def main():
    """Entry point for running the Flask application using the built-in server.

    This is only for development purposes, use Gunicorn or similar for production.
    """
    app = create_app()
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
