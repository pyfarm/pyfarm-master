# No shebang line, this module is meant to be imported
#
# Copyright 2014 Oliver Palmer
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
Test Utilities
==============

Functions and classes mainly used during the unittests.
"""

import json
import os
import time
import warnings
import uuid
from unittest import TestCase

try:
    from httplib import (
        OK, CREATED, ACCEPTED, NO_CONTENT, BAD_REQUEST, UNAUTHORIZED,
        FORBIDDEN, NOT_FOUND, NOT_ACCEPTABLE, INTERNAL_SERVER_ERROR, CONFLICT,
        UNSUPPORTED_MEDIA_TYPE, METHOD_NOT_ALLOWED, TEMPORARY_REDIRECT)
except ImportError:
    from http.client import (
        OK, CREATED, ACCEPTED, NO_CONTENT, BAD_REQUEST, UNAUTHORIZED,
        FORBIDDEN, NOT_FOUND, NOT_ACCEPTABLE, INTERNAL_SERVER_ERROR, CONFLICT,
        UNSUPPORTED_MEDIA_TYPE, METHOD_NOT_ALLOWED, TEMPORARY_REDIRECT)

try:
    from UserDict import UserDict
except ImportError:
    from collections import UserDict

try:
    import blinker
except ImportError:
    blinker = NotImplemented

from flask import Response, json_available
from sqlalchemy.exc import SAWarning
from werkzeug.utils import cached_property
from werkzeug.datastructures import ImmutableDict

from pyfarm.master.application import get_application, db, before_request

TEST_ENVIRONMENT = ImmutableDict({
    "PYFARM_DB_PREFIX": "test%s_" % time.strftime("%M%d%Y%H%M%S"),
    "PYFARM_DB_MAX_USERNAME_LENGTH": "254",

    # agent port
    "PYFARM_AGENT_MIN_PORT": "1024",
    "PYFARM_AGENT_MAX_PORT": "65535",

    # agent cpus
    "PYFARM_AGENT_MIN_CPUS": "1",
    "PYFARM_AGENT_MAX_CPUS": "256",
    "PYFARM_AGENT_SPECIAL_CPUS": "[0]",

    # agent ram
    "PYFARM_AGENT_MIN_RAM": "16",
    "PYFARM_AGENT_MAX_RAM": "262144",
    "PYFARM_AGENT_SPECIAL_RAM": "[0]",

    # priority
    "PYFARM_QUEUE_DEFAULT_PRIORITY": "0",
    "PYFARM_QUEUE_MIN_PRIORITY": "-1000",
    "PYFARM_QUEUE_MAX_PRIORITY": "1000",

    # batching
    "PYFARM_QUEUE_DEFAULT_BATCH": "1",
    "PYFARM_QUEUE_MIN_BATCH": "1",
    "PYFARM_QUEUE_MAX_BATCH": "64",

    # requeue
    "PYFARM_QUEUE_DEFAULT_REQUEUE": "3",
    "PYFARM_QUEUE_MIN_REQUEUE": "0",
    "PYFARM_QUEUE_MAX_REQUEUE": "10",

    # cpus
    "PYFARM_QUEUE_DEFAULT_CPUS": "1",
    "PYFARM_QUEUE_MIN_CPUS": "1",  # copied from above
    "PYFARM_QUEUE_MAX_CPUS": "256",  # copied from above

    # ram
    "PYFARM_QUEUE_DEFAULT_RAM": "32",
    "PYFARM_QUEUE_MIN_RAM": "16",  # copied from above
    "PYFARM_QUEUE_MAX_RAM": "262144"  # copied from above
})


def get_test_environment(**environment):
    """
    Returns a dictionary that can be used to simulate a working
    environment.  Any key/value pairs passed in as keyword arguments
    will override the defaults.
    """
    assert isinstance(environment, (dict, UserDict))
    environment = environment.copy()

    for key, value in TEST_ENVIRONMENT.items():
        environment.setdefault(key, value)

    # if "PYFARM_DATABASE_URI" not in os.environ:
    environment.setdefault(
        "PYFARM_DATABASE_URI",
        os.environ.get("PYFARM_DATABASE_URI", "sqlite:///:memory:"))

    environment.setdefault(
        "PYFARM_CONFIG",
        os.environ.get("PYFARM_CONFIG", "debug"))

    return environment


class JsonResponseMixin(object):
    """
    Mixin with testing helper methods
    """
    @cached_property
    def json(self):
        if not json_available:  # pragma: no cover
            raise NotImplementedError

        return json.loads(self.data.decode("utf-8"))


def make_test_response(response_class=None):
    if response_class is None:
        return

    class TestResponse(response_class, JsonResponseMixin):
        pass

    return TestResponse


class BaseTestCase(TestCase):
    ENVIRONMENT_SETUP = False
    ORIGINAL_ENVIRONMENT = os.environ.copy()
    maxDiff = None

    @classmethod
    def build_environment(cls):
        """
        Sets up the current environment with some values for
        unittesting.  This must be used before any other code
        is imported otherwise

        .. warning::
            This classmethod should not be used outside of a testing context
        """
        # populate the environment
        environment = get_test_environment(**cls.ORIGINAL_ENVIRONMENT)
        for key, value in environment.items():
            os.environ.setdefault(key, value)

        # import all the models we have so the relationships
        # can be setup properly
        from pyfarm.models.agent import Agent
        from pyfarm.models.job import Job
        from pyfarm.models.jobtype import JobType
        from pyfarm.models.software import (
            Software, SoftwareVersion, JobSoftwareRequirement,
            JobTypeSoftwareRequirement)
        from pyfarm.models.tag import Tag
        from pyfarm.models.task import Task
        from pyfarm.models.user import User
        from pyfarm.models.jobqueue import JobQueue
        from pyfarm.models.gpu import GPU

        # set ENVIRONMENT_SETUP so the tests will run
        cls.ENVIRONMENT_SETUP = True

    def setup_warning_filter(self):
        for warning_class in (SAWarning, ):
            warnings.simplefilter("ignore", warning_class)

    def teardown_warning_filter(self):
        for warning_class in (SAWarning, ):
            warning_entry = ("ignore", None, warning_class, None, 0)
            while warning_entry in warnings.filters:
                warnings.filters.remove(warning_entry)

    def setup_app(self):
        """
        Constructs the application object and assigns the instance
        variables for tests.  If you're testing the master your
        sublcass will probably need to extend this method.
        """
        environment = os.environ.copy()
        environment.setdefault("app_name", uuid.uuid4().hex)
        self.app = get_application(**environment)

        @self.app.before_request
        def before_request_handler():
            return before_request()

        # construct response class so we can use the json methods
        # in our handlers
        self._original_response_class = self.app.response_class
        self.app.response_class = make_test_response(self.app.response_class)

        # construct and push the context
        self._context = self.app.test_request_context()
        self._context.push()

    def setup_client(self, app):
        """returns the test client from the given application instance"""
        self.client = app.test_client()

    def setup_database(self):
        db.create_all()

    def teardown_database(self):
        db.session.remove()
        db.drop_all()

    def teardown_app(self):
        self.app.response_class = self._original_response_class

    def setUp(self):
        # be sure this value has been set first, not doing so
        # could cause some dangerous behaviors (such as testing
        # on production data)
        if not self.ENVIRONMENT_SETUP:
            self.fail(
                "build_environment() not called, aborting due to "
                "possibility of dangerous behaviors")

        self.setup_warning_filter()
        self.setup_app()
        self.setup_client(self.app)
        self.setup_database()

    def tearDown(self):
        self.teardown_app()
        self.teardown_database()
        self.teardown_warning_filter()

    def assert_contents_equal(self, a_source, b_source):
        """
        Explicitly check to see of the two iterable objects
        contain the same data.  This method exists to check to make
        sure two iterables contain the same data without regards to order. This
        is mostly meant for cases where two lists contain unhashable
        types.
        """
        # for now, we only support lists
        self.assertIsInstance(a_source, list)
        self.assertIsInstance(b_source, list)
        a_copy = a_source[:]
        b_copy = b_source[:]

        for a_value, b_value in zip(a_source, b_source):
            self.assertIn(a_value, b_source)
            self.assertIn(b_value, a_source)
            a_copy.pop()
            b_copy.pop()

        # There should not be any data left over after the above
        # has completed.
        self.assertEqual(len(b_copy), 0)
        self.assertEqual(len(a_copy), 0)

    def assert_status(self, response, status_code=None):
        assert status_code is not None
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status_code)

    def assert_ok(self, response):
        self.assert_status(response, status_code=OK)

    def assert_created(self, response):
        self.assert_status(response, status_code=CREATED)

    def assert_accepted(self, response):
        self.assert_status(response, status_code=ACCEPTED)

    def assert_no_content(self, response):
        self.assert_status(response, status_code=NO_CONTENT)

    def assert_temporary_redirect(self, response):
        self.assert_status(response, status_code=TEMPORARY_REDIRECT)

    def assert_method_not_allowed(self, response):
        self.assert_status(response, status_code=METHOD_NOT_ALLOWED)

    def assert_bad_request(self, response):
        self.assert_status(response, status_code=BAD_REQUEST)

    def assert_conflict(self, response):
        self.assert_status(response, status_code=CONFLICT)

    def assert_unauthorized(self, response):
        self.assert_status(response, status_code=UNAUTHORIZED)

    def assert_forbidden(self, response):
        self.assert_status(response, status_code=FORBIDDEN)

    def assert_not_found(self, response):
        self.assert_status(response, status_code=NOT_FOUND)

    def assert_not_acceptable(self, response):
        self.assert_status(response, status_code=NOT_ACCEPTABLE)

    def assert_internal_server_error(self, response):
        self.assert_status(response, status_code=INTERNAL_SERVER_ERROR)

    def assert_unsupported_media_type(self, response):
        self.assert_status(response, status_code=UNSUPPORTED_MEDIA_TYPE)