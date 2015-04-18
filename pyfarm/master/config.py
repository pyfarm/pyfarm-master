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

"""
Configuration
============

A small wrapper around :class:`pyfarm.core.config.Configuration`
that loads in the configuration files and provides backwards
compatibility for some environment variables.
"""

import os
from pyfarm.core.config import (
    Configuration, read_env_int, read_env, read_env_bool)


def load_environment():
    """
    Provides a mapping of environment variable values to their
    configuration counterparts.
    """
    environment = {
        "autocreate_users": read_env_bool("PYFARM_AUTOCREATE_USERS", True),
        "autocreate_user_domain":
            read_env("PYFARM_AUTO_USERS_DEFAULT_DOMAIN", None),
    }

    if "PYFARM_DEFAULT_JOB_DELETE_TIME" in os.environ:
        environment.update(
            default_job_delete_time=read_env_int(
                "PYFARM_DEFAULT_JOB_DELETE_TIME")
        )

    return environment


try:
    config
except NameError:  # pragma: no cover
    config = Configuration("pyfarm.master")
    config.load(environment=load_environment())
