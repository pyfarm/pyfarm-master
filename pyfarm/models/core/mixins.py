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
Mixin Classes
=============

Module containing mixins which can be used by multiple models.
"""

from datetime import datetime

try:
    from collections import namedtuple
except ImportError:
    from pyfarm.core.backports import namedtuple

from sqlalchemy.orm import validates, class_mapper

from pyfarm.core.enums import DBWorkState, _WorkState, Values
from pyfarm.core.logger import getLogger
from pyfarm.core.config import read_env_int
from pyfarm.models.core.types import IPAddress


logger = getLogger("models.mixin")

# stores information about a model's columns
# and relationships
ModelTypes = namedtuple(
    "ModelTypes",
    ("primary_keys", "columns", "required", "relationships"))


class ValidatePriorityMixin(object):
    """
    Mixin that adds a `state` column and uses a class
    level `STATE_ENUM` attribute to assist in validation.
    """
    MIN_PRIORITY = read_env_int("PYFARM_QUEUE_MIN_PRIORITY", -1000)
    MAX_PRIORITY = read_env_int("PYFARM_QUEUE_MAX_PRIORITY", 1000)

    # quick check of the configured data
    assert MAX_PRIORITY >= MIN_PRIORITY, "MIN_PRIORITY must be <= MAX_PRIORITY"

    @validates("priority")
    def validate_priority(self, key, value):
        """ensures the value provided to priority is valid"""
        if self.MIN_PRIORITY <= value <= self.MAX_PRIORITY:
            return value

        err_args = (key, self.MIN_PRIORITY, self.MAX_PRIORITY)
        raise ValueError("%s must be between %s and %s" % err_args)

    @validates("attempts")
    def validate_attempts(self, key, value):
        """ensures the number of attempts provided is valid"""
        if value > 0 or value is None:
            return value

        raise ValueError("%s cannot be less than zero" % key)


class ValidateWorkStateMixin(object):
    STATE_ENUM = NotImplemented

    def validate_state(self, key, value):
        """Ensures that ``value`` is a member of ``STATE_ENUM``"""
        assert self.STATE_ENUM is not NotImplemented

        if value not in self.STATE_ENUM:
            raise ValueError("`%s` is not a valid state" % value)

        return value

    @validates("state")
    def validate_state_column(self, key, value):
        """validates the state column"""
        return self.validate_state(key, value)


class WorkStateChangedMixin(object):
    """
    Mixin which adds a static method to be used when the model
    state changes
    """
    @staticmethod
    def stateChangedEvent(target, new_value, old_value, initiator):
        """update the datetime objects depending on the new value"""
        if new_value == _WorkState.RUNNING:
            target.time_started = datetime.now()
            target.time_finished = None

            if target.attempts is None:
                target.attempts = 1
            else:
                target.attempts += 1

        elif new_value == _WorkState.DONE or new_value == _WorkState.FAILED:
            if target.time_started is None:  # pragma: no cover
                msg = "job %s has not been started yet, state is " % target.id
                msg += "being set to %s" % DBWorkState._map[new_value]
                logger.warning(msg)

            target.time_finished = datetime.now()


class UtilityMixins(object):
    """
    Mixins which can be used to produce dictionaries
    of existing data.

    :const dict DICT_CONVERT_COLUMN:
        A dictionary containing key value pairs of attribute names
        and a function to retrieve the attribute.  The function should
        take a single input and return the value itself.  Optionally,
        you can also use the ``NotImplemented`` object to exclude
        some columns from the results.
    """
    DICT_CONVERT_COLUMN = {}

    def _to_dict_column(self, name):
        """
        Default method used by :meth:`.to_dict` to convert a column to
        a standard value.
        """
        value = getattr(self, name)
        if isinstance(value, Values):
            return value.str
        elif isinstance(value, IPAddress):
            return str(value)
        else:
            return value

    def _to_dict_relationship(self, name):
        """
        Default method used by :meth:`.to_dict` to convert a relationship
        to a standard value.  In the event this method does not know
        how to unpack a relationship it will raise a ``NotImplementedError``
        """
        values = []

        for relationship in getattr(self, name):
            if name == "tags":
                values.append(relationship.tag)
            elif name == "projects":
                values.append(relationship.name)
            elif name == "software":
                values.append([relationship.name, relationship.version])
            elif name in ("tasks", "jobs"):
                values.append(relationship.id)
            else:
                raise NotImplementedError(
                    "don't know how to unpack relationships for `%s`" % name)

        return values

    def to_dict(self):
        """Produce a dictionary of existing data in the table"""
        if not isinstance(self.DICT_CONVERT_COLUMN, dict):
            raise TypeError(
                "expected %s.DICT_CONVERT_COLUMN to "
                "be a dictionary" % self.__class__.__name__)

        results = {}
        types = self.types()

        # first convert all the non-relationship columns
        for name in types.columns:
            converter = self.DICT_CONVERT_COLUMN.get(
                name, self._to_dict_column)

            if converter is NotImplemented:
                continue

            elif not callable(converter):
                raise TypeError(
                    "converter function for %s was not callable" % name)

            else:
                results[name] = converter(name)

        # now convert all of the relationships
        for name in types.relationships:
            converter = self.DICT_CONVERT_COLUMN.get(
                name, self._to_dict_relationship)

            if converter is NotImplemented:
                continue

            elif not callable(converter):
                raise TypeError(
                    "converter function for %s was not callable" % name)

            else:
                results[name] = converter(name)

        return results

    @classmethod
    def to_schema(cls):
        """
        Produce a dictionary which represents the
        table's schema in a basic format
        """
        result = {}

        for name in cls.types().columns:
            column = cls.__table__.c[name]

            try:
                column.type.python_type
            except NotImplementedError:
                result[name] = column.type.__class__.__name__
            else:
                result[name] = str(column.type)

        return result

    @classmethod
    def types(cls):
        """
        A classmethod that constructs a ``namedtuple`` object with four
        attributes:

            * primary_keys - set of all primary key(s) names
            * columns - set of all column names
            * required - set of all required columns (non-nullable wo/defaults)
            * relationships - not columns themselves but do store relationships
        """
        mapper = class_mapper(cls)
        primary_keys = set()
        columns = set()
        required = set()
        relationships = set(
            name for name, column in mapper.relationships.items())

        # create sets for all true columns, primary keys,
        # and required columns
        for name, column in mapper.mapped_table.c.items():
            columns.add(name)

            if column.primary_key:
                primary_keys.add(name)

            if column.primary_key and not column.autoincrement:
                required.add(name)

            if not column.nullable and column.default is None:
                required.add(name)

        return ModelTypes(
            primary_keys=primary_keys,
            columns=columns,
            required=required,
            relationships=relationships)


class ReprMixin(object):
    """
    Mixin which allows model classes to to convert columns into a more
    easily read object format.

    :cvar tuple REPR_COLUMNS:
        the columns to convert

    :cvar dict REPR_CONVERT_COLUMN:
        optional dictionary containing columns names and functions
        for converting to a more readable string format
    """
    REPR_COLUMNS = NotImplemented
    REPR_CONVERT_COLUMN = {}

    def __repr__(self):
        if self.REPR_COLUMNS is NotImplemented:
            return super(ReprMixin, self).__repr__()

        column_data = []
        for name in self.REPR_COLUMNS:
            convert = self.REPR_CONVERT_COLUMN.get(name, repr)
            try:
                column_data.append(
                    "%s=%s" % (name, convert(getattr(self, name))))

            except AttributeError:
                logger.warning("%s has no such column %s" % (
                    self.__class__.__name__, repr(name)))

        return "%s(%s)" % (self.__class__.__name__, ", ".join(column_data))

