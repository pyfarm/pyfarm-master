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
        self.all_request_columns = None

    def from_json(self):
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

        if isinstance(data, dict):
            self.all_request_columns = set(data)

            # more fields were provided than we have columns for
            if not self.all_request_columns.issubset(self.all_columns):
                extra_columns = list(self.all_request_columns-self.all_columns)
                errorno, msg = APIError.EXTRA_FIELDS_ERROR
                msg = "unknown columns were included with " \
                      "the request: %s" % extra_columns
                return JSONResponse((errorno, msg), status=BAD_REQUEST)

        return data

    def get_model(self, **kwargs):
        return self.model(**kwargs)

    def __call__(self, func):
        @wraps(func)
        def caller(self_):
            data = self.from_json()
            if isinstance(data, JSONResponse):
                return data

            model = self.get_model(**data)
            if model is None:
                errorno, msg = APIError.DATABASE_ERROR
                msg = "failed to find model using %s" % data
                return JSONResponse((errorno, msg), status=BAD_REQUEST)

            try:
                return func(self_, data, model)

            except (StatementError, ValueError), e:
                errorno, msg = APIError.DATABASE_ERROR
                msg += ": %s" % e
                return JSONResponse(
                    (errorno, msg), status=INTERNAL_SERVER_ERROR)

        return caller


class put_model(RequestDecorator):
    """
    Decorator used for validating PUT data including required fields,
    non-nullable information, and ensuring we're not trying to add extra fields
    """
    def from_json(self):
        data = super(put_model, self).from_json()

        if not isinstance(data, dict):
            return data

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

        return data


class post_model(RequestDecorator):
    """
    Decorator which will runs a few checks on the incoming
    request against the table.
    """
    def __init__(self, model, data_class=dict):
        super(post_model, self).__init__(model, data_class=data_class)
        self.all_columns.add("id")

    def from_json(self):
        data = super(post_model, self).from_json()

        if not isinstance(data, dict):
            return data

        # id not provided
        elif "id" not in data:
            errorno, msg = APIError.MISSING_FIELDS
            msg = "id field is missing"
            return JSONResponse((errorno, msg), status=BAD_REQUEST)

        # empty id provided
        elif not data["id"] and data["id"] != 0:
            errorno, msg = APIError.MISSING_FIELDS
            msg = "id field is not populated"
            return JSONResponse((errorno, msg), status=BAD_REQUEST)

        else:
            return data

    def get_model(self, **kwargs):
        return self.model.query.filter_by(id=kwargs["id"]).first()
