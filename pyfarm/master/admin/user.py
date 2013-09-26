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
from flask.ext.admin.contrib.sqlamodel import ModelView
from pyfarm.master.admin.base import AuthMixins
from pyfarm.master.application import db
from pyfarm.models.users import User


class CreateUser(Form):
    password = PasswordField()  # TODO: serialize
    expiration = DateField()

    # TODO: don't display last login or onetime code


    def validate_expiration(self, field):
        # TODO: ensure not already expired
        pass


class UserView(AuthMixins, ModelView):
    def __init__(self):
        super(UserView, self).__init__(User, db.session)