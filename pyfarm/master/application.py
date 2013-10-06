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

Contains the base application classes and functions necessary to
configure it.
"""

import os
from datetime import timedelta
from uuid import uuid4
from warnings import warn
from werkzeug.datastructures import ImmutableDict
from flask import Flask
from flask.ext.cache import Cache
from flask.ext.admin import Admin
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer
from pyfarm.core.config import cfg
from pyfarm.core.warning import EnvironmentWarning, ConfigurationWarning
from pyfarm.master.admin.base import AdminIndex

# default configuration values
# TODO: these should either be in the, read from a config, or come from the
# environment
cfg.update({
    "db.table_prefix": "pyfarm_",
    "agent.min_port": 1025,
    "agent.max_port": 65535,
    "agent.min_cpus": 1,
    "agent.max_cpus": 2147483647,
    "agent.special_cpus": [0],
    "agent.min_ram": 32,
    "agent.max_ram": 2147483647,
    "agent.special_ram": [0],
    "job.priority": 500,
    "job.max_username_length": 254,
    "job.min_priority": 0,
    "job.max_priority": 1000,
    "job.batch": 1,
    "job.requeue": 1,
    "job.cpus": 4,
    "job.ram": 32})



def get_secret_key(warning=True):
    """
    Returns the secret key to use.  Depending on :var:`warning` this may
    produce a warning if $PYFARM_SECRET_KEY was not in the environment.
    """
    if "PYFARM_SECRET_KEY" in os.environ:
        return os.environ["PYFARM_SECRET_KEY"]
    elif warning:
        warn("$PYFARM_SECRET_KEY not present in environment",
             EnvironmentWarning)

    return "4n)Z\xc2\xde\xdd\x17\xdd\xf7\xa6)>{\xfc\xff"


def get_database_uri(warning=True):
    """
    Returns the database uri.  Depending on :var:`warning` this may produce
    warnings for:

        * missing $PYFARM_DATABASE_URI in the environment
        * use of sqlite
    """
    if "PYFARM_DATABASE_URI" in os.environ:
        uri = os.environ["PYFARM_DATABASE_URI"]
    else:
        uri = "sqlite:///pyfarm.sql"

        if warning:
            warn("$PYFARM_DATABASE_URI not present in environment",
                 EnvironmentWarning)

    if warning and "sqlite:" in uri:
        warn("sqlite is for development purposes only", ConfigurationWarning)

    return uri


def get_session_key(warning=True):
    """returns the CSRF session key for use by the application"""
    if "PYFARM_CSRF_SESSION_KEY" in os.environ:
        return os.environ["PYFARM_CSRF_SESSION_KEY"]
    elif warning:
        warn("$PYFARM_CSRF_SESSION_KEY is not present in the environment",
             EnvironmentWarning)

    return str(uuid4()).replace("-", "").decode("hex")


# build the configuration
if os.environ.get("PYFARM_CONFIG", "debug") == "debug":
    CONFIG = ImmutableDict({
        "DEBUG": True,
        #"LOGIN_DISABLED": True,
        "SQLALCHEMY_ECHO": False,
        "SECRET_KEY": get_secret_key(warning=False),
        "SQLALCHEMY_DATABASE_URI": get_database_uri(warning=False),
        "CSRF_SESSION_KEY": get_session_key(warning=False),
        "CACHE_TYPE": "simple",
        "REMEMBER_COOKIE_DURATION": timedelta(hours=1)})

else:
    CONFIG = ImmutableDict({
        "DEBUG": False,
        "SQLALCHEMY_ECHO": False,
        "SECRET_KEY": get_secret_key(warning=True),
        "SQLALCHEMY_DATABASE_URI": get_database_uri(warning=True),
        "CSRF_SESSION_KEY": get_session_key(warning=True),
        "CACHE_TYPE": "simple",  # TODO: should probably be server based
        "REMEMBER_COOKIE_DURATION": timedelta(hours=12)})


app = Flask("PyFarm",
            static_url_path="/pyfarm/static",
            template_folder="pyfarm/master/templates",
            static_folder="pyfarm/master/static")

# configure the application
app.config.update(CONFIG)

# admin, database, and cache
admin = Admin(app, index_view=AdminIndex())
db = SQLAlchemy(app)
cache = Cache(app)

# login system
login_manager = LoginManager(app)
login_manager.login_view = "/login/"
login_serializer = URLSafeTimedSerializer(app.secret_key)


class SessionMixin(object):
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