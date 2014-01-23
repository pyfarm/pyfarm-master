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


try:
    from httplib import (
        OK, CREATED, ACCEPTED, NO_CONTENT, BAD_REQUEST, UNAUTHORIZED,
        FORBIDDEN, NOT_FOUND, NOT_ACCEPTABLE, INTERNAL_SERVER_ERROR)
except ImportError:
    from http.client import (
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

from pyfarm.master.entrypoints.main import load_master
from pyfarm.master.application import (
    get_application, get_admin, get_api_blueprint)


def get_test_environment(**environment):
    """
    Returns a dictionary that can be used to simulate a working
    environment.  Any key/value pairs passed in as keyword arguments
    will override the defaults.
    """
    default_environment = {
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
    }

    for key, value in default_environment.items():
        environment.setdefault(key, value)

    # if "PYFARM_DATABASE_URI" not in os.environ:
    environment.setdefault(
        "PYFARM_DATABASE_URI",
        os.environ.get("PYFARM_DATABASE_URI", "sqlite:///:memory:"))

    environment.setdefault(
        "PYFARM_CONFIG",
        os.environ.get("PYFARM_CONFIG", "debug"))

    return environment


class TestCase(unittest.TestCase):
    ORIGINAL_ENVIRONMENT = os.environ.copy()
    TEST_ENVIRONMENT = get_test_environment(**ORIGINAL_ENVIRONMENT)

    setup_environment = True

    def setUp(self):
        super(TestCase, self).setUp()

        if self.setup_environment:
            os.environ.clear()
            os.environ.update(self.TEST_ENVIRONMENT)

    def tearDown(self):
        if self.setup_environment:
            os.environ.clear()
            os.environ.update(self.ORIGINAL_ENVIRONMENT)
