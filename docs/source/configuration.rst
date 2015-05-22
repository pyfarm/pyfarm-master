.. _Configuration: https://pyfarm.readthedocs.org/projects/pyfarm-core/en/latest/modules/pyfarm.core.config.html#pyfarm.core.config.Configuration

Configuration Files
===================

Below are the configuration files for this subproject.  These files are
installed along side the source code when the package is installed.  These are
only the defaults however, you can always override these values in your own
environment.  See the Configuration_ object documentation for more detailed
information.

Master
------

The below is the current configuration file for the agent.  This
file lives at ``pyfarm/master/etc/master.yml`` in the source tree.

.. literalinclude:: ../../pyfarm/master/etc/master.yml
    :language: yaml
    :lines: 14-
    :linenos:


Models
------

The below is the current configuration file for job types.  This
file lives at ``pyfarm/models/etc/models.yml`` in the source tree.

.. literalinclude:: ../../pyfarm/models/etc/models.yml
    :language: yaml
    :lines: 14-
    :linenos:


Scheduler
---------

The below is the current configuration file for job types.  This
file lives at ``pyfarm/scheduler/etc/scheduler.yml`` in the source tree.

.. literalinclude:: ../../pyfarm/scheduler/etc/scheduler.yml
    :language: yaml
    :lines: 14-
    :linenos:

