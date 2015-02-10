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
from collections import namedtuple

try:
    from httplib import INTERNAL_SERVER_ERROR
except ImportError:
    from http.client import INTERNAL_SERVER_ERROR

from sqlalchemy.orm import validates, class_mapper

from pyfarm.core.enums import DBWorkState, _WorkState, Values, PY2
from pyfarm.core.logger import getLogger
from pyfarm.core.config import read_env_int
from pyfarm.models.core.types import IPAddress

logger = getLogger("models.mixin")

# stores information about a model's columns
# and relationships
ModelTypes = namedtuple(
    "ModelTypes",
    ("primary_keys", "autoincrementing", "columns", "required",
     "relationships", "mappings"))


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
        if value is None or self.MIN_PRIORITY <= value <= self.MAX_PRIORITY:
            return value

        err_args = (key, self.MIN_PRIORITY, self.MAX_PRIORITY, value)
        raise ValueError(
            "%s must be between %s and %s, got %s instead" % err_args)

    @validates("attempts")
    def validate_attempts(self, key, value):
        """ensures the number of attempts provided is valid"""
        if value is None or value >= 0:
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
    def state_changed(target, new_value, old_value, initiator):
        """update the datetime objects depending on the new value"""

        if (new_value == _WorkState.RUNNING and
            (old_value not in [_WorkState.RUNNING, _WorkState.PAUSED] or
             target.time_started == None)):
            target.time_started = datetime.utcnow()
            target.time_finished = None

        elif new_value in (_WorkState.DONE, _WorkState.FAILED):
            target.time_finished = datetime.utcnow()


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
        relation = getattr(self.__class__, name)
        relation_object = getattr(self, name)

        if relation_object is None:
            return

        if relation.property.uselist:
            out = []
            for relationship in relation_object:
                if name == "tags":
                    out.append(relationship.tag)
                elif name == "projects":
                    out.append(relationship.name)
                elif name == "software":
                    out.append(relationship.name)
                elif name == "versions":
                    out.append({"id": relationship.id,
                                "version": relationship.version,
                                "rank": relationship.rank})
                elif name == "software_versions":
                    out.append({"id": relationship.id,
                                "software": relationship.software.software,
                                "version": relationship.version,
                                "rank": relationship.rank})
                elif name in ("jobs", "agents"):
                    out.append(relationship.id)
                elif name == "software_requirements":
                    out.append({"software_id": relationship.software_id,
                                "software": relationship.software.software,
                                "min_version_id": relationship.min_version_id,
                                "min_version":
                                    (relationship.min_version.version
                                     if relationship.min_version else None),
                                "max_version_id": relationship.max_version_id,
                                "max_version":
                                    (relationship.max_version.version
                                     if relationship.max_version else None)})
                elif name in ("tasks", "tasks_queued", "tasks_done",
                              "tasks_failed"):
                    out.append({"id": relationship.id,
                                "frame": relationship.frame,
                                "state": str(relationship.state)})
                elif name == "notified_users":
                    out.append({"id": relationship.user_id,
                                "username": relationship.user.username,
                                "email": relationship.user.email,
                                "on_success": relationship.on_success,
                                "on_failure": relationship.on_failure,
                                "on_deletion": relationship.on_deletion})
                elif name == "parents":
                    out.append({"id": relationship.id,
                                "title": relationship.title})
                elif name == "children":
                    out.append({"id": relationship.id,
                                "title": relationship.title})
                else:
                    raise NotImplementedError(
                        "don't know how to unpack relationships for `%s`" % name)
        else:
            if name == "software":
                out = {"software": relation_object.software,
                       "id":  relation_object.id}
            elif name == "jobtype_version":
                out = {"version": relation_object.version,
                       "jobtype": relation_object.jobtype.name}
            elif name in ("min_version", "max_version"):
                out = {"id": relation_object.id,
                       "version": relation_object.version}
            elif name == "job":
                out = {"id": relation_object.id,
                       "title": relation_object.title}
            elif name == "agent":
                out = {"id": relation_object.id,
                       "hostname": relation_object.hostname,
                       "remote_ip": str(relation_object.remote_ip),
                       "port": relation_object.port}
            elif name == "parent":
                out = {"id": relation_object.id,
                       "name": relation_object.name,
                       "priority": relation_object.priority,
                       "weight": relation_object.weight,
                       "maximum_agents": relation_object.maximum_agents,
                       "minimum_agents": relation_object.minimum_agents}
            else:
                raise NotImplementedError(
                    "don't know how to unpack relationships for `%s`" % name)

        return out

    def to_dict(self, unpack_relationships=True):
        """
        Produce a dictionary of existing data in the table

        :type unpack_relationships: list, tuple, set, bool
        :param unpack_relationships:
            If ``True`` then unpack all relationships.  If
            ``unpack_relationships`` is an iterable such as a list or
            tuple object then only unpack those relationships.
        """
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

        # unpack all relationships
        if unpack_relationships is True:
            relationships = types.relationships

        # unpack the intersection of the requested relationships
        # and the real relationships
        elif isinstance(unpack_relationships, (list, set, tuple)):
            relationships = set(unpack_relationships) & types.relationships

        else:
            relationships = set()

        for name in relationships:
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
            * autoincrementing - set of all columns which have autoincrement set
            * columns - set of all column names
            * required - set of all required columns (non-nullable wo/defaults)
            * relationships - not columns themselves but do store relationships
            * mappings - contains a dictionary with each field mapping to a
              Python type
        """
        mapper = class_mapper(cls)
        primary_keys = set()
        autoincrementing = set()
        columns = set()
        required = set()
        relationships = set(
            name for name, column in mapper.relationships.items())

        # TODO: it's possible though unlikely, based on our current tables,
        # that a relationship this could be some other than a list
        type_mapping = dict((name, list) for name in relationships)

        # create sets for all true columns, primary keys,
        # and required columns
        for name, column in mapper.c.items():
            columns.add(name)

            if column.primary_key:
                primary_keys.add(name)

            if column.autoincrement:
                autoincrementing.add(name)

            if column.primary_key and not column.autoincrement:
                required.add(name)

            if not column.nullable and column.default is None:
                required.add(name)

            # get the Python type(s)
            try:
                python_types = column.type.python_type
            except NotImplementedError:  # custom type object
                python_types = column.type.json_types

            # if we're using Python 2.x be sure that we include
            # a couple of extra types that could potentially
            # come in with a request
            if PY2 and python_types is str:
                # pylint: disable=undefined-variable
                python_types = (python_types, unicode)

            elif PY2 and python_types is int:
                # pylint: disable=undefined-variable
                python_types = (python_types, long)

            type_mapping[name] = python_types

        return ModelTypes(
            primary_keys=primary_keys,
            autoincrementing=autoincrementing,
            columns=columns,
            required=required,
            relationships=relationships,
            mappings=type_mapping)


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

