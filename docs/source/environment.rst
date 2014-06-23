Environment Variables
=====================
PyFarm's master and models have several environment variables which can
be used to change the operation at runtime.  For more information see the
individual sections below.

.. note::
    Not all environment variables defined below are directly used by
    PyFarm.  Many of these values are provided to make it easier to group
    settings together and so settings for PyFarm won't conflict with any
    existing software.

Database Schema
---------------
Environment variables that are used to setup or control the database backend.

.. warning::
    These values are used to construct the database schema.  If your schema
    already exists then changing these values may have uninteded consequences.


.. envvar:: PYFARM_DB_PREFIX

    The prefix for all table names.  Normally this should never be changed but
    could be for testing or similiar similiar circumstances.
    **NOTE**: making this value to long may produce errors in some databases
    such as MySQL

.. envvar:: PYFARM_DB_MAX_HOSTNAME_LENGTH

    The maximum length a hostname can be
    **Default**: 255

.. envvar:: PYFARM_DB_MAX_JOBTYPE_LENGTH

    The maximum length for the name of a jobtype.
    **Default**: 64

.. envvar:: PYFARM_DB_MAX_COMMAND_LENGTH

    The maximum length a single command can be.
    **Default**: 64

.. envvar:: PYFARM_DB_MAX_USERNAME_LENGTH

    The maximum length a username can be.
    **Default**: 255

.. envvar:: PYFARM_DB_MAX_EMAILADDR_LENGTH

    The maximum length a email address can be
    **Default**: 255

.. envvar:: PYFARM_DB_MAX_ROLE_LENGTH

    The maximum length a role can be
    **Default**: 128

.. envvar:: PYFARM_DB_MAX_TAG_LENGTH

    The maximum length a tag can be
    **Default**: 64

    **NOTE** PyFarm uses the word 'tag' in several places.  This value controls
    the max length of any string which is a tag.

.. envvar:: PYFARM_DB_MAX_PROJECT_NAME_LENGTH

    The maximum length any one project name can be.
    **Default**: 32

Database Constraints and Validation
-----------------------------------
Unlike the above section, these values are checked when a database entry is
modified or created.  They are intended to provide validation so erroneous
data cannot be inserted.  Do note however the **max** value any integer can
be raised to is 2147483647.

.. envvar:: PYFARM_AGENT_CPU_ALLOCATION

    The total amount of cpu space an agent is allowed to work in.  For example
    if four jobs requires four cpus and :envvar:`PYFARM_AGENT_CPU_ALLOCATION` is
    1.0 then all those jobs can be assigned to the agent. If
    :envvar:`PYFARM_AGENT_CPU_ALLOCATION` was .5 however only half of those jobs
    could be assigned.  This value must always be greater than 0.
    **Default**: .8

.. envvar:: PYFARM_AGENT_RAM_ALLOCATION

    Same as :envvar:`PYFARM_AGENT_CPU_ALLOCATION` except for ram resources.
    This value must always be greater than 0.
    **Default**: 1.0

.. envvar:: PYFARM_AGENT_MIN_PORT

    The minimum port an agent is allowed to communicate on.
    **Default**: 1024


.. envvar:: PYFARM_AGENT_MAX_PORT

    The maximum port an agent is allowed to communicate on.
    **Default**: 65535

.. envvar:: PYFARM_AGENT_MIN_CPUS

    The minimum number of cpus an agent is allowed to have.
    **Default**: 1

.. envvar:: PYFARM_AGENT_MAX_CPUS

    The maximum number of cpus an agent is allowed to have.
    **Default**: 256

.. envvar:: PYFARM_AGENT_MIN_RAM

    The minimum amount of ram, in megabytes, an agent is allowed to have.
    **Default**: 16

.. envvar:: PYFARM_AGENT_MAX_RAM

    The maximum amount of ram, in megabytes, an agent is allowed to have.
    **Default**: 262144

.. envvar:: PYFARM_QUEUE_MIN_PRIORITY

    The minimum priority any job or task is allowed to have.
    **Default**: -1000

.. envvar:: PYFARM_QUEUE_MAX_PRIORITY

    The maximum priority any job or task is allowed to have.
    **Default**: 1000

