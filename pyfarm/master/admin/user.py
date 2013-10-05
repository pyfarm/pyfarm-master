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
User
====

Objects and classes for working with the user models.
"""

from wtforms import Form, PasswordField, DateField
from pyfarm.master.admin.base import BaseModelView
from pyfarm.master.application import db
from pyfarm.models.users import User


from flask.ext.admin.contrib.sqlamodel.form import AdminModelConverter


class TestConverter(AdminModelConverter):
    def post_process(self, form_class, info):
        print form_class
        return form_class


# TODO: post process password field for insertion
# TODO: don't display password, or other security related fields
class UserView(BaseModelView):
    inline_model_form_converter = TestConverter  # not always working?

    def __init__(self):
        super(UserView, self).__init__(User, db.session,
                                       access_roles=("admin.usermanager",))
