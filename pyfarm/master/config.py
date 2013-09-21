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
Config
======

Contains the classes required for configuring the application
object.
"""

import os
from warnings import warn
from pyfarm.core.warning import EnvironmentWarning
from uuid import uuid4


def get_session_key(warning=True):
    if "PYFARM_CSRF_SESSION_KEY" in os.environ:
        return os.environ["PYFARM_CSRF_SESSION_KEY"]
    elif warning:
        warn("$PYFARM_CSRF_SESSION_KEY is not present in the environment",
             EnvironmentWarning)

    return str(uuid4()).replace("-", "").decode("hex")


class _Prod(object):
    SECURITY_TRACKABLE = True
    WTF_CSRF_ENABLED = False
    CSRF_ENABLED = True
    CSRF_SESSION_KEY = property(fget=lambda self: get_session_key())


class Debug(_Prod):
    CSRF_SESSION_KEY = get_session_key(warning=False)


Prod = _Prod()