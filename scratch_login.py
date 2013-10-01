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

from pyfarm.models.users import User, Role
from pyfarm.master.admin.user import UserView
from pyfarm.master.application import app, db, admin

# load endpoints
from pyfarm.master import index, login, errors


@app.before_first_request
def create_user():
    db.create_all()
    User.create(username="pyfarm", password="pyfarm", roles=["root"])


from flask.ext.admin.base import MenuLink

#print admin._add_view_to_menu(MenuItem("Foo"))
# TODO: add /preferences endpoint, maybe give it an admin interface too?
admin.add_link(MenuLink("Preferences", "/preferences"))
admin.add_link(MenuLink("Log Out", "/logout"))
admin.add_view(UserView())


app.run()