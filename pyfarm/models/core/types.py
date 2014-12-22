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
import uuid
from json import dumps, loads
from textwrap import dedent

try:  # pragma: no cover
    from UserDict import UserDict
    from UserList import UserList
except ImportError:
    from collections import UserDict, UserList

from sqlalchemy.types import (
    TypeDecorator, BigInteger, Integer, UnicodeText, TypeEngine, VARBINARY)
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from netaddr import AddrFormatError, IPAddress as _IPAddress

from pyfarm.master.application import db
from pyfarm.core.enums import (
    STRING_TYPES, INTEGER_TYPES, _AgentState, _UseAgentAddress, _WorkState,
    _OperatingSystem, Values, PY3)

ID_DOCSTRING = dedent("""Provides an id for the current row.  This value should
                         never be directly relied upon and it's intended for use
                         by relationships.""")
NoneType = type(None)  # from stdlib types module
JSON_NONE = dumps(None)
RESUB_GUID_CHARS = re.compile("[{}-]")

# types which our custom column types will accept via json
try:
    # pylint: disable=undefined-variable
    JSON_CUSTOM_COLUMN_TYPES = (str, unicode, int, long)
except NameError:
    JSON_CUSTOM_COLUMN_TYPES = (str, int)

# global mappings which can be used in relationships by external
# tables
if db.engine.name == "sqlite":
    IDTypeWork = Integer
else:
    IDTypeWork = BigInteger

if db.engine.name == "postgresql":
    import psycopg2.extras
    psycopg2.extras.register_uuid()

IDTypeTag = Integer


class JSONSerializable(TypeDecorator):
    """
    Base of all custom types which process json data
    to and from the database.

    :var tuple serialize_types:
        the kinds of objects we expect to serialize to
        and from the database

    :var bool serialize_none:
        if True then return None instead of converting it to
        its json value

    :var bool allow_blank:
        if True, do not raise a :class:`ValueError` for empty data

    :var bool allow_empty:
        if True, do not raise :class:`ValueError` if the input data
        itself is empty
    """
    impl = UnicodeText
    serialize_types = None
    serialize_none = False

    # pylint: disable=super-on-old-class
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

        return dumps(value)

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
    json_types = list


class JSONDict(JSONSerializable):
    """Column type for storing dictionary objects as json"""
    serialize_types = (dict, UserDict)
    json_types = dict


class MACAddress(TypeDecorator):
    """
    Column type which can store and retrieve MAC addresses in a more
    efficient manner
    """
    impl = BigInteger
    MAX_INT = 0xFFFFFFFFFFFF
    json_types = JSON_CUSTOM_COLUMN_TYPES

    def process_bind_param(self, value, dialect):
        if isinstance(value, int):
            if value < 0 or value > self.MAX_INT:
                args = (value, self.__class__.__name__)
                raise ValueError("invalid integer '%s' for %s" % args)
            return value

        elif isinstance(value, STRING_TYPES):
            return int("0" + value.replace(":", ""), 16)

        elif value is None:
            return value

        else:
            raise ValueError("unexpected type %s for value" % type(value))

    def process_result_value(self, value, dialect):
        if value is not None:
            out = format((value >> 40) & 0xFF, "02x")
            out += ":"
            out += format((value >> 32) & 0xFF, "02x")
            out += ":"
            out += format((value >> 24) & 0xFF, "02x")
            out += ":"
            out += format((value >> 16) & 0xFF, "02x")
            out += ":"
            out += format((value >> 8) & 0xFF, "02x")
            out += ":"
            out += format(value & 0xFF, "02x")
            return out


class IPAddress(_IPAddress):
    """
    Custom version of :class:`netaddr.IPAddress` which can match itself
    against other instance of the same class, a string, or an integer.
    """
    def __eq__(self, other):  # pylint: disable=super-on-old-class
        if isinstance(other, STRING_TYPES):
            return str(self) == other
        elif isinstance(other, int):
            return int(self) == other
        else:
            return super(IPAddress, self).__eq__(other)

    def __ne__(self, other):  # pylint: disable=super-on-old-class
        if isinstance(other, STRING_TYPES):
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
    json_types = JSON_CUSTOM_COLUMN_TYPES

    def checkInteger(self, value):
        if value < 0 or value > self.MAX_INT:
            args = (value, self.__class__.__name__)
            raise ValueError("invalid integer '%s' for %s" % args)

        return value

    def process_bind_param(self, value, dialect):
        if isinstance(value, int):
            return self.checkInteger(value)

        elif isinstance(value, STRING_TYPES):
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

    :var enum:
        required class level variable which defines what enum
        this custom column handles

    :raises AssertionError:
        raised if ``enum`` is not set on the class
    """
    impl = Integer
    enum = NotImplemented
    json_types = JSON_CUSTOM_COLUMN_TYPES

    # pylint: disable=super-on-old-class
    def __init__(self, *args, **kwargs):
        super(EnumType, self).__init__(*args, **kwargs)
        assert self.enum is not NotImplemented, "`enum` not set"

    def process_bind_param(self, value, dialect):
        """
        Takes ``value`` and maps it to the internal integer.

        :raises ValueError:
            raised if ``value`` is not part of the class level
            ``enum`` mapping
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


class UUIDType(TypeDecorator):
    """
    Custom column type which handles UUIDs in the appropriate
    manner for various databases.
    """
    impl = TypeEngine
    json_types = uuid.UUID

    def _to_uuid(self, value):
        if isinstance(value, uuid.UUID):
            return value

        elif isinstance(value, INTEGER_TYPES):
            return uuid.UUID(int=value)

        elif PY3 and isinstance(value, bytes):
            return uuid.UUID(bytes=value)

        elif isinstance(value, STRING_TYPES):
            try:
                return uuid.UUID(value)
            except ValueError:  # pragma: no cover
                if PY3:  # We handle bytes above
                    raise
                return uuid.UUID(bytes=value)

        else:
            raise TypeError("Don't know how to handle %s" % type(value))

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(POSTGRES_UUID())

        return dialect.type_descriptor(VARBINARY(16))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        value = self._to_uuid(value)

        if dialect.name == "postgresql":
            return value

        return value.bytes

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        return self._to_uuid(value)


class OperatingSystemEnum(EnumType):
    """custom column type for working with :class:`.AgentState`"""
    enum = _OperatingSystem


class UseAgentAddressEnum(EnumType):
    """custom column type for working with :class:`.UseAgentAddress`"""
    enum = _UseAgentAddress


class AgentStateEnum(EnumType):
    """custom column type for working with :class:`.AgentState`"""
    enum = _AgentState


class WorkStateEnum(EnumType):
    """custom column type for working with :class:`.WorkState`"""
    enum = _WorkState

IDTypeAgent = UUIDType


def id_column(column_type=None, **kwargs):
    """
    Produces a column used for `id` on each table.  Typically this is done
    using a class in :mod:`pyfarm.models.mixins` however because of the ORM
    and the table relationships it's cleaner to have a function produce
    the column.
    """
    kwargs.setdefault("primary_key", True)
    kwargs.setdefault("autoincrement", True)
    kwargs.setdefault("doc", ID_DOCSTRING)
    kwargs.setdefault("nullable", False)
    return db.Column(column_type or Integer, **kwargs)

