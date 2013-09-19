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
Flask Application
=================

Sets up the flask application object and database interface

:attr app:
    module level instance of the :class:`flask.Flask` application object

:attr db:
    module level instance of the :class:`flask.ext.sqlalchemy.SQLAlchemy` class
"""

import os
from uuid import uuid4
from os.path import expandvars
from flask import Flask
from pyfarm.core.config import cfg

if "SQLALCHEMY_DATABASE_URI" in os.environ and "db.uri" not in cfg:
    cfg.setdefault("db.uri", os.environ["SQLALCHEMY_DATABASE_URI"])
else:  # pragma: no cover
    cfg.setdefault("db.uri", "sqlite:///:memory:")

# For security reasons, we should not keep SQLALCHEMY_DATABASE_URI in
# the environment.
os.environ.pop("SQLALCHEMY_DATABASE_URI", None)

app = Flask("PyFarm")
app.config["SQLALCHEMY_DATABASE_URI"] = expandvars(cfg.get("db.uri"))
app.config["SECRET_KEY"] = cfg.get("app.secret", str(uuid4()))

# sqlite fixes (development work only)
if cfg.get("db.uri").startswith("sqlite"):  # pragma: no cover
    from warnings import warn
    from sqlalchemy.engine import Engine
    from sqlalchemy import event

    from pyfarm.core.warning import ConfigurationWarning

    warn("sqlite is for development purposes only", ConfigurationWarning)

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.close()


from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)