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

import uuid
from flask import Flask
from pyfarm.core.config import cfg

app = Flask("PyFarm")
app.config["SQLALCHEMY_DATABASE_URI"] = cfg.get("db.uri")
app.secret_key = str(uuid.uuid4())  # TODO: this needs a config or extern lookup

# sqlite fixes (development work only)
if cfg.get("db.uri").startswith("sqlite"):
    from sqlalchemy.engine import Engine
    from sqlalchemy import event

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.close()


from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)
