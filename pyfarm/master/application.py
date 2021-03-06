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
from multiprocessing.util import register_after_fork
from uuid import UUID

try:
    from httplib import BAD_REQUEST, UNSUPPORTED_MEDIA_TYPE
except ImportError:
    from http.client import BAD_REQUEST, UNSUPPORTED_MEDIA_TYPE

from flask import Flask, Blueprint, request, g, abort
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.engine import Engine
from sqlalchemy import event
from werkzeug.exceptions import BadRequest
from werkzeug.routing import BaseConverter, ValidationError

from pyfarm.core.enums import NOTSET, STRING_TYPES, PY3
from pyfarm.core.logger import getLogger
from pyfarm.master.config import config

POST_METHODS = set(("POST", "PUT"))
IGNORED_MIMETYPES = set((
    "application/x-www-form-urlencoded", "multipart/form-data",
    "application/zip", "text/csv"))

logger = getLogger("app")


class UUIDConverter(BaseConverter):
    """
    A URL converter for UUIDs.  This class is loaded as part of
    the Flask application setup and may be used in url routing:

    .. code-block:: python

        @app.route('/foo/<uuid:value>')
        def foobar(value):
            pass

    When a request such as ``GET /foo/F9A63B47-66BF-4E2B-A545-879986BB7CA9``
    is made :class:`UUIDConverter` will receive ``value`` to :meth:`to_python`
    which will then convert the string to an instance of :class:`UUID`.
    """
    def to_python(self, value):
        if isinstance(value, UUID):
            return value
        try:
            return UUID(value)
        except Exception as e:
            logger.error("Failed to convert %r to a UUID", e)
            raise ValidationError

    def to_url(self, value):  # pylint: disable=super-on-old-class
        if PY3 and isinstance(value, bytes):
            try:
                value = UUID(bytes=value)
            except (AttributeError, ValueError):
                value = None

        if isinstance(value, STRING_TYPES):
            try:
                value = UUID(value)
            except Exception:
                try:
                    value = UUID(bytes=value)
                except (AttributeError, ValueError):
                    value = None

        if not isinstance(value, UUID):
            raise ValidationError

        return super(UUIDConverter, self).to_url(value)


def get_application(**configuration_keywords):
    """
    Returns a new application context.  If keys and values are provided
    to ``config_values`` they will be used to override the default
    configuration values or create new ones

    >>> app = get_application(TESTING=True)
    >>> assert app.testing is True

    :keyword bool setup_appcontext:
        If ``True`` then setup the ``flask.g`` variable to include the
        application level information (ex. ``g.db``)
    """
    app_config = {
        "DEBUG": config.get("debug"),
        "SECRET_KEY": config.get("secret_key"),
        "LOGIN_DISABLED": config.get("login_disabled"),
        "PYFARM_JSON_PRETTY": config.get("pretty_json"),
        "SQLALCHEMY_ECHO": config.get("echo_sql"),
        "SQLALCHEMY_DATABASE_URI": config.get("database"),
        "CSRF_SESSION_KEY": config.get("csrf_session_key"),
        "REMEMBER_COOKIE_DURATION": timedelta(**config.get("cookie_duration")),
        "JSONIFY_PRETTYPRINT_REGULAR": config.get("pretty_json"),
        "TIMESTAMP_FORMAT": config.get("timestamp_format")
    }

    if config.get("enable_statistics"):
        app_config["SQLALCHEMY_BINDS"] = {
            "statistics": config.get("statistics_database")}

    static_folder = configuration_keywords.pop("static_folder", None)
    if static_folder is None:  # static folder not provided
        import pyfarm.master
        static_folder = os.path.join(
            os.path.dirname(pyfarm.master.__file__), "static")

    static_folder = os.path.abspath(static_folder)
    assert os.path.isdir(static_folder), "No such directory %s" % static_folder

    app = Flask("pyfarm.master", static_folder=static_folder)
    app.config.update(app_config)
    app.config.update(configuration_keywords)
    app.url_map.converters["uuid"] = UUIDConverter

    @app.context_processor
    def template_context_processor():
        return {
            "timestamp_format": app.config["TIMESTAMP_FORMAT"]
        }

    return app


def get_sqlalchemy(app=None, use_native_unicode=True, session_options=None):
    """
    Constructs and returns an instance of :class:`.SQLAlchemy`.  Any keyword
    arguments provided will be passed to the constructor of :class:`.SQLAlchemy`
    """
    db = SQLAlchemy(
        app=app, use_native_unicode=use_native_unicode,
        session_options=session_options)

    # sqlite specific configuration for development
    if db.engine.name == "sqlite":
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.execute("PRAGMA journal_mode=MEMORY")
            cursor.close()

    # When the web application is forked any existing connections
    # need to be disposed of.  This generally only seems to be a problem
    # with Postgres, more specifically psycopg2, but doing this globally
    # should not have any ill effects.  This problem was discovered while
    # testing the Agent using uwsgi 2.0.3, nginx 1.4.6, Postgres 9.1, and
    # psycopg2 2.5.2.  The bug does not present itself 100% of the time
    # making it difficult to test reliably.  The fix below is based
    # on a fix made to Celery which had the exact same problem ours did:
    #   https://github.com/celery/celery/issues/1564
    #
    # This implementation however is based on the suggestion made in Celery
    # 3.1's release notes:
    #    https://celery.readthedocs.org/en/latest/whatsnew-3.1.html
    register_after_fork(db.engine, db.engine.dispose)

    return db


def get_api_blueprint(url_prefix=None):
    """
    Constructs and returns an instance of :class:`.Blueprint` for routing api
    requests.

    :param string url_prefix:
        The url prefix for the api such as ``/api/v1``.  If not provided then
        value will be derived from the `api_prefix` configuration variable.
    """
    if url_prefix is None:
        url_prefix = config.get("api_prefix")

    return Blueprint("api", "pyfarm.master.api", url_prefix=url_prefix)


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


def before_request():
    """
    Global before_request handler that will handle common problems when
    trying to accept json data to the api.
    """
    g.json = NOTSET
    g.error = None

    if request.method not in POST_METHODS or \
            request.mimetype in IGNORED_MIMETYPES:
        pass

    elif request.mimetype == "application/json":
        # manually handle decoding errors from get_json()
        # so we can produce a better error message
        try:
            g.json = request.get_json()
        except (ValueError, BadRequest):  # pragma: no cover
            g.error = "failed to decode json"

            # see if there just was not any data to decode
            if not request.get_data():
                g.error = "no data to decode"

            abort(BAD_REQUEST)

    elif request.get_data():
        g.error = "Unsupported media type %r" % request.mimetype
        abort(UNSUPPORTED_MEDIA_TYPE)

# main object setup (app, api, etc)
app = get_application()
api = get_api_blueprint()
db = get_sqlalchemy(app=app)
login_manager = get_login_manager(app=app, login_view="/login/")
login_serializer = get_login_serializer(app.secret_key)

# attach the remaining functions to the application object
app.register_blueprint(api)
app.before_request_funcs.setdefault(None, []).append(before_request)


class SessionMixin(object):
    """
    Mixin which adds a :attr:`._session` attribute.  This class is provided
    mainly to limit issues with circular imports.
    """
    _session = property(fget=lambda self: db.session)

