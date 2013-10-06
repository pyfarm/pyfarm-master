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

from flask.ext.admin.contrib.sqla import ajax
from wtforms.fields import SelectField
from pyfarm.master.application import db


class AjaxQueryLoader(ajax.QueryAjaxModelLoader):
    def __init__(self, name, model, **kwargs):
        super(AjaxQueryLoader, self).__init__(
            name, db.session, model, **kwargs)


class EnumList(SelectField):
    """
    Custom list field which is meant to handle enums objects

    :param enum:
        the enum to read data

    :type values:
    :param values:
        if provided, only these keys will be provided as choices
        in the html list widget
    """
    def __init__(self, *args, **kwargs):
        processed_choices = []
        enum = kwargs.pop("enum")
        values = kwargs.pop("values")

        for key, value in enum._asdict().iteritems():
            if value in values:
                processed_choices.append((value, key.title()))

        super(EnumList, self).__init__(
            choices=processed_choices, coerce=int, **kwargs)
