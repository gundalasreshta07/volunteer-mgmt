from functools import wraps

from flask import flash, redirect, session, url_for


def volunteer_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("user_type") != "volunteer":
            flash("Please log in as a volunteer.", "error")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapper


def coordinator_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("user_type") != "coordinator":
            flash("Please log in as a coordinator.", "error")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapper
