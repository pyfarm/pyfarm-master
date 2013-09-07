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
from inspect import isclass
from importlib import import_module

from netaddr import IPAddress

try:
    from json import dumps, loads
except ImportError:
    from simplejson import dumps, loads

from sqlalchemy.types import (
    TypeDecorator, CHAR, BigInteger, Integer, UnicodeText)
from sqlalchemy.dialects.postgresql import UUID as PGUuid
from pyfarm.models.core.app import db

ID_GUID_DEFAULT = lambda: str(uuid4()).replace("-", "")
ID_DOCSTRING = dedent("""Provides an id for the current row.  This value should
                         never be directly relied upon and it's intended for use
                         by relationships.""")
JSON_NONE = dumps(None)
RESUB_GUID_CHARS = re.compile("[{}-]")
NoneType = type(None)  # from stdlib types module


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
    impl = CHAR

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

    def process_result_value(self, value, dialect):
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
        if not isinstance(value, self.serialize_types):
            args = (type(value), self.__class__.__name__)
            raise ValueError("unexpected type %s for `%s`" % args)

        elif NoneType in self.serialize_types and value is None:
            return self.dumps(value) if self.serialize_none else value

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
            return self.checkInteger(int(IPAddress(value)))

        elif isinstance(value, IPAddress):
            return self.checkInteger(int(value))

        else:
            raise ValueError("unexpected type %s for value" % type(value))

    def process_result_value(self, value, dialect):
        value = IPAddress(value)
        self.checkInteger(int(value))
        return value


def IDColumn(column_type=GUID):
    """
    Produces a column used for `id` on each table.  Typically this is done
    using a class in :mod:`pyfarm.models.mixins` however because of the ORM
    and the table relationships it's cleaner to have a function produce
    the column.
    """
    kwargs = {
        "primary_key": True, "unique": True, "nullable": False,
        "doc": ID_DOCSTRING}

    if column_type is GUID:
        kwargs.update(default=ID_GUID_DEFAULT)
    else:
        kwargs.update(autoincrement=True)

    return db.Column(column_type, **kwargs)

# global mappings which can be used in relationships by external
# tables
IDTypeWork = GUID
IDTypeAgent = Integer
IDTypeTag = Integer