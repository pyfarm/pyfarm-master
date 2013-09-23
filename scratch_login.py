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

from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqlamodel import ModelView
from pyfarm.core.app.loader import package
from pyfarm.models.users import User, Role

# setup endpoints
from pyfarm.master.admin.index import AdminIndexView
from pyfarm.master import index, login


app = package.application()
db = package.database()

admin = Admin(app, index_view=AdminIndexView())
admin.add_view(ModelView(User, db.session))


@app.before_first_request
def create_user():
    db.create_all()
    user = User.create(username="agent", password="agent")
    role = Role.create("api")
    user.roles.append(role)
    db.session.add_all([user, role])
    db.session.commit()

from datetime import timedelta
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=14)
app.run()