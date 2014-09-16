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
Admin Core
==========

Functions, class, and objects form the base datatypes and
logic necessary for the admin forms.
"""

from functools import partial

from flask.ext.admin.babel import gettext
from flask.ext.admin.contrib.sqla.ajax import QueryAjaxModelLoader
from flask.ext.admin.contrib.sqla.filters import BaseSQLAFilter
from wtforms.validators import StopValidation

from pyfarm.models.agent import Agent
from pyfarm.master.application import db


def validate_model_field(form, field, function=None):
    """
    Wraps a call to an underlying function to perform field validation.
    Typically,  this is done using a partial function

    >>> from functools import partial
    >>> from pyfarm.models.agent import Agent
    >>> validate_state = partial(validate_model_field,
    ...     function=Agent.validate_state)
    """
    try:
        return function(field.name, field.data)
    except ValueError as e:
        raise StopValidation(str(e))

# resource validation wrappers
validate_hostname = partial(
    validate_model_field, function=Agent.validate_hostname)
validate_resource = partial(
    validate_model_field, function=Agent.validate_resource)


def validate_network_fields_provided(form, field):
    """
    When the form is submitted ensure that if either the IP or sub
    """


class AjaxLoader(QueryAjaxModelLoader):
    """
    Same init as Flask's QueryAjaxModelLoader except the session is
    shared and you can override the primary key

    :keyword pk:
        the name of column to use as the primary key

    :keyword fmt:
        callable function which will format the row's model
    """
    # pylint: disable=super-on-old-class
    def __init__(self, name, model, session=db.session, **options):
        pk = options.pop("pk", None)
        self.fmt = options.pop("fmt", lambda model: model.decode("utf-8"))

        super(AjaxLoader, self).__init__(name, session, model, **options)
        if pk is not None:
            self.pk = pk

    def format(self, model):
        if not model:
            return None

        return (getattr(model, self.pk), self.fmt(model))


class BaseFilter(BaseSQLAFilter):
    """
    Wrapper around :class:`.BaseSQLAFilter` which will properly
    the `table` attributes for columns which don't already have it.  This
    is required for certain types of objects, such as relationships.
    """
    column = None
    operation_text = NotImplemented

    class MapTableAttribute(object):
        def __init__(self, column):
            self.column = column

        def __getattr__(self, item):
            if item == "table":
                return self.column._parententity.class_.__table__
            return object.__getattribute__(self, item)

    # pylint: disable=super-on-old-class
    def __init__(self, column, name, options=None, data_type=None):
        if not hasattr(column, "table"):
            column = self.MapTableAttribute(column)

        super(BaseFilter, self).__init__(
            column, name, options=options, data_type=data_type)

        if self.operation_text is NotImplemented:
            raise NotImplementedError("`operation_text` was not defined")

    def __str__(self):
        return self.name

    def apply(self, query, value):
        raise NotImplementedError

    def operation(self):
        return gettext(self.operation_text)
