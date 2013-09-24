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
from flask.ext.login import current_user
from flask.ext.admin.contrib.sqlamodel import ModelView as BaseModelView
from flask.ext.admin import AdminIndexView
from pyfarm.core.warning import ConfigurationWarning


def authorized(login_url, required=None, allowed=None):
    if not current_user.is_authenticated():
        return redirect(login_url)

    elif not current_user.has_roles(allowed=allowed, required=required):
        abort(401)

    return False


class AuthMixin(object):
    access_roles = set()

    def is_visible(self):
        if current_user.is_authenticated():
            return current_user.has_roles(allowed=self.access_roles)
        return False

    def is_accessible(self):
        if current_user.is_authenticated():
            return current_user.has_roles(allowed=self.access_roles)
        return True  # should always return True so we can run render()


class AdminIndex(AuthMixin, AdminIndexView):
    access_roles = set(["admin"])

    def render(self, template, **kwargs):
        return (
            authorized("/login?next=admin", allowed=self.access_roles) or
            super(AdminIndex, self).render(template, **kwargs))


class ModelView(AuthMixin, BaseModelView):
    def __init__(self, model, session,
                 name=None, category=None, endpoint=None, url=None,
                 access_roles=None):
        if isinstance(access_roles, (list, tuple)):
            self.access_roles = set(access_roles)
        elif isinstance(access_roles, set):
            self.access_roles = access_roles
        elif access_roles is not None:
            raise TypeError("expected list, tuple, or set for `access_roles`")

        if not access_roles:
            warn("no access_roles provided for %s" % model, ConfigurationWarning)

        super(ModelView, self).__init__(
            model, session, name=name, category=category, endpoint=endpoint, url=url)

    def render(self, template, **kwargs):
        return (
            authorized("/login/?next=%s" % self.url) or
            super(ModelView, self).render(template, **kwargs))
