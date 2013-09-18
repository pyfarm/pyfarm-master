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

.. image:: https://travis-ci.org/pyfarm/pyfarm-master.png?branch=master
    :target: https://travis-ci.org/pyfarm/pyfarm-master
    :align: left

.. TODO: add coverage
.. .. image:: https://coveralls.io/repos/pyfarm/pyfarm-models/badge.png?branch=master
..    :target: https://coveralls.io/r/pyfarm/pyfarm-models?branch=master
..    :align: left


Sub-library which contains the code necessary to run an instance of the master
server.  Each master instance is intended to be able to serve:
    * the underlying REST api for PyFarm
    * backend for the admin interface
    * layer between requests and resources such as:
        * agents
        * queue management
        * jobs and tasks
        * progress information
        * general metrics