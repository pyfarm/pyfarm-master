# No shebang line, this module is meant to be imported
#
# Copyright 2015 Oliver Palmer
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

import os
from unittest import TestCase
from random import randint

from pyfarm.core.config import read_env_int
from pyfarm.master.config import Configuration


class TestConfiguration(TestCase):
    def test_loads_environment_override(self):
        envvar = "PYFARM_UNITTEST_ENVVAR_OVERRIDE"
        value = randint(-1000, 1000)
        os.environ[envvar] = str(value)
        self.addCleanup(os.environ.pop, envvar)
        self.addCleanup(
            Configuration.ENVIRONMENT_OVERRIDES.pop, "unittest_override")
        Configuration.ENVIRONMENT_OVERRIDES["unittest_override"] = (
            envvar, read_env_int
        )
        config = Configuration()
        self.assertEqual(config["unittest_override"], value)