.. envvar:: PYFARM_QUEUE_DEFAULT_PRIORITY

    The default priority any new jobs or tasks are given
    **Default**: 0

.. envvar:: PYFARM_QUEUE_MIN_BATCH

    The minimum number of tasks which can be sent to a single agent for
    processing.
    **Default**: 1

.. envvar:: PYFARM_QUEUE_MAX_BATCH

    The maximum number of tasks which can be sent to a single agent for
    processing.
    **Default**: 64

.. envvar:: PYFARM_QUEUE_DEFAULT_BATCH

    The default number of tasks which can be sent to a single agent for
    processing.
    **Default**: 1

.. envvar:: PYFARM_QUEUE_MIN_REQUEUE

    The minimum number of times a task is allowed to reque.
    **Default**: 0

.. envvar:: PYFARM_QUEUE_MAX_REQUEUE

    The maximum number of times a task is allowed to reque.  Not setting this
    value will allow **any** tasks to reque an infinite number of times if
    requested by a user.
    **Default**: 10

.. envvar:: PYFARM_QUEUE_DEFAULT_REQUEUE

    The default number of times a task is allowed to reque.
    **Default**: 3

.. envvar:: PYFARM_QUEUE_MIN_CPUS

    The minimum number of cpus that can be required to any one job.
    **Default**: 1

.. envvar:: PYFARM_QUEUE_MAX_CPUS

    The maximum number of cpus that can be required to any one job.
    **Default**: 256

.. envvar:: PYFARM_QUEUE_DEFAULT_CPUS

    The default number of cpus required for any one job.
    **Default**: 1

.. envvar:: PYFARM_QUEUE_MIN_RAM

    The minimum amount of ram, in megabytes, that can be required for any one
    job.
    **Default**: 16

.. envvar:: PYFARM_QUEUE_MAX_RAM

    The maximum number of cpus that can be required to any one job.
    **Default**: 256

.. envvar:: PYFARM_QUEUE_DEFAULT_RAM

    The default amount of ram, in megabytes, that is required for a job.
    **Default**: 32

.. envvar:: PYFARM_REQUIRE_PRIVATE_IP

    Whether pyfarm-master should reject agents with non-private IP addresses
    **Default**: False

Master
------
Environment variables that are used within the server processes on the
master.

.. envvar:: PYFARM_CONFIG

    Controls which configuration should be loaded.  Currently the only
    supported values are `debug` and `prod` and the configuration itself
    is handled internally.

.. envvar:: PYFARM_DATABASE_URI

    The URI to connect to the backend database.  This should be a valid
    `sqlalchemy uri <http://docs.sqlalchemy.org/en/rel_0_8/core/engines.html#database-urls>`_
    which looks something like this::

        dialect+driver://user:password@host/dbname[?key=value..]

.. envvar:: PYFARM_SECRET_KEY

    When present this value is used by forms and the password storage as
    a seed value for several operations.

.. envvar:: PYFARM_CSRF_SESSION_KEY

    Key used to set the cross site request forgery key for use
    by :mod:`wtforms`.  If not provided this will be set to
    :envvar:`PYFARM_SECRET_KEY`

.. envvar:: PYFARM_JSON_PRETTY

    If set to `true` then all json output by the REST api will be human
    readable.  Setting :envvar:`PYFARM_CONFIG` to `debug` will also produce
    the same effect.

.. envvar:: PYFARM_API_VERSION

    The version of the REST api used for varying points of logic and
    for constructing :envvar:`PYFARM_API_PREFIX`

.. envvar:: PYFARM_API_PREFIX

    If set, this will establish the prefix for mounting the API.  This value
    is combined with :envvar:`PYFARM_API_VERSION` resulting in something along
    the lines of::

        https://$hostname/$PYFARM_API_PREFIX$PYFARM_API_VERSION

.. envvar:: JOBTYPE_DEFAULT_MAX_BATCH

    Performs the same function as :envvar:`PYFARM_QUEUE_MAX_BATCH` but provides
    an override specifically for :attr:`pyfarm.models.jobtype.JobType.max_batch`

.. envvar:: JOBTYPE_DEFAULT_BATCH_CONTIGUOUS

    Sets the default value for
    :attr:`pyfarm.models.jobtype.JobType.batch_contiguous`
