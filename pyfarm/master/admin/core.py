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

import socket
from functools import partial
from flask import flash
from flask.ext.admin.babel import gettext
from flask.ext.admin.contrib.sqla.ajax import QueryAjaxModelLoader
from flask.ext.admin.contrib.sqla.filters import BaseSQLAFilter
from sqlalchemy.orm.exc import MultipleResultsFound
from wtforms.validators import StopValidation
from wtforms.fields import SelectField
from pyfarm.models.agent import AgentModel
from pyfarm.master.application import db


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


def validate_model_field(form, field, function=None):
    """
    Wraps a call to an underlying function to perform field validation.
    Typically,  this is done using a partial function

    >>> from functools import partial
    >>> from pyfarm.models.agent import AgentModel
    >>> validate_state = partial(validate_model_field,
    ...     function=AgentModel.validate_state)
    """
    try:
        return function(field.name, field.data)
    except ValueError, e:
        raise StopValidation(str(e))

# resource validation wrappers
validate_address = partial(
    validate_model_field, function=AgentModel.validate_ip_address)
validate_hostname = partial(
    validate_model_field, function=AgentModel.validate_hostname)
validate_resource = partial(
    validate_model_field, function=AgentModel.validate_resource)


def check_dns_mapping(form, field):
    """
    When a form is submitted check to see if the ip address provided matches
    the hostname.  If not, flash a warning message.
    """
    hostname = form.hostname.data
    try:
        ipaddress = socket.gethostbyname(hostname)
    except socket.error:
        ipaddress = None

    if ipaddress and ipaddress != field.data:
        args = (hostname, field.data)
        msg = "`%s` resolved to %s which does not match address provided" % args
        flash(msg, category="warning")


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
    def __init__(self, name, model, session=db.session, **options):
        pk = options.pop("pk", None)
        self.fmt = options.pop("fmt", lambda model: unicode(model))
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

    def __init__(self, column, name, options=None, data_type=None):
        if not hasattr(column, "table"):
            column = self.MapTableAttribute(column)

        super(BaseFilter, self).__init__(
            column, name, options=options, data_type=data_type)

        if self.operation_text is NotImplemented:
            raise NotImplementedError("`operation_text` was not defined")

    def apply(self, query, value):
        raise NotImplementedError

    def operation(self):
        return gettext(self.operation_text)


class FilterResultWrapper(object):
    """
    This class is a wrapper around :class:`sqlalchemy.orm.Query` objects.
    Flask-admin's form uses :meth:`sqlalchemy.orm.Query.scalar` to
    discover how many rows are in the query however for relationships this
    often returns None or raises an exception.  We catch those conditions here
    and return the value from :meth:`sqlalchemy.orm.Query.count` instead.
    """
    def __init__(self, result, failed=False):
        self._result = result
        self._failed = failed

    def __getattr__(self, attr):
        if attr == "scalar":
            if not self._failed:
                try:
                    value = self._result.scalar()
                except MultipleResultsFound:
                    value = self._result.count()

                return lambda: value or 0
            else:
                return lambda: 0

        return getattr(self._result, attr)