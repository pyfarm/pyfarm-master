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

from warnings import warn
from flask import redirect, abort
from flask.ext.login import current_user, current_app
from flask.ext.admin.contrib.sqlamodel import ModelView as _ModelView
from flask.ext.admin import AdminIndexView
from pyfarm.core.warning import ConfigurationWarning

def current_user_authorized(required=None, allowed=None, redirect=True):
    """
    Simple function which take into account roles, enabled/disabled login system
    and various other bits of information.  In the event a user does not
    have access when this function is call a 401 will e raised using
    :func:`abort`
    """
    if current_app.login_manager._login_disabled:
        return True

    if not current_user.is_authenticated():
        return False

    if not (current_user.has_roles(allowed=allowed, required=required)
              and redirect):
            abort(401)

    return False


class AuthMixins(object):
    access_roles = set()

    def _has_access(self, default):
        if current_app.login_manager._login_disabled:
            return True
        elif current_user.is_authenticated():
            return current_user.has_roles(allowed=self.access_roles)
        else:
            return default

    def is_visible(self):
        return self._has_access(False)

    def is_accessible(self):
        return self._has_access(True)

    def render(self, template, **kwargs):
        if not current_app.login_manager._login_disabled:
            if not current_user.is_authenticated():
                return redirect("/login/?next=%s" % self.url)

            if not current_user.has_roles(allowed=self.access_roles):
                abort(401)

        return super(AuthMixins, self).render(template, **kwargs)


class AdminIndex(AuthMixins, AdminIndexView):
    access_roles = (
        "admin", "admin.db", "admin.db.user", "admin.db.job",
        "admin.db.agent")


class BaseModelView(AuthMixins, _ModelView):
    def __init__(self, name=None, category=None, endpoint=None, url=None):

        try:
            self.access_roles
        except AttributeError:
            raise NotImplementedError("you must override `access_roles`")

        try:
            self._session
        except AttributeError:
            raise NotImplementedError("you must provide a `_session` attribute")

        super(BaseModelView, self).__init__(
            self.model, self._session, name=name,
            category=(category or "Database"),
            endpoint="db/%s" % (endpoint or self.model.__name__),
            url=url)