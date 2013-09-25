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
from pyfarm.models.users import User, Role
from pyfarm.master.admin.base import ModelView
from pyfarm.master.application import app, db, admin

# load endpoints
from pyfarm.master import index, login, errors


@app.before_first_request
def create_user():
    db.create_all()
    user = User.create(username="admin", password="admin")
    roles = ["api", "admin", "admin.usermanager"]
    for role in roles:
        user.roles.append(Role.create(role))

    db.session.add(user)
    db.session.commit()

#admin = Admin(app, index_view=AdminIndex())
admin.add_view(ModelView(User, db.session,
                         access_roles=("admin.usermanager", )))


from datetime import timedelta
app.config["SQLALCHEMY_ECHO"] = True
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=14)
app.run()