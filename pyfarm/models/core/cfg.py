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
Configuration Variables
=======================

Stores basic configuration data related to tables and models.  Most of these
variables have defaults defined in the configuration under `db.<value>`

:const string TABLE_PREFIX:
    Prefix for all tables

:const string TABLE_AGENT:
    Stores the name of the table for agents

:const string TABLE_AGENT_TAGS:
    Stores the name of the table for agent tags

:const string TABLE_AGENT_SOFTWARE:
    Stores the name of the table for agent software

:const string TABLE_JOB:
    Stores the name of the table for jobs

:const string TABLE_JOB_TAG:
    Stores the name of the table for job tags

:const string TABLE_JOB_SOFTWARE:
    Stores the name of the table for job software

:const string TABLE_TASK:
    Stores the name of the table for job tasks

:const string TABLE_USERS_USER:
    Stores the registered users (both human and api)

:const string TABLE_USERS_ROLE:
    Stores roles in which a user can operate in

:const string TABLE_USERS_USER_ROLE:
    Stores relationships between :const:`.TABLE_USERS_USER` and
    :const:`.TABLE_USERS_ROLE`

:const integer MAX_HOSTNAME_LENGTH:
    the max length of a hostname

:const integer MAX_JOBTYPE_LENGTH:
    the max length of a jobtype

:const integer MAX_COMMAND_LENGTH:
    the max length of a command (ex. `bash` or `cmd.exe`)

:const integer MAX_USERNAME_LENGTH:
    the max length of a username

:const integer MAX_TAG_LENGTH:
    the max length of a tag

    .. note::
        this value is shared amongst all tag columns and may be split into
        multiple values at a later time
"""

from pyfarm.core.config import cfg

# table names
TABLE_PREFIX = cfg.get("db.table_prefix", "pyfarm_")
TABLE_AGENT = "%sagents" % TABLE_PREFIX
TABLE_AGENT_TAGS = "%s_tags" % TABLE_AGENT
TABLE_AGENT_TAGS_DEPENDENCIES = "%s_dependencies" % TABLE_AGENT
TABLE_AGENT_SOFTWARE = "%s_software" % TABLE_AGENT
TABLE_AGENT_SOFTWARE_DEPENDENCIES = "%s_dependencies" % TABLE_AGENT_SOFTWARE
TABLE_JOB = "%sjobs" % TABLE_PREFIX
TABLE_JOB_TYPE = "%s_jobtypes" % TABLE_JOB
TABLE_JOB_TAG = "%s_tags" % TABLE_JOB
TABLE_JOB_DEPENDENCIES = "%s_dependencies" % TABLE_JOB
TABLE_JOB_SOFTWARE = "%s_software" % TABLE_JOB
TABLE_TASK = "%stask" % TABLE_PREFIX
TABLE_TASK_DEPENDENCIES = "%s_dependencies" % TABLE_TASK
TABLE_USERS = "%susers" % TABLE_PREFIX
TABLE_USERS_USER = "%s_users" % TABLE_USERS
TABLE_USERS_ROLE = "%s_roles" % TABLE_USERS
TABLE_USERS_USER_ROLES = "%s_user_roles" % TABLE_USERS
TABLE_PROJECT = "%sprojects" % TABLE_PREFIX
TABLES = (TABLE_AGENT_TAGS, TABLE_AGENT_SOFTWARE, TABLE_AGENT_SOFTWARE,
          TABLE_AGENT, TABLE_AGENT_TAGS_DEPENDENCIES, TABLE_JOB_TYPE,
          TABLE_USERS_USER, TABLE_USERS_ROLE, TABLE_USERS_USER_ROLES,
          TABLE_TASK, TABLE_TASK_DEPENDENCIES, TABLE_JOB_DEPENDENCIES,
          TABLE_JOB_TAG, TABLE_JOB_SOFTWARE, TABLE_JOB, TABLE_PROJECT)

# column lengths
MAX_HOSTNAME_LENGTH = cfg.get("db.MAX_COMMAND_LENGTH", 255)
MAX_JOBTYPE_LENGTH = cfg.get("db.MAX_JOBTYPE_LENGTH", 64)
MAX_COMMAND_LENGTH = cfg.get("db.MAX_COMMAND_LENGTH", 64)
MAX_USERNAME_LENGTH = cfg.get("db.MAX_USERNAME_LENGTH", 255)
MAX_EMAILADDR_LENGTH = cfg.get("db.MAX_EMAILADDR_LENGTH", 255)
SHA256_ASCII_LENGTH = cfg.get("db.SHA256_ASCII_LENGTH", 255)
MAX_ROLE_LENGTH = cfg.get("db.MAX_ROLE_LENGTH", 128)
MAX_TAG_LENGTH = cfg.get("db.MAX_TAG_LENGTH", 32)  # used by multiple columns
