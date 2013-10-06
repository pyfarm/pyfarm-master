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
from pyfarm.core.config import cfg

if "PYFARM_DATABASE_URI" not in os.environ:
    os.environ["PYFARM_DATABASE_URI"] = "sqlite:///:memory:"

if "PYFARM_CONFIG" not in os.environ:
    os.environ["PYFARM_CONFIG"] = "debug"


# Some initial configuration values before we load the models.  Some values,
# such as the table prefix are included here just so two tests don't step
# on each other (though in production it would be better to use a different DB).
cfg.update({
    "db.table_prefix": "pyfarm_unittest_%s_" % time.strftime("%M%d%Y%H%M%S"),
    "agent.min_port": 1025,
    "agent.max_port": 65535,
    "agent.min_cpus": 1,
    "agent.max_cpus": 2147483647,
    "agent.special_cpus": [0],
    "agent.min_ram": 32,
    "agent.max_ram": 2147483647,
    "agent.special_ram": [0],
    "job.priority": 500,
    "job.max_username_length": 254,
    "job.min_priority": 0,
    "job.max_priority": 1000,
    "job.batch": 1,
    "job.requeue": 1,
    "job.cpus": 4,
    "job.ram": 32})

# import all model objects into this space so relationships, foreign keys,
# and the the mapper won't have problems finding the required classes
from pyfarm.models.agent import AgentModel, AgentSoftwareModel, AgentTagsModel
from pyfarm.models.task import TaskModel
from pyfarm.models.job import JobModel, JobSoftwareModel, JobTagsModel

from pyfarm.master.application import db


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
