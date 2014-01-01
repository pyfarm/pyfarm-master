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
Application
===========

Contains the functions necessary to construct the application layer classes
necessary to run the master.
"""

import os
from datetime import timedelta
from flask import Flask, Blueprint
from flask.ext.admin import Admin
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer
from pyfarm.core.config import read_env
from pyfarm.master.admin.baseview import AdminIndex


def get_application(**configuration_keywords):
    """
    Returns a new application context.  If keys and values are provided
    to ``config_values`` they will be used to override the default
    configuration values or create new ones

    >>> app = get_application(TESTING=True)
    >>> assert app.testing is True
    """

    # build the configuration
    if read_env("PYFARM_CONFIG", "debug", ) == "debug":
        secret_key = read_env(
            "PYFARM_SECRET_KEY", "NG4pWsOCw57DnRfDncO3wqYpPnvDvMO",
            log_result=False)

        app_config = {
            "DEBUG": True,
            "SECRET_KEY": secret_key,
            "LOGIN_DISABLED":
                read_env("PYFARM_LOGIN_DISABLED", False, eval_literal=True),
            "PYFARM_JSON_PRETTY":
                read_env("PYFARM_JSON_PRETTY", True, eval_literal=True),
            "SQLALCHEMY_ECHO":
                read_env("PYFARM_SQL_ECHO", False, eval_literal=True),
            "SQLALCHEMY_DATABASE_URI":
                read_env("PYFARM_DATABASE_URI", "sqlite:///pyfarm.sqlite",
                         log_result=False),
            "CSRF_SESSION_KEY":
                read_env("PYFARM_CSRF_SESSION_KEY", secret_key,
                         log_result=False),
            "CACHE_TYPE":
                read_env("PYFARM_CACHE_TYPE", "simple"),
            "REMEMBER_COOKIE_DURATION": timedelta(hours=1)}

    else:
        secret_key = read_env("PYFARM_SECRET_KEY", log_result=False)
        app_config = {
            "DEBUG": False,
            "SECRET_KEY": secret_key,
            "LOGIN_DISABLED":
                read_env("PYFARM_LOGIN_DISABLED", False, eval_literal=True),
            "PYFARM_JSON_PRETTY":
                read_env("PYFARM_JSON_PRETTY", False, eval_literal=True),
            "SQLALCHEMY_ECHO":
                read_env("PYFARM_SQL_ECHO", False, eval_literal=True),
            "SQLALCHEMY_DATABASE_URI":
                read_env("PYFARM_DATABASE_URI", "sqlite:///pyfarm.sqlite",
                         log_result=False),
            "CSRF_SESSION_KEY":
                read_env("PYFARM_CSRF_SESSION_KEY", secret_key,
                         log_result=False),
            "CACHE_TYPE":
                read_env("PYFARM_CACHE_TYPE", "simple"),
            "REMEMBER_COOKIE_DURATION": timedelta(hours=12)}

    app_config.setdefault(
        "JSONIFY_PRETTYPRINT_REGULAR",
        app_config.get("PYFARM_JSON_PRETTY", True))

    static_folder = configuration_keywords.pop("static_folder", None)
    if static_folder is None:  # static folder not provided
        import pyfarm.master
        static_folder = os.path.join(
            os.path.dirname(pyfarm.master.__file__), "static")

    app = Flask("pyfarm.master", static_folder=static_folder)
    app.config.update(app_config)
    app.config.update(configuration_keywords)
    return app


def get_api_blueprint(url_prefix=None):
    """
    Constructs and returns an instance of :class:`.Blueprint` for routing api
    requests.

    :param string url_prefix:
        The url prefix for the api such as ``/api/v1``.  If not provided then
        value will be derived from :envvar:`PYFARM_API_PREFIX` and/or
        :envvar:`PYFARM_API_VERSION`
    """
    if url_prefix is None:
        url_prefix = read_env("PYFARM_API_PREFIX",
                              "/api/v%s" % read_env("PYFARM_API_VERSION", "1"))

    return Blueprint("api", "pyfarm.master.api", url_prefix=url_prefix)


def get_admin(**kwargs):
    """
    Constructs and returns an instance of :class:`.Admin`.  Any keyword
    arguments provided will be passed to the constructor of :class:`.Admin`
    """
    kwargs.setdefault("index_view", AdminIndex())
    return Admin(**kwargs)


def get_sqlalchemy(**kwargs):
    """
    Constructs and returns an instance of :class:`.SQLAlchemy`.  Any keyword
    arguments provided will be passed to the constructor of :class:`.SQLAlchemy`
    """
    return SQLAlchemy(**kwargs)


def get_login_manager(**kwargs):
    """
    Constructs and returns an instance of :class:`.LoginManager`.  Any keyword
    arguments provided will be passed to the constructor of
    :class:`LoginManager`
    """
    login_view = kwargs.pop("login_view", "/login/")
    manager = LoginManager(**kwargs)
    manager.login_view = login_view
    return manager


def get_login_serializer(secret_key):
    """
    Constructs and returns and instance of :class:`.URLSafeTimedSerializer`
    """
    return URLSafeTimedSerializer(secret_key)


app = get_application()
api = get_api_blueprint()
app.register_blueprint(api)
admin = get_admin(app=app)
db = get_sqlalchemy(app=app)
login_manager = get_login_manager(app=app, login_view="/login/")
login_serializer = get_login_serializer(app.secret_key)


class SessionMixin(object):
    """
    Mixin which adds a :attr:`._session` attribute.  This class is provided
    mainly to limit issues with circular imports.
    """
    _session = property(fget=lambda self: db.session)


# sqlite specific configuration for development
if db.engine.name == "sqlite":
    from sqlalchemy.engine import Engine
    from sqlalchemy import event

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.close()