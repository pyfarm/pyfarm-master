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

from functools import wraps
from httplib import BAD_REQUEST, INTERNAL_SERVER_ERROR
from sqlalchemy.exc import StatementError
from flask import request
from pyfarm.core.logger import getLogger
from pyfarm.core.enums import APIError
from pyfarm.master.utility import JSONResponse, get_column_sets

logger = getLogger("api.decorators")


class RequestDecorator(object):
    def __init__(self, model, data_class=dict):
        self.model = model
        self.data_class = data_class
        self.all_columns, self.required_columns = get_column_sets(model)

    def to_json(self):
        # before doing anything else, make sure we can
        # decode the json data
        try:
            data = request.get_json()

        except ValueError, e:
            logger.error("failed to decode json from request: %s" % e)
            return JSONResponse(
                APIError.JSON_DECODE_FAILED, status=BAD_REQUEST)

        # make sure the data retrieved from the request is the class
        # we're expecting
        if not isinstance(data, self.data_class):
            logger.error("invalid json class")
            logger.debug("provided: %s, " % str(type(data)) +
                         "expected: %s" % self.data_class)
            return JSONResponse(
                APIError.UNEXPECTED_DATATYPE, status=BAD_REQUEST)

        # since we're working with a dictionary from the request
        # compare its data against the table
        if isinstance(data, dict):
            # create sets of all required columns from the request
            # which are null (as well as a complete set of all columns)
            nulled_required_columns = set()
            all_request_columns = set()
            for key, value in data.iteritems():
                all_request_columns.add(key)
                if value is None and key in self.required_columns:
                    nulled_required_columns.add(key)

            # error out if we found any columns in the request which are
            # required but not provided
            if nulled_required_columns:
                errorno, msg = APIError.UNEXPECTED_NULL
                msg = "the following required columns " \
                      "were null: %s" % nulled_required_columns
                return JSONResponse((errorno, msg), status=BAD_REQUEST)

            # more fields were provided than we have columns for
            if all_request_columns > self.all_columns:
                extra_fields = all_request_columns - self.all_columns
                errorno, msg = APIError.EXTRA_FIELDS_ERROR
                msg = "extra fields were included with " \
                      "the request: %s" % extra_fields
                return JSONResponse((errorno, msg), status=BAD_REQUEST)

        return data


class put_model(RequestDecorator):
    def __call__(self, func):
        @wraps(func)
        def caller(self_):
            data = self.to_json()
            if isinstance(data, JSONResponse):
                return data

            try:
                return func(self_, data, self.model(**data))

            except StatementError:
                return JSONResponse(
                    APIError.DATABASE_ERROR, status=INTERNAL_SERVER_ERROR)

        return caller
