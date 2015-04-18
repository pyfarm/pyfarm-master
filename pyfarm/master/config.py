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
import tempfile
from functools import partial
from errno import EEXIST

from pyfarm.core.config import (
    Configuration as _Configuration, read_env_int, read_env, read_env_bool)

try:
    WindowsError
except NameError:  # pragma: no cover
    WindowsError = OSError


class Configuration(_Configuration):
    def __init__(self):
        super(Configuration, self).__init__("pyfarm.master")
        read_env_no_log = partial(read_env, log_result=False)
        overrides = {
            "secret_key": ("PYFARM_SECRET_KEY", read_env_no_log),
            "autocreate_users": ("PYFARM_AUTOCREATE_USERS", read_env_bool),
            "autocreate_user_domain": (
                "PYFARM_AUTO_USERS_DEFAULT_DOMAIN", read_env_bool),
            "default_job_delete_time": (
                "PYFARM_DEFAULT_JOB_DELETE_TIME", read_env_int),
            "login_disabled": ("PYFARM_LOGIN_DISABLED", read_env_bool),
            "pretty_json": ("PYFARM_JSON_PRETTY", read_env_bool),
            "echo_sql": ("PYFARM_SQL_ECHO", read_env_bool),
            "database": ("PYFARM_DATABASE_URI", read_env_no_log),
            "timestamp_format": ("PYFARM_TIMESTAMP_FORMAT", read_env),
            "allow_agents_from_loopback": (
                "PYFARM_DEV_ALLOW_AGENT_LOOPBACK_ADDRESSES", read_env_bool),
            "agent_updates_dir": ("PYFARM_AGENT_UPDATES_DIR", read_env),
            "agent_updates_webdir": ("PYFARM_AGENT_UPDATES_WEBDIR", read_env),
            "farm_name": ("PYFARM_FARM_NAME", read_env),
            "tasklogs_dir": ("PYFARM_LOGFILES_DIR", read_env)
        }

        self.load(environment=overrides)

        # TODO: Specialize per platform? gettempdir() is not constant on OS X.
        if self["tempdir"] is None:
            self["tempdir"] = tempfile.gettempdir()

        # Make sure tempdir exists.  In the default case
        # this should always be true.  In the non-default
        # case we won't know unless we try.
        try:
            os.makedirs(self["tempdir"])
        except (OSError, IOError, WindowsError) as error:
            if error.errno != EEXIST:
                raise

try:
    config
except NameError:  # pragma: no cover
    config = Configuration()
