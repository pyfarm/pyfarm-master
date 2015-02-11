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

:const string TABLE_USER:
    Stores the registered users (both human and api)

:const string TABLE_ROLE:
    Stores roles in which a user can operate in

:const string TABLE_USERS_USER_ROLE:
    Stores relationships between :const:`.TABLE_USERS_USER` and
    :const:`.TABLE_ROLE`

:const string TABLE_JOB_QUEUES:
    Stores the name of the table for job queues

:const string TABLE_PATH_MAP:
    Stores the name of the table for path maps

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
TABLE_PREFIX = read_env("PYFARM_DB_PREFIX", "")
TABLE_SOFTWARE = "%ssoftware" % TABLE_PREFIX
TABLE_SOFTWARE_VERSION = "%s_versions" % TABLE_SOFTWARE
TABLE_TAG = "%stags" % TABLE_PREFIX
TABLE_AGENT = "%sagents" % TABLE_PREFIX
TABLE_AGENT_SOFTWARE_VERSION_ASSOC = (
    "%sagent_software_version_associations" % TABLE_PREFIX)
TABLE_AGENT_TAG_ASSOC = "%sagent_tag_associations" % TABLE_PREFIX
TABLE_AGENT_MAC_ADDRESS = "%sagent_mac_addresses" % TABLE_PREFIX
TABLE_JOB = "%sjobs" % TABLE_PREFIX
TABLE_JOB_TYPE = "%sjobtypes" % TABLE_PREFIX
TABLE_JOB_TYPE_VERSION = "%sjobtype_versions" % TABLE_PREFIX
TABLE_JOB_TAG_ASSOC = "%sjob_tag_associations" % TABLE_PREFIX
TABLE_JOB_DEPENDENCY = "%sjob_dependencies" % TABLE_PREFIX
TABLE_JOB_SOFTWARE_REQ = "%sjob_software_requirements" % TABLE_PREFIX
TABLE_JOB_NOTIFIED_USER = "%snotified_users" % TABLE_PREFIX
TABLE_JOB_TYPE_SOFTWARE_REQ = "%sjobtype_software_requirements" % TABLE_PREFIX
TABLE_TASK = "%stasks" % TABLE_PREFIX
TABLE_USER = "%susers" % TABLE_PREFIX
TABLE_ROLE = "%sroles" % TABLE_PREFIX
TABLE_USER_ROLE = "%suser_roles" % TABLE_PREFIX
TABLE_JOB_QUEUE = "%sjob_queues" % TABLE_PREFIX
TABLE_PATH_MAP = "%spath_maps" % TABLE_PREFIX
TABLE_TASK_LOG = "%stask_logs" % TABLE_PREFIX
TABLE_TASK_TASK_LOG_ASSOC = "%stask_log_associations" % TABLE_PREFIX
TABLE_GPU = "%sgpus" % TABLE_PREFIX
TABLE_GPU_IN_AGENT = "%sgpu_agent_associations" % TABLE_PREFIX

TABLES = (TABLE_SOFTWARE, TABLE_SOFTWARE_VERSION, TABLE_TAG,
          TABLE_AGENT_SOFTWARE_VERSION_ASSOC, TABLE_AGENT, TABLE_JOB_TYPE,
          TABLE_AGENT_TAG_ASSOC, TABLE_USER, TABLE_ROLE,
          TABLE_USER_ROLE, TABLE_TASK,
          TABLE_JOB_DEPENDENCY, TABLE_JOB_TAG_ASSOC, TABLE_JOB_SOFTWARE_REQ,
          TABLE_JOB_NOTIFIED_USER, TABLE_JOB_TYPE_SOFTWARE_REQ, TABLE_JOB,
          TABLE_JOB_TYPE_VERSION, TABLE_JOB_QUEUE, TABLE_PATH_MAP,
          TABLE_TASK_LOG, TABLE_TASK_TASK_LOG_ASSOC, TABLE_AGENT_MAC_ADDRESS,
          TABLE_GPU, TABLE_GPU_IN_AGENT)

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
MAX_JOBQUEUE_NAME_LENGTH = read_env_int("PYFARM_MAX_JOBQUEUE_NAME_LENGTH", 255)
MAX_JOBQUEUE_PATH_LENGTH = read_env_int("PYFARM_MAX_JOBQUEUE_PATH_LENGTH", 1024)
MAX_PATH_LENGTH = read_env_int("PYFARM_MAX_PATH_LENGTH", 512)
MAX_OSNAME_LENGTH = read_env_int("PYFARM_MAX_OSNAME_LENGTH", 128)
MAX_CPUNAME_LENGTH = read_env_int("PYFARM_MAX_CPUNAME_LENGTH", 128)
MAX_GPUNAME_LENGTH = read_env_int("PYFARM_MAX_GPUNAME_LENGTH", 128)
