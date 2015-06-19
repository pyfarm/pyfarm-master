# No shebang line, this module is meant to be imported
#
# Copyright 2015 Ambient Entertainment GmbH & Co. KG
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

try:
    from httplib import NOT_FOUND, SEE_OTHER, BAD_REQUEST
except ImportError:  # pragma: no cover
    from http.client import NOT_FOUND, SEE_OTHER, BAD_REQUEST

from sqlalchemy import sql

from flask import render_template, request, flash, redirect, url_for

from pyfarm.models.software import Software, SoftwareVersion
from pyfarm.master.application import db


def software_version(software_id, version_id):
    software = Software.query.filter_by(id=software_id).first()
    if not software:
        return (render_template("pyfarm/error.html",
                                error="Software %s not found" % software_id),
                NOT_FOUND)

    version = SoftwareVersion.query.filter_by(
        software=software, id=version_id).first()
    if not version:
        return (render_template("pyfarm/error.html",
                                error="Version %s not found" % version_id),
                NOT_FOUND)

    if request.method == "POST":
        version.discovery_code =\
            request.form["discovery_code"].strip() or sql.null()
        version.discovery_function_name =\
            request.form["discovery_function"].strip() or sql.null()

        if ((version.discovery_code is None and
             version.discovery_function_name is not None) or
            (version.discovery_code is not None and
             version.discovery_function_name is None)):
                return (render_template(
                    "pyfarm/error.html",
                    error="`discovery_code` and `discovery_function_name` must "
                          "either be both unset or both set" % software_id),
                BAD_REQUEST)

        db.session.add(version)
        db.session.commit()

        flash("Discovery code for version %s has been updated." %
              version.version)

        return redirect(url_for("single_software_version_ui",
                                software_id=software.id,
                                version_id=version.id),
                        SEE_OTHER)

    else:
        return render_template("pyfarm/user_interface/software_version.html",
                               software=software, version=version)
