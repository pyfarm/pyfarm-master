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

read_env_no_log = partial(read_env, log_result=False)
env_bool_false = partial(read_env_bool, default=False)


class Configuration(_Configuration):
    """
    The main configuration object for the master, models and
    scheduler.  This will load in the configuration files and
    also handle any overrides present in the environment.

    :var ENVIRONMENT_OVERRIDES:
        A dictionary containing all environment variables
        we support as overrides.  This set is mainly provided
        for backwards comparability purposes or for the rare case
        where an environment override would be preferred over a
        config.
    """
    ENVIRONMENT_OVERRIDES = {
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
        "tasklogs_dir": ("PYFARM_LOGFILES_DIR", read_env),
        "flask_listen_address": (
            "PYFARM_DEV_LISTEN_ON_WILDCARD", env_bool_false),
        "dev_db_drop_all": (
            "PYFARM_DEV_APP_DB_DROP_ALL", env_bool_false),
        "dev_db_create_all": (
            "PYFARM_DEV_APP_DB_CREATE_ALL", env_bool_false),
        "instance_application": ("PYFARM_APP_INSTANCE", env_bool_false),
        "scheduler_broker": ("PYFARM_SCHEDULER_BROKER", read_env),
        "agent_poll_interval": (
            "PYFARM_AGENTS_POLL_INTERVAL", read_env_int),
        "assign_tasks_interval": (
            "PYFARM_SCHEDULER_INTERVAL", read_env_int),
        "orphaned_log_cleanup_interval": (
            "PYFARM_LOG_CLEANUP_INTERVAL", read_env_int),
        "autodelete_old_job_interval": (
            "PYFARM_AUTODELETE_INTERVAL", read_env_int),
        "compress_log_interval": (
            "PYFARM_LOG_COMPRESS_INTERVAL", read_env_int),
        "delete_job_interval": (
            "PYFARM_DELETE_HANGING_INTERVAL", read_env_int)
    }

    def __init__(self):  # pylint: disable=super-on-old-class
        super(Configuration, self).__init__("pyfarm.master")
        self.load(environment=self.ENVIRONMENT_OVERRIDES)

    def load(self, environment=None):  # pylint: disable=super-on-old-class
        """
        Overrides the default behavior of :meth:`load so we can
        support environment variables.
        """
        if environment is None:
            environment = {}
            try:
                items = self.ENVIRONMENT_OVERRIDES.iteritems
            except AttributeError:  # pragma: no cover
                items = self.ENVIRONMENT_OVERRIDES.items

            for config_var, (envvar, load_func) in items():
                if envvar in os.environ:
                    environment[config_var] = load_func(envvar)

        return super(Configuration, self).load(environment=environment)

try:
    config
except NameError:  # pragma: no cover
    config = Configuration()
