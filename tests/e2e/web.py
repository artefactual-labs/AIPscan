"""Serve real app instances with both report backends in one test process."""

from werkzeug.middleware.dispatcher import DispatcherMiddleware

from AIPscan import create_app

application = create_app()
if application.config["TYPESENSE_API_KEY"]:
    sql_application = create_app()
    sql_application.config["TYPESENSE_API_KEY"] = None
    application = DispatcherMiddleware(application, {"/sql": sql_application})
