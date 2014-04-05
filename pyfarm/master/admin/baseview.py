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


from flask.ext.admin.contrib.sqla import ModelView


class SQLModelView(ModelView):
    """Base of all other model view classes for SQL tables"""
    edit_form_class = None
    create_form_class = None

    def __init__(self, name=None, category=None, endpoint=None, url=None):
        try:
            self._session
        except AttributeError:
            raise NotImplementedError("you must provide a `_session` attribute")

        super(SQLModelView, self).__init__(
            self.model, self._session, name=name,
            category=(category or "Database"),
            endpoint="database/%s" % (endpoint or self.model.__name__),
            url=url)

    def get_create_form(self):
        """
        Returns `edit_form_class` if it was defined otherwise it
        calls :meth:`get_form`
        """
        if self.create_form_class is not None:
            return self.create_form_class
        else:
            return self.get_form()

    def get_edit_form(self):
        """
        Returns `edit_form_class` if it was defined otherwise it
        calls :meth:`get_form`
        """
        if self.edit_form_class is not None:
            return self.edit_form_class
        else:
            return self.get_form()
