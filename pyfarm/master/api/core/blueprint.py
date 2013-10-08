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
API Blueprint
=============

Base :class:`flask.Blueprint` object used to construct PyFarm's
REST api.
"""

from flask import Blueprint


class APIBlueprint(Blueprint):
    VERSION = 1
    PREFIX = "/v%s" % VERSION

    # TODO: application (aka import) name is pyfarm.api
    # TODO: add response update so the default is application/json
    # TODO: standard method for error ourput (errorno, [href], [error], [description])
    # TODO: wrapper/integration with the flask MethodView class
    pass