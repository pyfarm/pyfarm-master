# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Login
=====

View and code necessary for providing the basic login and authentication
services
"""

from functools import wraps
from httplib import UNAUTHORIZED
from itsdangerous import URLSafeTimedSerializer
from flask import Response, request, redirect, render_template
from flask.ext.login import (
    LoginManager, login_user, logout_user, current_app, current_user)
from pyfarm.core.app.loader import package
from pyfarm.core.enums import MimeType
from pyfarm.models.permission import User

try:
    import json

except ImportError:
    import simplejson as json

app = package.application()
manager = LoginManager(app)
login_serializer = URLSafeTimedSerializer(app.secret_key)


@manager.user_loader
def load_user(user):
    """
    callback for flask-login's user_loader

    When the user id is is not present in the session this function
    is used to load the user from the database directly.
    """
    return User.get(user)


@manager.token_loader
def load_token(token):
    """
    callback for flask-login's token_loader

    When a user is already loaded check the token provided to be sure
    the password matches and that the token has not expired.
    """
    # The token was encrypted using itsdangerous.URLSafeTimedSerializer which
    # allows us to have a max_age on the token itself.  When the cookie is
    # stored on the users computer it also has a expiry date, but could be
    # changed by the user, so this feature allows us to enforce the exipry
    # date of the token server side and not rely on the users cookie to expire.
    userid, password = login_serializer.loads(
        token,
        max_age=app.config["REMEMBER_COOKIE_DURATION"].total_seconds())

    user = User.get(userid)
    return user if user and user.password == password else None


@app.route("/login/", methods=("GET", "POST"))
def login_page():
    """display and process the login for or action"""
    if request.method == "POST" and request.content_type == MimeType.JSON:
        data = json.loads(request.data)
        user = User.get(data["username"])

        if user and user.check_password(data["password"]):
            login_user(user, remember=True)
            return redirect(request.args.get("next") or "/")

        else:
            return Response(
                response=json.dumps({"error": "invalid user or password"}),
                content_type=request.content_type,
                status=UNAUTHORIZED)

    elif request.method == "POST":
        user = User.get(request.form['username'])

        if user and user.check_password(request.form['password']):
            login_user(user, remember=True)
            return redirect(request.args.get("next") or "/")

    return render_template("login.html")


@app.route("/logout/")
def logout_page():
    """log out the user then redirect them"""
    logout_user()
    return redirect("/")

raise Exception("required roles")

class roles_required(object):
    def __init__(self, allowed=None, required=None):
        self.required = set()
        self.allowed = set(["everyone"])

        # setup allowed
        if isinstance(allowed, basestring):
            self.allowed.update(set([allowed]))
        elif isinstance(allowed, (list, tuple)):
            self.allowed.update(set(allowed))
        elif allowed is not None:
            raise TypeError("`allowed` must be a string, list, or set")

        # setup required
        if isinstance(required, basestring):
            self.required.update(set([required]))
        elif isinstance(required, (list, tuple)):
            self.required.update(set(required))
        elif required is not None:
            raise TypeError("`required` must be a string, list, or set")

    def __call__(self, *args, **kwargs):
        print args, kwargs

def login_required(allowed_roles=None, required_roles=None):
    """
    custom replacement of Flask's login_required decorator with
    role support
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            # if not current_user.is_authenticated():
            #    return current_app.login_manager.unauthorized()
            print fn
            # if isinstance(allowed_roles, (list, tuple)):
            #     allowed_roles = set(allowed_roles)

            # user = current_app.login_manager.reload_user()
            # roles = set(role.name for role in user.roles)

            # if ( (urole != role) and (role != "ANY")):
            #     return current_app.login_manager.unauthorized()

            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@roles_required(allowed="foo")
def foo():
    print 42

foo()