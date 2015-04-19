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

from pyfarm.core.config import read_env_int
from pyfarm.master.config import config

# table names
TABLE_PREFIX = config.get("table_prefix")
TABLE_SOFTWARE = config.get("table_software")
TABLE_SOFTWARE_VERSION = config.get("table_software_version")
TABLE_TAG = config.get("table_tag")
TABLE_AGENT = config.get("table_agent")
TABLE_AGENT_SOFTWARE_VERSION_ASSOC = \
    config.get("table_agent_software_version_assoc")
TABLE_AGENT_TAG_ASSOC = config.get("table_agent_tag_assoc")
TABLE_AGENT_MAC_ADDRESS = config.get("table_agent_mac_address")
TABLE_JOB = config.get("table_job")
TABLE_JOB_TYPE = config.get("table_job_type")
TABLE_JOB_TYPE_VERSION = config.get("table_job_type_version")
TABLE_JOB_TAG_ASSOC = config.get("table_job_tag_assoc")
TABLE_JOB_DEPENDENCY = config.get("table_job_dependency")
TABLE_JOB_SOFTWARE_REQ = config.get("table_job_software_req")
TABLE_JOB_NOTIFIED_USER = config.get("table_job_notified_users")
TABLE_JOB_TYPE_SOFTWARE_REQ = config.get("table_job_type_software_req")
TABLE_TASK = config.get("table_task")
TABLE_USER = config.get("table_user")
TABLE_ROLE = config.get("table_role")
TABLE_USER_ROLE = config.get("table_user_role")
TABLE_JOB_QUEUE = config.get("table_job_queue")
TABLE_PATH_MAP = config.get("table_path_map")
TABLE_TASK_LOG = config.get("table_task_log")
TABLE_TASK_LOG_ASSOC = config.get("table_task_log_assoc")
TABLE_GPU = config.get("table_gpu")
TABLE_GPU_IN_AGENT = config.get("table_gpu_in_agent")

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
