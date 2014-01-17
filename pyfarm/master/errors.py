# No shebang line, this module is meant to be imported
# -*- coding: utf-8 -*-
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

from json import dumps

try:
    from httplib import (
        BAD_REQUEST, NOT_FOUND, UNAUTHORIZED, INTERNAL_SERVER_ERROR)
except ImportError:
    from http.client import (
        BAD_REQUEST, NOT_FOUND, UNAUTHORIZED, INTERNAL_SERVER_ERROR)

from flask import render_template, request, jsonify


def error_400(e):
    """
    Populates and renders the custom 400 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return jsonify({
            "error": "unhandled bad request to %s" % request.url}), BAD_REQUEST
    else:
        return render_template(
            "pyfarm/errors/400.html", url=request.url), BAD_REQUEST


def error_401(e):
    """
    Populates and renders the custom 401 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return jsonify(
            {"error": "unhandled unauthorized request to %s" % request.url}), \
               UNAUTHORIZED
    else:
        return render_template(
            "pyfarm/errors/401.html", url=request.url), UNAUTHORIZED


def error_404(e):
    """
    Populates and renders the custom 404 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return jsonify(
            {"error":
                 "%s was not found and was not explicitly handled internally" %
                 request.url}), NOT_FOUND
    else:
        return render_template(
            "pyfarm/errors/404.html", url=request.url), NOT_FOUND


def error_500(e):
    """
    Populates and renders the custom 500 error page.  For json requests
    this will send out a response with the error number, error string,
    and a short description.
    """
    if request.mimetype == "application/json":
        return jsonify(
            {"error":
                 "unhandled internal server error when requesting %s" %
                 request.url}), INTERNAL_SERVER_ERROR
    else:
        return render_template(
            "pyfarm/errors/500.html", url=request.url), INTERNAL_SERVER_ERROR
