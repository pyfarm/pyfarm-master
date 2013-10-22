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
Utility
=======

General utility which are not view or tool specific
"""

from httplib import BAD_REQUEST

try:
    from json import dumps as _dumps
except ImportError: # pragma: no cover
    from simplejson import dumps as _dumps

from werkzeug.datastructures import ImmutableDict
from flask import Response
from pyfarm.core.enums import APIError
from pyfarm.master.application import app

PRETTY_JSON = app.config["PYFARM_JSON_PRETTY"]
COLUMN_CACHE = {}


def dumps(*args, **kwargs):
    """
    Wrapper around :func:`._dumps` which does some work to respect any
    application settings.
    """
    if PRETTY_JSON:
        kwargs.setdefault("indent", 4)
    return _dumps(*args, **kwargs)


def get_column_sets(model):
    """
    returns a tuple of two sets containing all columns and required columns
    for the model provided
    """
    all_columns = set()
    required_columns = set()

    for name, column in model.__table__.c.items():
        # skip autoincremented primary keys
        if column.primary_key and column.autoincrement:
            continue

        all_columns.add(name)

        # column is non-nullable without a default
        if not column.nullable and column.default is None:
            required_columns.add(name)

    return all_columns, required_columns


class JSONResponse(Response):
    """
    Wrapper around :class:`.Response` which will set the proper content type
    and serialize any input
    """
    def __init__(self, data=None, **kwargs):
        if isinstance(data, ReducibleDictionary):
            data.reduce()

        kwargs.setdefault("content_type", "application/json")

        if data is not None:
            super(JSONResponse, self).__init__(dumps(data), **kwargs)
        else:
            super(JSONResponse, self).__init__(**kwargs)


class ReducibleDictionary(dict):
    """
    Adds a :meth:`.reduce` method to :class:`dict` class
    which will remove empty values from a dictionary.

    >>> data = ReducibleDictionary({"foo": True, "bar": None})
    >>> data.reduce()
    >>> print data
    {'foo': True}
    """
    def reduce(self):
        for key, value in self.copy().iteritems():
            if value is None:
                self.pop(key)


class TemplateDictionary(ImmutableDict):
    """
    Simple dictionary which subclasses werkzeug's :class:`.ImmutableDict`
    but allows for new instanced to be produced using :meth:`.__call__`.

    >>> template = TemplateDictionary({"foo": None})
    >>> data = template()
    >>> data["foo"] = True
    >>> data["bar"] = False
    >>> print data, template
    {'foo': True, 'bar': False} TemplateDictionary({'foo': None})

    This class is mainly meant for simple REST responses, other considerations
    should be taken for more complex structures.
    """
    def __call__(self, reducible=True):
        class_ = ReducibleDictionary if reducible else dict
        return class_(self.copy())


def json_from_request(request, all_keys=None, required_keys=None,
                      disallowed_keys=None):
    """
    Returns the json data from the request or a :class:`.JSONResponse` object
    on failure.

    :keyword set all_keys:
        a set of all possible keys which may be present in the json request

    :keyword set required_keys:
        a set of keys which must be present in the json request

    :keyword set disallowed_keys:
        a set of keys which cannot be part of the request
    """
    try:
        data = request.get_json()

    except ValueError, e:
        errorno, msg = APIError.JSON_DECODE_FAILED
        msg += ": %s" % e
        return JSONResponse((errorno, msg), status=BAD_REQUEST)

    if isinstance(data, dict) and (all_keys or required_keys or disallowed_keys):
        request_keys = set(data)

        # make sure that we don't have more request keys
        # than there are total keys
        if all_keys is not None and not request_keys.issubset(all_keys):
            errorno, msg = APIError.EXTRA_FIELDS_ERROR
            msg += ".  Extra fields were: %s" % list(request_keys - all_keys)
            return JSONResponse((errorno, msg), status=BAD_REQUEST)

        # if required keys were provided, make sure the
        # request has at least those fields
        if required_keys is not None and not \
            request_keys.issuperset(required_keys):
            missing_keys = list(required_keys-request_keys)
            errorno, msg = APIError.MISSING_FIELDS
            msg += ".  Missing fields are: %s" % missing_keys
            return JSONResponse((errorno, msg), status=BAD_REQUEST)

        if disallowed_keys is not None and \
            request_keys.issuperset(disallowed_keys):
            errorno, msg = APIError.EXTRA_FIELDS_ERROR
            disallowed_extras = list(request_keys.intersection(disallowed_keys))
            msg += ".  Extra fields were: %s" % disallowed_extras
            return JSONResponse((errorno, msg), status=BAD_REQUEST)

    return data
