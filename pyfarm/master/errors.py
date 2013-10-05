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
Error
=====

Custom error Flask error pages
"""

from flask import render_template, request


def error_404(e):
    return render_template(
        "pyfarm/errors/404.html", url=request.url), 404


def error_401(e):
    return render_template(
        "pyfarm/errors/401.html", url=request.url), 401


def error_500(e):
    return render_template(
        "pyfarm/errors/500.html", url=request.url), 500
