from functools import wraps

from flask import abort, render_template, request


def confirm_required(model, id_argument, prompt, action, cancel_route):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            instance = model.query.get(kwargs[id_argument])

            if not instance:
                abort(404)

            if request.args.get("confirm"):
                return f(*args, **kwargs)

            return render_template(
                "confirm.html",
                prompt=prompt,
                action=action,
                cancel_route=cancel_route,
            )

        return decorated_function

    return decorator
