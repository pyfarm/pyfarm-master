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
variables have defaults defined in the configuration under `PYFARM_DB_<value>`

:const string TABLE_PREFIX:
    Prefix for all tables

:const string TABLE_SOFTWARE:
    Stores the name of the table for software items

:const string TABLE_TAG:
    Stores the name of the table for tags

:const string TABLE_AGENT:
    Stores the name of the table for agents

:const string TABLE_AGENT_TAGS:
    Stores the name of the table for agent tags

:const string TABLE_JOB:
    Stores the name of the table for jobs

:const string TABLE_JOB_TAG:
    Stores the name of the table for job tags

:const string TABLE_TASK:
    Stores the name of the table for job tasks

:const string TABLE_USERS_USER:
    Stores the registered users (both human and api)

:const string TABLE_USERS_ROLE:
    Stores roles in which a user can operate in

:const string TABLE_USERS_USER_ROLE:
    Stores relationships between :const:`.TABLE_USERS_USER` and
    :const:`.TABLE_USERS_ROLE`

:const string TABLE_JOB_QUEUES:
    Stores the name of the table for job queues

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

from pyfarm.core.config import read_env, read_env_int

# table names
TABLE_PREFIX = read_env("PYFARM_DB_PREFIX", "pyfarm_")
TABLE_SOFTWARE = "%ssoftware" % TABLE_PREFIX
TABLE_SOFTWARE_VERSION = "%s_version" % TABLE_SOFTWARE
TABLE_TAG = "%stag" % TABLE_PREFIX
TABLE_AGENT = "%sagents" % TABLE_PREFIX
TABLE_AGENT_SOFTWARE_VERSION_ASSOC = "%s_software_version_assoc" % TABLE_AGENT
TABLE_AGENT_TAG_ASSOC = "%s_tag_assoc" % TABLE_AGENT
TABLE_JOB = "%sjobs" % TABLE_PREFIX
TABLE_JOB_TYPE = "%s_jobtypes" % TABLE_JOB
TABLE_JOB_TYPE_VERSION = "%s_versions" % TABLE_JOB_TYPE
TABLE_JOB_TAG_ASSOC = "%s_tag_assoc" % TABLE_JOB
TABLE_JOB_DEPENDENCIES = "%s_dependencies" % TABLE_JOB
TABLE_JOB_SOFTWARE_REQ = "%s_software_req" % TABLE_JOB
TABLE_JOB_TYPE_SOFTWARE_REQ = "%sjobtype_software_req" % TABLE_PREFIX
TABLE_TASK = "%stask" % TABLE_PREFIX
TABLE_TASK_DEPENDENCIES = "%s_dependencies" % TABLE_TASK
TABLE_USERS = "%susers" % TABLE_PREFIX
TABLE_USERS_PROJECTS = "%s_projects" % TABLE_USERS
TABLE_USERS_USER = "%s_users" % TABLE_USERS
TABLE_USERS_ROLE = "%s_roles" % TABLE_USERS
TABLE_USERS_USER_ROLES = "%s_user_roles" % TABLE_USERS
TABLE_PROJECT = "%sprojects" % TABLE_PREFIX
TABLE_PROJECT_AGENTS = "%s_agents" % TABLE_PROJECT
TABLE_JOB_QUEUE = "%sjob_queues" % TABLE_PREFIX

TABLES = (TABLE_SOFTWARE, TABLE_SOFTWARE_VERSION, TABLE_TAG,
          TABLE_AGENT_SOFTWARE_VERSION_ASSOC, TABLE_AGENT, TABLE_JOB_TYPE,
          TABLE_AGENT_TAG_ASSOC, TABLE_USERS_USER, TABLE_USERS_ROLE,
          TABLE_USERS_USER_ROLES, TABLE_TASK, TABLE_TASK_DEPENDENCIES,
          TABLE_JOB_DEPENDENCIES, TABLE_JOB_TAG_ASSOC, TABLE_JOB_SOFTWARE_REQ,
          TABLE_JOB_TYPE_SOFTWARE_REQ, TABLE_JOB, TABLE_PROJECT,
          TABLE_PROJECT_AGENTS, TABLE_USERS_PROJECTS, TABLE_JOB_TYPE_VERSION,
          TABLE_JOB_QUEUE)

# column lengths
MAX_HOSTNAME_LENGTH = read_env_int("PYFARM_DB_MAX_HOSTNANE_LENGTH", 255)
MAX_JOBTITLE_LENGTH = read_env_int("PYFARM_DB_MAX_JOBTTITLE_LENGTH", 255)
MAX_JOBTYPE_LENGTH = read_env_int("PYFARM_DB_MAX_JOBTYPE_LENGTH", 64)
MAX_COMMAND_LENGTH = read_env_int("PYFARM_DB_MAX_COMMAND_LENGTH", 64)
MAX_USERNAME_LENGTH = read_env_int("PYFARM_DB_MAX_USERNAME_LENGTH", 255)
MAX_EMAILADDR_LENGTH = read_env_int("PYFARM_DB_MAX_EMAILADDR_LENGTH", 255)
SHA256_ASCII_LENGTH = 64  # static length of a sha256 string
MAX_ROLE_LENGTH = read_env_int("PYFARM_DB_MAX_ROLE_LENGTH", 128)
MAX_TAG_LENGTH = read_env_int("PYFARM_DB_MAX_TAG_LENGTH", 64)
MAX_PROJECT_NAME_LENGTH = read_env_int("PYFARM_DB_MAX_PROJECT_NAME_LENGTH", 32)
MAX_JOBQUEUE_NAME_LENGTH = read_env_int("PYFARM_MAX_JOBQUEUE_NAME_LENGTH", 255)
