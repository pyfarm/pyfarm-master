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
Module containing the base test class and functions
used by the unittests.
"""

import json
import os
import time
import warnings

try:
    from http.client import (
        OK, CREATED, ACCEPTED, NO_CONTENT, BAD_REQUEST, UNAUTHORIZED,
        FORBIDDEN, NOT_FOUND, NOT_ACCEPTABLE, INTERNAL_SERVER_ERROR)
except ImportError:
    from httplib import (
        OK, CREATED, ACCEPTED, NO_CONTENT, BAD_REQUEST, UNAUTHORIZED,
        FORBIDDEN, NOT_FOUND, NOT_ACCEPTABLE, INTERNAL_SERVER_ERROR)

from pyfarm.core.enums import PY26

if PY26:
    import unittest2 as unittest
else:
    import unittest

try:
    import blinker
except ImportError:
    blinker = NotImplemented


from flask import Response, template_rendered, json_available
from sqlalchemy.exc import SAWarning
from werkzeug import cached_property

from pyfarm.core.logger import disable_logging
disable_logging(True)

from pyfarm.master.entrypoints.main import load_master
from pyfarm.master.application import (
    get_application, get_admin, get_api_blueprint)

if "PYFARM_DATABASE_URI" not in os.environ:
    os.environ["PYFARM_DATABASE_URI"] = "sqlite:///:memory:"

if "PYFARM_CONFIG" not in os.environ:
    os.environ["PYFARM_CONFIG"] = "debug"

# Some initial configuration values before we load the models.  Some values,
# such as the table prefix are included here just so two tests don't step
# on each other (though in production it would be better to use a different DB).
os.environ.update(

    PYFARM_DB_PREFIX="test%s_" % time.strftime("%M%d%Y%H%M%S"),
    PYFARM_DB_MAX_USERNAME_LENGTH="254",

    # agent port
    PYFARM_AGENT_MIN_PORT="1024",
    PYFARM_AGENT_MAX_PORT="65535",

    # agent cpus
    PYFARM_AGENT_MIN_CPUS="1",
    PYFARM_AGENT_MAX_CPUS="256",
    PYFARM_AGENT_SPECIAL_CPUS="[0]",

    # agent ram
    PYFARM_AGENT_MIN_RAM="16",
    PYFARM_AGENT_MAX_RAM="262144",
    PYFARM_AGENT_SPECIAL_RAM="[0]",

    # priority
    PYFARM_QUEUE_DEFAULT_PRIORITY="0",
    PYFARM_QUEUE_MIN_PRIORITY="-1000",
    PYFARM_QUEUE_MAX_PRIORITY="1000",

    # batching
    PYFARM_QUEUE_DEFAULT_BATCH="1",
    PYFARM_QUEUE_MIN_BATCH="1",
    PYFARM_QUEUE_MAX_BATCH="64",

    # requeue
    PYFARM_QUEUE_DEFAULT_REQUEUE="3",
    PYFARM_QUEUE_MIN_REQUEUE="0",
    PYFARM_QUEUE_MAX_REQUEUE="10",

    # cpus
    PYFARM_QUEUE_DEFAULT_CPUS="1",
    PYFARM_QUEUE_MIN_CPUS="1",  # copied from above
    PYFARM_QUEUE_MAX_CPUS="256",  # copied from above

    # ram
    PYFARM_QUEUE_DEFAULT_RAM="32",
    PYFARM_QUEUE_MIN_RAM="16",  # copied from above
    PYFARM_QUEUE_MAX_RAM="262144"  # copied from above
)

from pyfarm.master.application import db

# import all model objects into this space so relationships, foreign keys,
# and the the mapper won't have problems finding the required classes
from pyfarm.models.agent import Agent, AgentSoftware, AgentTag
from pyfarm.models.task import Task
from pyfarm.models.job import Job, JobSoftware, JobTag
from pyfarm.models.project import Project


class JsonResponseMixin(object):
    """
    Mixin with testing helper methods
    """
    @cached_property
    def json(self):
        if not json_available:  # pragma: no cover
            raise NotImplementedError
        return json.loads(self.data)


def _make_test_response(response_class):
    class TestResponse(response_class, JsonResponseMixin):
        pass

    return TestResponse


class MasterTestCase(unittest.TestCase):
    """
    Base test case for the master application.  A lot of this code is copied
    from the flask-testing package so it's kept in on place and because there's
    some issues between Python 3 and flask-testing.
    """
    ORIGINAL_ENVIRONMENT = dict(os.environ)

    # enable/disable test features
    reset_environment = True
    clean_database = False
    web_application = False

    def _template_rendered(self, app, template, context):
        self.templates_rendered.append((template, context))

    def setUp(self):
        super(MasterTestCase, self).setUp()
        warnings.simplefilter("ignore", category=SAWarning, append=True)

        if self.reset_environment:
            os.environ.clear()
            os.environ.update(self.ORIGINAL_ENVIRONMENT)

        if self.clean_database:
            db.session.rollback()

        if self.web_application:
            self.templates_rendered = []
            if blinker is not NotImplemented:
                template_rendered.connect(self._template_rendered)

            # application and test client
            self.app = get_application()

            # response class
            self._original_response_class = self.app.response_class
            self.app.response_class = _make_test_response(self.app.response_class)

            self.client = self.app.test_client()

            # context
            self._ctx = self.app.test_request_context()
            self._ctx.push()

            # internal testing end points
            self.admin = get_admin(app=self.app)
            self.api = get_api_blueprint()

            load_master(self.app, self.admin, self.api)

    def tearDown(self):
        if self.reset_environment:
            os.environ.clear()
            os.environ.update(self.ORIGINAL_ENVIRONMENT)

        if self.clean_database:
            db.session.remove()
            db.drop_all()

        if self.web_application:
            del self.templates_rendered[:]

            if blinker is not None:
                template_rendered.disconnect(self._template_rendered)

            if self.app is not None:
                self.app.response_class = self._original_response_class

    def assert_template_used(self, name, tmpl_name_attribute="name"):
        if not self.web_application:
            self.fail("`web_application` must be True to use this function")

        if blinker is NotImplemented:
            raise RuntimeError("signals module not supported")

        for template, context in self.templates_rendered:
            if getattr(template, tmpl_name_attribute) == name:
                return True
        raise AssertionError("template %s not used" % name)

    def assert_status(self, response, status_code=None):
        if not self.web_application:
            self.fail("`web_application` must be True to use this function")

        assert status_code is not None
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status_code)

    assert_ok = lambda self, response: \
        self.assert_status(response, status_code=OK)
    assert_created = lambda self, response: \
        self.assert_status(response, status_code=CREATED)
    assert_accepted = lambda self, response: \
        self.assert_status(response, status_code=ACCEPTED)
    assert_no_content = lambda self, response: \
        self.assert_status(response, status_code=NO_CONTENT)
    assert_bad_request = lambda self, response: \
        self.assert_status(response, status_code=BAD_REQUEST)
    assert_unauthorized = lambda self, response: \
        self.assert_status(response, status_code=UNAUTHORIZED)
    assert_forbidden = lambda self, response: \
        self.assert_status(response, status_code=FORBIDDEN)
    assert_not_found = lambda self, response: \
        self.assert_status(response, status_code=NOT_FOUND)
    assert_not_acceptable = lambda self, response: \
        self.assert_status(response, status_code=NOT_ACCEPTABLE)
    assert_internal_server_error = lambda self, response: \
        self.assert_status(response, status_code=INTERNAL_SERVER_ERROR)
