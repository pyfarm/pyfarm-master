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
Contains all the models used for database communication and object
relational management.
"""

#from pyfarm.master.application import db
#
## sqlite specific configuration for development
#if db.engine.name == "sqlite":
#    from sqlalchemy.engine import Engine
#    from sqlalchemy import event
#
#    @event.listens_for(Engine, "connect")
#    def set_sqlite_pragma(dbapi_connection, connection_record):
#        cursor = dbapi_connection.cursor()
#        cursor.execute("PRAGMA foreign_keys=ON")
#        cursor.execute("PRAGMA synchronous=OFF")
#        cursor.execute("PRAGMA journal_mode=MEMORY")
#        cursor.close()
