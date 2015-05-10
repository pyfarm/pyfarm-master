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
=============

A small wrapper around :class:`pyfarm.core.config.Configuration`
that loads in the configuration files and provides backwards
compatibility for some environment variables.
"""

import os

from pyfarm.core.config import Configuration as _Configuration

try:
    WindowsError
except NameError:  # pragma: no cover
    WindowsError = OSError


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
    ENVIRONMENT_OVERRIDES = {}

    def __init__(self):  # pylint: disable=super-on-old-class
        super(Configuration, self).__init__("pyfarm.master")
        self.load()

        # Load model configuration
        models_config = _Configuration("pyfarm.models", version=self.version)
        models_config.load()
        self.update(models_config)

        # Load scheduler configuration
        sched_config = _Configuration("pyfarm.scheduler", version=self.version)
        sched_config.load()
        self.update(sched_config)

        try:
            items = self.ENVIRONMENT_OVERRIDES.iteritems
        except AttributeError:  # pragma: no cover
            items = self.ENVIRONMENT_OVERRIDES.items

        overrides = {}
        for config_var, (envvar, load_func) in items():
            if envvar in os.environ:
                overrides[config_var] = load_func(envvar)

        self.update(overrides)

try:
    config
except NameError:  # pragma: no cover
    config = Configuration()
