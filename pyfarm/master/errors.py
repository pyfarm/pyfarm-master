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

Custom error Flask error pages.  For failures within the REST
api these error pages are only provided as a fallback.  Typically,
those requests will be responded to directly instead of calling
:meth:`flask.abort`
"""

from flask import render_template, request
from pyfarm.master.utility import JSONResponse

ERROR_400_JSON = {u"errorno": 400, u"error": u"BAD REQUEST"}
ERROR_401_JSON = {u"errorno": 401, u"error": u"UNAUTHORIZED"}
ERROR_404_JSON = {u"errorno": 404, u"error": u"NOT FOUND"}
ERROR_500_JSON = {u"errorno": 500, u"error": u"INTERNAL SERVER ERROR"}


def error_400(e):
    """
    Populates and renders the custom 400 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return JSONResponse(ERROR_400_JSON, status=400)
    else:
        return render_template(
            "pyfarm/errors/400.html", url=request.url), 400


def error_401(e):
    """
    Populates and renders the custom 401 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return JSONResponse(ERROR_401_JSON, status=401)
    else:
        return render_template(
            "pyfarm/errors/401.html", url=request.url), 401


def error_404(e):
    """
    Populates and renders the custom 404 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return JSONResponse(ERROR_404_JSON, status=404)
    else:
        return render_template(
            "pyfarm/errors/404.html", url=request.url), 404


def error_500(e):
    """
    Populates and renders the custom 500 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return JSONResponse(ERROR_500_JSON, status=500)
    else:
        return render_template(
            "pyfarm/errors/500.html", url=request.url), 500
