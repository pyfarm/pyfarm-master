.. Copyright 2013 Oliver Palmer
..
.. Licensed under the Apache License, Version 2.0 (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..   http://www.apache.org/licenses/LICENSE-2.0
..
.. Unless required by applicable law or agreed to in writing, software
.. distributed under the License is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.

PyFarm Master
=============

.. image:: https://travis-ci.org/pyfarm/pyfarm-master.svg?branch=master
    :target: https://travis-ci.org/pyfarm/pyfarm-master
    :alt: build status (master)

.. image:: https://coveralls.io/repos/pyfarm/pyfarm-master/badge?branch=master
    :target: https://coveralls.io/r/pyfarm/pyfarm-master?branch=master
    :alt: coverage

Sub-library which contains the code necessary to run an instance of the master
server.  The primary purposes of the master including serving a REST API,
running the scheduler and serving the web interface.

Python Version Support
----------------------

This library supports Python 2.7 and Python 3.3+ in one code base.  Python 2.6
and lower are not supported due to syntax differences and support for 2.6 in
external libraries.

Documentation
-------------

The documentation for this this library is hosted on
`Read The Docs <https://pyfarm.readthedocs.org/projects/pyfarm-master/en/latest/>`_.
It's generated directly from this library using sphinx (setup may vary depending
on platform)::

    virtualenv env
    . env/bin/activate
    pip install sphinx sphinxcontrib-httpdomain
    pip install -e . --egg
    make -C docs html


Testing
-------

.. note::

    A broker is required for most of the tests due to pyfarm.master's dependency
    on celery.  Redis is recommended because it's the default, least
    persistent and easiest to setup.

General Testing
+++++++++++++++

Tests are run on `Travis <https://travis-ci.org/pyfarm/pyfarm-master>`_ for
every commit.  They can also be run locally too (setup may vary depending
on platform)::

    virtualenv env
    . env/bin/activate
    pip install nose
    pip install -e . --egg
    nosetests tests/

Testing Specific Databases
++++++++++++++++++++++++++

By default tests are run against sqlite.  While this is sufficient in many
cases it's generally best to test against the database type you wish to use.
Setup wise the only difference will be in the call to ``nosetests``::

    PYFARM_DATABASE_URI="dialect+driver://username:password@host:port/database" nosetests tests/

For more information on database URIs see `sqlalchemy's documentation <http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#database-urls>`_
or the `Travis configuration <https://github.com/pyfarm/pyfarm-master/blob/master/.travis.yml>`_.
