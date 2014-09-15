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

try:
    from httplib import UNAUTHORIZED, BAD_REQUEST
except ImportError:
    from http.client import UNAUTHORIZED, BAD_REQUEST

from flask import request, redirect, render_template, abort
from flask.ext.login import login_user, logout_user, current_user
from itsdangerous import BadTimeSignature
from wtforms import Form, TextField, PasswordField, validators, ValidationError

from pyfarm.models.user import User
from pyfarm.master.application import app, login_manager, login_serializer
from pyfarm.master.utility import jsonify

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

    # pylint: disable=super-on-old-class
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


def login_page():
    """display and process the login for or action"""
    if request.method == "POST" and request.content_type == "application/json":
        user = User.get(request.json["username"])

        if user and user.check_password(request.json["password"]):
            login_user(user, remember=True)
            return jsonify(None)

        return jsonify(None), UNAUTHORIZED

    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        login_user(form.dbuser, remember=True)
        return redirect(request.args.get("next") or "/")

    if request.content_type == "application/json":
        abort(BAD_REQUEST)

    return render_template("pyfarm/login.html", form=form,
                           next=request.args.get("next") or "/")


def logout_page():
    """log out the user then redirect them"""
    logged_in = current_user.is_authenticated()
    if logged_in:
        logout_user()

    # TODO: this should probably have a configuration value for seconds
    return render_template("pyfarm/logout.html", logged_in=logged_in, seconds=3)
