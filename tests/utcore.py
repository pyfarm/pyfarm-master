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

import os
import sys
import time
from functools import wraps

if sys.version_info[0:2] < (2, 7):
    import unittest2 as unittest
else:
    import unittest

try:
    import json
except ImportError:
    import simplejson as json

from nose.plugins.skip import SkipTest
from pyfarm.core.logger import disable_logging
disable_logging(True)

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


def skip_on_ci(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "BUILDBOT_UUID" in os.environ or "TRAVIS" in os.environ:
            raise SkipTest
        return func(*args, **kwargs)
    return wrapper


class ModelTestCase(unittest.TestCase):
    ORIGINAL_ENVIRONMENT = dict(os.environ.data)

    def setUp(self):
        db.session.rollback()
        os.environ.clear()
        os.environ.update(self.ORIGINAL_ENVIRONMENT)
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
