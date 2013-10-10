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
from pyfarm.master.utility import JSONResponse, TemplateDictionary

# template for all json errors
json_error_template = TemplateDictionary(
    {"errorno": None,
     "error": None,
     "description": None})


def error_400(e):
    if request.mimetype == "application/json":
        data = json_error_template()
        data["errorno"] = 400
        data["error"] = "BAD REQUEST"
        return JSONResponse(response=data, status=400)
    else:
        return render_template(
            "pyfarm/errors/400.html", url=request.url), 400


def error_401(e):
    if request.mimetype == "application/json":
        data = json_error_template()
        data["errorno"] = 401
        data["error"] = "UNAUTHORIZED"
        data["description"] = "unauthorized access to %s" % request.url
        return JSONResponse(response=data, status=401)
    else:
        return render_template(
            "pyfarm/errors/401.html", url=request.url), 401


def error_404(e):
    if request.mimetype == "application/json":
        data = json_error_template()
        data["errorno"] = 404
        data["error"] = "NOT FOUND"
        data["description"] = "%s could not be found" % request.url
        return JSONResponse(response=data, status=404)
    else:
        return render_template(
            "pyfarm/errors/404.html", url=request.url), 404


def error_500(e):
    if request.mimetype == "application/json":
        data = json_error_template()
        data["errorno"] = 500
        data["error"] = "INTERNAL SERVER ERROR"
        data["description"] = "the server produce an error while serving " \
                              "a request for %s" % request.url
        return JSONResponse(response=data, status=500)
    else:
        return render_template(
            "pyfarm/errors/500.html", url=request.url), 500
