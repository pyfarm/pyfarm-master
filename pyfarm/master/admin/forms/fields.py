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

from functools import partial
from wtforms.validators import Required
from wtforms.fields import SelectField, TextField, IntegerField, FloatField


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
    def __init__(self, enum, choices=None, **kwargs):
        processed_choices = []

        for key, value in enum._asdict().iteritems():
            if not choices or value in choices:
                processed_choices.append((value, key.title()))

        super(EnumList, self).__init__(
            choices=processed_choices, coerce=int, **kwargs)


def construct_field(field_type, column, label=None, required=True, **kwargs):
    if required:
        validators = kwargs.setdefault("validators", [])
        validators.append(Required())

    kwargs["description"] = column.__doc__
    if label:
        kwargs["label"] = label

    if column.default:
        kwargs.setdefault("default", column.default.arg)

    return field_type(**kwargs)

txt_field = partial(construct_field, TextField)
int_field = partial(construct_field, IntegerField)
float_field = partial(construct_field, FloatField)