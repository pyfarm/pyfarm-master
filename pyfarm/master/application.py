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
from functools import partial
from datetime import timedelta
from werkzeug.datastructures import ImmutableDict
from flask import Flask, Blueprint
from flask.ext.cache import Cache
from flask.ext.admin import Admin
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer
from pyfarm.core.config import cfg, read_env
from pyfarm.master.admin.baseview import AdminIndex

# default configuration values
eval_env = partial(read_env, eval_literal=True)
cfg.update({
    "db.table_prefix": eval_env("PYFARM_TABLE_PREFIX", "pyfarm_"),
    "agent.min_port": eval_env("PYFARM_AGENT_MIN_PORT", 1025),
    "agent.max_port": eval_env("PYFARM_AGENT_MAX_PORT", 65535),
    "agent.min_cpus": eval_env("PYFARM_AGENT_MIN_CPUS", 1),
    "agent.max_cpus": eval_env("PYFARM_AGENT_MAX_CPUS", 2147483647),
    "agent.special_cpus": [0],
    "agent.min_ram": eval_env("PYFARM_AGENT_MIN_RAM", 32),
    "agent.max_ram": read_env("PYFARM_AGENT_MAX_RAM", 2147483647),
    "agent.special_ram": [0],
    "job.max_username_length": eval_env("PYFARM_MAX_USERNAME_LENGTH", 254),
    "job.priority": eval_env("PYFARM_JOB_DEFAULT_PRIORITY", 500),
    "job.min_priority": eval_env("PYFARM_JOB_MIN_PRIORITY", 0),
    "job.max_priority": eval_env("PYFARM_JOB_MAX_PRIORITY", 1000),
    "job.batch": eval_env("PYFARM_JOB_DEFAULT_BATCH", 1),
    "job.requeue": eval_env("PYFARM_JOB_DEFAULT_REQUEUE", 1),
    "job.cpus": eval_env("PYFARM_JOB_DEFAULT_CPUS", 4),
    "job.ram": eval_env("PYFARM_JOB_DEFAULT_RAM", 32)})


# build the configuration
if read_env("PYFARM_CONFIG", "debug", ) == "debug":
    __secret_key__ = read_env(
        "PYFARM_SECRET_KEY", "4n)Z\xc2\xde\xdd\x17\xdd\xf7\xa6)>{\xfc\xff",
        log_result=False)

    CONFIG = ImmutableDict({
        "DEBUG": True,
        "SECRET_KEY": __secret_key__,
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
            read_env("PYFARM_CSRF_SESSION_KEY", __secret_key__,
                     log_result=False),
        "CACHE_TYPE":
            read_env("PYFARM_CACHE_TYPE", "simple"),
        "REMEMBER_COOKIE_DURATION": timedelta(hours=1)})

else:
    __secret_key__ = read_env("PYFARM_SECRET_KEY", log_result=False)
    
    CONFIG = ImmutableDict({
        "DEBUG": False,
        "SECRET_KEY": __secret_key__,
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
            read_env("PYFARM_CSRF_SESSION_KEY", __secret_key__,
                     log_result=False),
        "CACHE_TYPE":
            read_env("PYFARM_CACHE_TYPE", "simple"),
        "REMEMBER_COOKIE_DURATION": timedelta(hours=12)})


del __secret_key__  # should not be visible on the module

app = Flask("pyfarm.master")

# configure the application
app.config.update(CONFIG)

# api blueprint
api_version = os.environ.get("PYFARM_API_VERSION", "1")
api = Blueprint(
    "api", "pyfarm.master.api",
    url_prefix=os.environ.get("PYFARM_API_PREFIX", "/api/v%s" % api_version))
app.register_blueprint(api)

# admin, database, and cache
admin = Admin(app, index_view=AdminIndex())
db = SQLAlchemy(app)
cache = Cache(app)

# login system
login_manager = LoginManager(app)
login_manager.login_view = "/login/"
login_serializer = URLSafeTimedSerializer(app.secret_key)


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