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

PyFarm Models
=============

.. image:: https://travis-ci.org/pyfarm/pyfarm-models.png?branch=master
    :target: https://travis-ci.org/pyfarm/pyfarm-models
    :align: left

.. image:: https://coveralls.io/repos/pyfarm/pyfarm-models/badge.png?branch=master
    :target: https://coveralls.io/r/pyfarm/pyfarm-models?branch=master
    :align: left


Sub-library which contains the database models used by the admin interface and
master server(s).  These models contains information and classes for:
    * jobs and tasks
    * tagging
    * validation mixins
    * interface classes for API usage and testing

In addition to the models there's several core classes and functions which
provide additional help including:
    * central configuration of table naming and prefixes
    * custom column types to serialize and deserialize data (IP addresses/json)
    * functions to generate some common columns in a standard manner