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
Admin Index
===========

Setup the administrative index.
"""

from flask import redirect
from flask.ext.login import current_user
from flask.ext.admin import Admin as _Admin
from flask.ext.admin import AdminIndexView as _AdminIndexView, expose, BaseView


class AdminIndexView(_AdminIndexView):

    @expose()
    def index(self):
        """
        Dislay the index
        """
        if not current_user.is_authenticated():
            return redirect("/login?next=admin")
        else:
            return super(AdminIndexView, self).index()


class Admin(_Admin):
    def render(self):
        pass