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

:var TABLE_PREFIX:
    Prefix for all tables

:var TABLE_AGENT:
    Stores the name of the table for agents

:var TABLE_AGENT_TAGS:
    Stores the name of the table for agent tags

:var TABLE_AGENT_SOFTWARE:
    Stores the name of the table for agent software

:var TABLE_JOB:
    Stores the name of the table for jobs

:var TABLE_JOB_TAGS:
    Stores the name of the table for job tags

:var TABLE_JOB_SOFTWARE:
    Stores the name of the table for job software

:var TABLE_TASK:
    Stores the name of the table for job tasks

:var MAX_HOSTNAME_LENGTH:
    the max length of a hostname

:var MAX_JOBTYPE_LENGTH:
    the max length of a jobtype

:var MAX_COMMAND_LENGTH:
    the max length of a command (ex. `bash` or `cmd.exe`)

:var MAX_USERNAME_LENGTH:
    the max length of a username

:var MAX_TAG_LENGTH:
    the max length of a tag

    .. note::
        this value is shared amongst all tag columns and may be split into
        multiple values at a later time
"""

from pyfarm.core.config import cfg

# table names
TABLE_PREFIX = cfg.get("db.table_prefix", "pyfarm_")
TABLE_AGENT = "%sagent" % TABLE_PREFIX
TABLE_AGENT_TAGS = "%s_tags" % TABLE_AGENT
TABLE_AGENT_SOFTWARE = "%s_software" % TABLE_AGENT
TABLE_JOB = "%sjob" % TABLE_PREFIX
TABLE_JOB_TYPE = "%s_jobtype" % TABLE_JOB
TABLE_JOB_TAGS = "%s_tags" % TABLE_JOB
TABLE_JOB_SOFTWARE = "%s_software" % TABLE_JOB
TABLE_TASK = "%stask" % TABLE_PREFIX

# column lengths
MAX_HOSTNAME_LENGTH = cfg.get("db.MAX_COMMAND_LENGTH", 255)
MAX_JOBTYPE_LENGTH = cfg.get("db.MAX_JOBTYPE_LENGTH", 64)
MAX_COMMAND_LENGTH = cfg.get("db.MAX_COMMAND_LENGTH", 64)
MAX_USERNAME_LENGTH = cfg.get("db.MAX_USERNAME_LENGTH", 255)
MAX_TAG_LENGTH = cfg.get("db.MAX_TAG_LENGTH", 32)  # used by multiple columns
