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
Custom Columns and Type Generators
==================================

Special column types used by PyFarm's models.
"""

import re
from textwrap import dedent
from uuid import uuid4, UUID
from UserDict import UserDict
from UserList import UserList

try:
    from json import dumps, loads
except ImportError:  # pragma: no cover
    from simplejson import dumps, loads

from sqlalchemy.types import (
    TypeDecorator, CHAR, BigInteger, Integer, UnicodeText)
from sqlalchemy.dialects.postgresql import UUID as PGUuid
from netaddr import AddrFormatError, IPAddress as _IPAddress

from pyfarm.master.application import db
from pyfarm.core.enums import (
    _AgentState, _UseAgentAddress, _WorkState, _JobTypeLoadMode, Values)

ID_GUID_DEFAULT = lambda: str(uuid4()).replace("-", "")
ID_DOCSTRING = dedent("""Provides an id for the current row.  This value should
                         never be directly relied upon and it's intended for use
                         by relationships.""")
JSON_NONE = dumps(None)
RESUB_GUID_CHARS = re.compile("[{}-]")
NoneType = type(None)  # from stdlib types module

# global mappings which can be used in relationships by external
# tables
if db.engine.name == "sqlite":
    IDTypeWork = Integer
else:
    IDTypeWork = BigInteger

IDTypeAgent = Integer
IDTypeTag = Integer


def short_guid(func):
    """decorator which shortens guids by replacing {, }, and - with ''"""
    def wrapper(*args, **kwargs):
        value = func(*args, **kwargs)
        if isinstance(value, basestring):
            value = RESUB_GUID_CHARS.sub("", value)

        return value
    return wrapper


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    .. note::
        This code is copied from sqlalchemy's standard documentation with
        some minor modifications
    """
    impl = None

    def load_dialect_impl(self, dialect):
        # Currently, pg8000 does not support the PGUuid type.  This is
        # backed up both by tests and from sqlalchemy's docs. Unfortunately,
        # there's not really much information about other drivers so we'll
        # only use the proper type where we know it should work (for now).
        if dialect.name == "postgresql" and dialect.driver == "psycopg2":
            return dialect.type_descriptor(PGUuid())
        else:
            return dialect.type_descriptor(CHAR(32))

    @short_guid
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, UUID):
                return "%.32x" % UUID(value)
            else:
                # hexstring
                return "%.32x" % value

    def process_result_value(self, value, dialect):  # pragma: no cover
        if value is None:
            return value
        else:
            return UUID(value)


class JSONSerializable(TypeDecorator):
    """
    Base of all custom types which process json data
    to and from the database.

    :cvar serialize_types:
        the kinds of objects we expect to serialize to
        and from the database

    :cvar serialize_none:
        if True then return None instead of converting it to
        its json value

    :cvar allow_blank:
        if True, do not raise a :class:`ValueError` for empty data

    :cvar allow_empty:
        if True, do not raise :class:`ValueError` if the input data
        itself is empty
    """
    impl = UnicodeText
    serialize_types = None
    serialize_none = False

    def __init__(self, *args, **kwargs):
        super(JSONSerializable, self).__init__(*args, **kwargs)

        # make sure the subclass is doing something we expect
        if self.serialize_types is None:
            raise NotImplementedError("`serialize_types` is not defined")

    def dumps(self, value):
        """
        Performs the process of dumping `value` to json.  For classes
        such as :class:`UserDict` or :class:`UserList` this will dump the
        underlying data instead of the object itself.
        """
        if isinstance(value, (UserDict, UserList)):
            value = value.data

        return unicode(dumps(value))

    def process_bind_param(self, value, dialect):
        """Converts the value being assigned into a json blob"""
        if NoneType in self.serialize_types and value is None:
            return self.dumps(value) if self.serialize_none else value
        elif NoneType not in self.serialize_types and value is None:
            return
        elif not isinstance(value, self.serialize_types):
            args = (type(value), self.__class__.__name__)
            raise ValueError("unexpected type %s for `%s`" % args)
        else:
            return self.dumps(value)

    def process_result_value(self, value, dialect):
        """Converts data from the database into a Python object"""
        if value is not None:
            value = loads(value)

        return value


