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

from httplib import UNAUTHORIZED
from functools import wraps
from wtforms import (
    Form, TextField, PasswordField, validators, ValidationError)
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature
from flask import Response, request, redirect, render_template, abort, flash
from flask.ext.login import (
    LoginManager, login_user, logout_user, current_app, current_user, login_url,
    user_unauthorized)
from pyfarm.core.enums import MimeType
from pyfarm.master.application import app, login_manager, login_serializer
from pyfarm.models.users import User

try:
    import json

except ImportError:
    import simplejson as json


@login_manager.user_loader
def load_user(user):
    """
    callback for :func:`flask_login.LoginManager.user_loader`

    When the user id is is not present in the session this function
    is used to load the user from the database directly.
    """
    return User.get(user)


@login_manager.token_loader
def load_token(token):
    """
    callback for :func:`flask_login.LoginManager.token_loader`

    When a user is already loaded check the token provided to be sure
    the password matches and that the token has not expired.
    """
    # The token was encrypted using itsdangerous.URLSafeTimedSerializer which
    # allows us to have a max_age on the token itself.  When the cookie is
    # stored on the users computer it also has a expiry date, but could be
    # changed by the user, so this feature allows us to enforce the exipry
    # date of the token server side and not rely on the users cookie to expire.
    try:
        userid, password = login_serializer.loads(
            token,
            max_age=app.config["REMEMBER_COOKIE_DURATION"].total_seconds())
        user = User.get(userid)
        return user if user and user.password == password else None

    except BadTimeSignature:
        return None


class LoginForm(Form):
    username = TextField(validators=[validators.Required()])
    password = PasswordField(validators=[validators.Required()])

    def __init__(self, *args, **kwargs):
        self.dbuser = False
        super(LoginForm, self).__init__(*args, **kwargs)

    def validate_username(self, field):
        if self.dbuser is False:
            self.dbuser = User.get(request.form["username"])

        if self.dbuser is None:
            raise ValidationError("invalid username")

    def validate_password(self, field):
        if self.dbuser is False:
            self.dbuser = User.get(request.form["username"])

        if self.dbuser:
            password = str(field.data)
            if self.dbuser.hash_password(password) != self.dbuser.password:
                raise ValidationError("invalid password")


@app.route("/login/", methods=("GET", "POST"))
def login_page():
    """display and process the login for or action"""
    if request.method == "POST" and request.content_type == MimeType.JSON:
        data = json.loads(request.data)
        user = User.get(data["username"])

        if user and user.check_password(data["password"]):
            login_user(user, remember=True)
            return redirect(request.args.get("next") or "/")

        return Response(
            response=json.dumps({"error": "invalid user or password"}),
            content_type=request.content_type,
            status=UNAUTHORIZED)

    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        login_user(form.dbuser, remember=True)
        return redirect(request.args.get("next") or "/")

    return render_template("pyfarm/login.html", form=form,
                           next=request.args.get("next"))


@app.route("/logout/")
def logout_page():
    """log out the user then redirect them"""
    logged_in = current_user.is_authenticated()
    if logged_in:
        logout_user()

    # TODO: this should probably have a configuration value for seconds
    return render_template("pyfarm/logout.html", logged_in=logged_in, seconds=3)


def login_role(allow_roles=None, require_roles=None):
    """
    Decorator which operates in the same manner that
    :func:`flask_login.login_required` does but can also check for the user's
    membership in one or more roles.

    :type allow_roles: set or str or list or tuple
    :param allow_roles:
        if provided the user must have at least one of these roles

    :type require_roles: set or str or list or or tuple
    :param require_roles:
        if provided the user must have all of these roles
    """
    def construct_data(data, varname):
        if isinstance(data, (list, tuple)):
            return set(data)

        elif isinstance(data, basestring):
            return set([data])

        elif data is None:
            return set()

        else:
            raise TypeError(
                "expected list, tuple, or string for `%s`" % varname)

    def wrap(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_app.login_login_manager._login_disabled:
                return func(*args, **kwargs)
            elif not current_user.is_authenticated():
                return current_app.login_login_manager.unauthorized()
            else:
                # construct the data we're doing to operate on
                # and rename the variable so we don't have to have to
                # use 'global'
                allowed = construct_data(allow_roles, "allow_roles")
                required = construct_data(require_roles, "require_roles")
                if required and allowed:
                    raise ValueError(
                        "please use either allow_roles or require_roles")

                if not current_user.has_roles(
                        allowed=allowed, required=required):
                    return current_app.login_login_manager.unauthorized()

                return func(*args, **kwargs)
        return wrapper
    return wrap
