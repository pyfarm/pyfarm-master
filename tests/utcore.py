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
import shutil
import tempfile
from random import randint
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

TEST_CONFIG = {
    "agent.min_port": 1025, "agent.max_port": 65535,
    "agent.min_cpus": 1, "agent.max_cpus": 2147483647,
    "agent.min_ram": 32, "agent.max_ram": 2147483647,
    "job.priority": 500, "job.max_username_length": 254,
    "job.batch": 1, "job.requeue": True, "job.cpus": 4,
    "job.ram": 0}

cfg.update(TEST_CONFIG)

from pyfarm.models.core.app import db
from pyfarm.core.utility import randstr


def skip_on_ci(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "BUILDBOT_UUID" in os.environ or "TRAVIS" in os.environ:
            raise SkipTest
        return func(*args, **kwargs)
    return wrapper


class RandomPrivateIPGenerator(set):
    def __call__(self):
        while True:
            int_values = [10, randint(0, 255), randint(0, 255), randint(0, 255)]
            random_address = ".".join(map(str, int_values))

            if random_address not in self:
                self.add(random_address)
                return random_address


class RandomStringGenerator(set):
    def __call__(self):
        while True:
            value = randstr()
            if value not in self:
                self.add(value)
                return value


unique_ip = RandomPrivateIPGenerator()
unique_str = RandomStringGenerator()


class TestCase(unittest.TestCase):
    TEMPDIR_PREFIX = ""
    BUILDBOT_UUID = os.environ.get("BUILDBOT_UUID")
    ORIGINAL_ENVIRONMENT = {}
    temp_directories = set()

    @classmethod
    def remove(cls, path):
        assert isinstance(path, basestring), "expected a string for `path`"

        if os.path.isfile(path):
            delete = os.remove
        elif os.path.isdir(path):
            delete = shutil.rmtree
        else:
            delete = lambda path: None

        # delete the path
        try:
            delete(path)

        except (OSError, IOError):
            pass

        else:
            if path in cls.temp_directories:
                cls.temp_directories.remove(path)

    @classmethod
    def setUpClass(cls):
        cls.ORIGINAL_ENVIRONMENT = os.environ.copy()

    @classmethod
    def mktempdir(cls):
        tempdir = tempfile.mkdtemp(prefix=cls.TEMPDIR_PREFIX)
        cls.temp_directories.add(tempdir)
        return tempdir

    def setUp(self):
        self.tempdir = self.mktempdir()
        os.environ.clear()
        os.environ.update(self.ORIGINAL_ENVIRONMENT)

    def tearDown(self):
        self.remove(self.tempdir)
        map(self.remove, self.temp_directories.copy())


class ModelTestCase(TestCase):
    def setUp(self):
        super(ModelTestCase, self).setUp()
        db.create_all()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        super(ModelTestCase, self).setUp()