class JSONList(JSONSerializable):
    """Column type for storing list objects as json"""
    serialize_types = (list, tuple, UserList)


class JSONDict(JSONSerializable):
    """Column type for storing dictionary objects as json"""
    serialize_types = (dict, UserDict)


class IPAddress(_IPAddress):
    """
    Custom version of :class:`netaddr.IPAddress` which can match itself
    against other instance of the same class, a string, or an integer.
    """
    def __eq__(self, other):
        if isinstance(other, basestring):
            return str(self) == other
        elif isinstance(other, int):
            return int(self) == other
        else:
            return super(IPAddress, self).__eq__(other)

    def __ne__(self, other):
        if isinstance(other, basestring):
            return str(self) != other
        elif isinstance(other, int):
            return int(self) != other
        else:
            return super(IPAddress, self).__ne__(other)


class IPv4Address(TypeDecorator):
    """
    Column type which can store and retrieve IPv4 addresses in a more
    efficient manner
    """
    impl = BigInteger
    MAX_INT = 4294967295

    def checkInteger(self, value):
        if value < 0 or value > self.MAX_INT:
            args = (value, self.__class__.__name__)
            raise ValueError("invalid integer '%s' for %s" % args)

        return value

    def process_bind_param(self, value, dialect):
        if isinstance(value, int):
            return self.checkInteger(value)

        elif isinstance(value, basestring):
            try:
                return self.checkInteger(int(IPAddress(value.replace("%", ""))))
            except AddrFormatError:  # pragma: no cover
                # value provided is coming from a form search
                if "%" in value:
                    return None
                raise

        elif isinstance(value, _IPAddress):
            return int(value)

        elif value is None:
            return value

        else:
            raise ValueError("unexpected type %s for value" % type(value))

    def process_result_value(self, value, dialect):
        if value is not None:
            value = IPAddress(value)
            self.checkInteger(int(value))
            return value


class EnumType(TypeDecorator):
    """
    Special column type which handles translation from a human
    readable enum into an integer that the database can use.

    :cvar enum:
        required class level variable which defines what enum
        this custom column handles

    :raises AssertionError:
        raised if :cvar:`.enum` is not set
    """
    impl = Integer
    enum = NotImplemented

    def __init__(self, *args, **kwargs):
        super(EnumType, self).__init__(*args, **kwargs)
        assert self.enum is not NotImplemented, "`enum` not set"

    def process_bind_param(self, value, dialect):
        """
        Takes ``value`` and maps it to the internal integer.

        :raises ValueError:
            raised if ``value`` is not part of :cvar:`.enum`'s mapping
        """
        if value is None:
            return None

        elif isinstance(value, Values):
            return value.int

        else:
            return self.process_result_value(value, dialect).int

    def process_result_value(self, value, dialect):
        if value is not None:
            for enum_value in self.enum:
                if value == enum_value:
                    return enum_value
            else:
                error_args = (repr(value), repr(self.enum))
                raise ValueError(
                    "failed to map %s to an enum value in %s" % error_args)

        return value


class UseAgentAddressEnum(EnumType):
    """custom column type for working with :class:`.UseAgentAddress`"""
    enum = _UseAgentAddress


class AgentStateEnum(EnumType):
    """custom column type for working with :class:`.AgentState`"""
    enum = _AgentState


class WorkStateEnum(EnumType):
    """custom column type for working with :class:`.WorkState`"""
    enum = _WorkState


class JobTypeLoadModeEnum(EnumType):
    """custom column type for working with :class:`.JobTypeLoadMode`"""
    enum = _JobTypeLoadMode


def id_column(column_type=None):
    """
    Produces a column used for `id` on each table.  Typically this is done
    using a class in :mod:`pyfarm.models.mixins` however because of the ORM
    and the table relationships it's cleaner to have a function produce
    the column.
    """
    return db.Column(
        column_type or Integer,
        primary_key=True, autoincrement=True, doc=ID_DOCSTRING, nullable=False)
