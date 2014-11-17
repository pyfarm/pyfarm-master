# No shebang line, this module is meant to be imported
#
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
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
Jobtypes
============

UI endpoints allowing seeing and manipulating jobtypes via the web interface
"""

try:
    from httplib import (
        NOT_FOUND, INTERNAL_SERVER_ERROR, SEE_OTHER, BAD_REQUEST)
except ImportError:  # pragma: no cover
    from http.client import (
        NOT_FOUND, INTERNAL_SERVER_ERROR, SEE_OTHER, BAD_REQUEST)

from flask import render_template, request, redirect, flash, url_for

from sqlalchemy import desc, func, sql

from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.software import (
    JobTypeSoftwareRequirement, Software, SoftwareVersion)
from pyfarm.master.application import db

def jobtypes():
    return render_template("pyfarm/user_interface/jobtypes.html",
                           jobtypes=JobType.query)

def jobtype(jobtype_id):
    """
    UI endpoint for a single jobtype. Allows showing and updating the jobtype
    """
    jobtype = JobType.query.filter_by(id=jobtype_id).first()
    if not jobtype:
        return (render_template(
                    "pyfarm/error.html", error="Jobtype %s not found" %
                    jobtype_id), NOT_FOUND)

    if request.method == "POST":
        with db.session.no_autoflush:
            jobtype.description = request.form["description"]

            new_version = JobTypeVersion(jobtype=jobtype)
            new_version.max_batch = request.form["max_batch"].strip() or\
                sql.null()
            new_version.batch_contiguous =\
                ("batch_contiguous" in request.form and
                 request.form["batch_contiguous"] == "true")
            new_version.classname = request.form["classname"]
            new_version.code = request.form["code"]

            max_version, = db.session.query(func.max(
                    JobTypeVersion.version)).filter_by(jobtype=jobtype).first()
            new_version.version = (max_version or 0) + 1

            previous_version = JobTypeVersion.query.filter_by(
                jobtype=jobtype).order_by(desc(JobTypeVersion.version)).first()
            if previous_version:
                for requirement in previous_version.software_requirements:
                    new_requirement = JobTypeSoftwareRequirement()
                    new_requirement.jobtype_version = new_version
                    new_requirement.software = requirement.software
                    new_requirement.min_version = requirement.min_version
                    new_requirement.max_version = requirement.max_version
                    db.session.add(new_requirement)

            db.session.add(jobtype)
            db.session.add(new_version)
            db.session.commit()

            flash("Jobtype %s updated to version %s" %
                (jobtype.name, new_version.version))

            return redirect(url_for("single_jobtype_ui", jobtype_id=jobtype.id),
                            SEE_OTHER)

    else:
        latest_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by(desc(JobTypeVersion.version)).first()
        if not latest_version:
            return (render_template(
                        "pyfarm/error.html", error="Jobtype %s has no versions" %
                        jobtype_id), INTERNAL_SERVER_ERROR)


        return render_template("pyfarm/user_interface/jobtype.html",
                            jobtype=jobtype, latest_version=latest_version,
                            software_items=Software.query)

def remove_jobtype_software_requirement(jobtype_id, software_id):
    with db.session.no_autoflush:
        jobtype = JobType.query.filter_by(id=jobtype_id).first()
        if not jobtype:
            return (render_template(
                        "pyfarm/error.html", error="Jobtype %s not found" %
                        jobtype_id), NOT_FOUND)

        previous_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by(desc(JobTypeVersion.version)).first()
        if not previous_version:
            return (render_template(
                "pyfarm/error.html", error="Jobtype %s has no versions" %
                jobtype_id), INTERNAL_SERVER_ERROR)

        new_version = JobTypeVersion(jobtype=jobtype)
        new_version.max_batch = previous_version.max_batch
        new_version.batch_contiguous = previous_version.batch_contiguous
        new_version.classname = previous_version.classname
        new_version.code = previous_version.code
        new_version.version = previous_version.version + 1

        for requirement in previous_version.software_requirements:
            if requirement.software_id != software_id:
                new_requirement = JobTypeSoftwareRequirement()
                new_requirement.jobtype_version = new_version
                new_requirement.software = requirement.software
                new_requirement.min_version = requirement.min_version
                new_requirement.max_version = requirement.max_version
                db.session.add(new_requirement)

        db.session.commit()

    flash("Software requirement has been removed from jobtype %s" %
          jobtype.name)

    return redirect(url_for("single_jobtype_ui", jobtype_id=jobtype.id),
                            SEE_OTHER)

def add_jobtype_software_requirement(jobtype_id):
    with db.session.no_autoflush:
        jobtype = JobType.query.filter_by(id=jobtype_id).first()
        if not jobtype:
            return (render_template(
                        "pyfarm/error.html", error="Jobtype %s not found" %
                        jobtype_id), NOT_FOUND)

        previous_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by(desc(JobTypeVersion.version)).first()
        if not previous_version:
            return (render_template(
                "pyfarm/error.html", error="Jobtype %s has no versions" %
                jobtype_id), INTERNAL_SERVER_ERROR)

        new_version = JobTypeVersion(jobtype=jobtype)
        new_version.max_batch = previous_version.max_batch
        new_version.batch_contiguous = previous_version.batch_contiguous
        new_version.classname = previous_version.classname
        new_version.code = previous_version.code
        new_version.version = previous_version.version + 1

        for requirement in previous_version.software_requirements:
            retained_requirement = JobTypeSoftwareRequirement()
            retained_requirement.jobtype_version = new_version
            retained_requirement.software = requirement.software
            retained_requirement.min_version = requirement.min_version
            retained_requirement.max_version = requirement.max_version
            db.session.add(retained_requirement)

        new_requirement = JobTypeSoftwareRequirement()
        new_requirement.jobtype_version = new_version

        new_requirement_software = Software.query.filter_by(
            id=request.form["software"]).first()
        if not new_requirement_software:
            return (render_template(
                        "pyfarm/error.html", error="Software %s not found" %
                        request.form["software"]), NOT_FOUND)
        new_requirement.software = new_requirement_software

        if request.form["minimum_version"] != "":
            min_version = SoftwareVersion.query.filter_by(
                id=request.form["minimum_version"]).first()
            if not min_version:
                return (render_template(
                        "pyfarm/error.html", error="Software version %s not "
                        "found" %  request.form["minimum_version"]), NOT_FOUND)
            if min_version.software != new_requirement_software:
                return (render_template(
                        "pyfarm/error.html", error="Software version %s does "
                        "not belong to software %s" %
                        (min_version.version,
                         new_requirement_software.software)), BAD_REQUEST)
            new_requirement.min_version = min_version

        if request.form["maximum_version"] != "":
            max_version = SoftwareVersion.query.filter_by(
                id=request.form["maximum_version"]).first()
            if not max_version:
                return (render_template(
                        "pyfarm/error.html", error="Software version %s not "
                        "found" %  request.form["maximum_version"]), NOT_FOUND)
            if max_version.software != new_requirement_software:
                return (render_template(
                        "pyfarm/error.html", error="Software version %s does "
                        "not belong to software %s" %
                        (max_version.version,
                         new_requirement_software.software)), BAD_REQUEST)
            new_requirement.max_version = max_version

        db.session.add(new_version)
        db.session.add(new_requirement)
        db.session.commit()

    flash("Software requirement has been added to jobtype %s" %
          jobtype.name)

    return redirect(url_for("single_jobtype_ui", jobtype_id=jobtype.id),
                            SEE_OTHER)

def remove_jobtype(jobtype_id):
    with db.session.no_autoflush:
        jobtype = JobType.query.filter_by(id=jobtype_id).first()
        if not jobtype:
            return (render_template(
                        "pyfarm/error.html", error="Jobtype %s not found" %
                        jobtype_id), NOT_FOUND)

        for version in jobtype.versions:
            if version.jobs.count() > 0:
                 return (render_template(
                     "pyfarm/error.html", error="Jobtype %s cannot be deleted "
                     "because there are still jobs referencing it. Please "
                     "delete those jobs first." % jobtype.name), BAD_REQUEST)

        db.session.delete(jobtype)
        db.session.commit()

    return redirect(url_for("jobtypes_index_ui"), SEE_OTHER)

def create_jobtype():
    if request.method == "GET":
        return render_template("pyfarm/user_interface/jobtype_create.html",
                               jobtypes=JobType.query,
                               software_items=Software.query)
    else:
        with db.session.no_autoflush:
            jobtype = JobType()
            jobtype.name = request.form["name"]
            jobtype.description = request.form["description"]
            jobtype_version = JobTypeVersion()
            jobtype_version.jobtype = jobtype
            jobtype_version.version = 1
            jobtype_version.max_batch = request.form["max_batch"].strip() or\
                sql.null()
            jobtype_version.batch_contiguous =\
                ("batch_contiguous" in request.form and
                 request.form["batch_contiguous"] == "true")
            jobtype_version.classname = request.form["classname"]
            jobtype_version.code = request.form["code"]

            requirements = zip(request.form.getlist("software"),
                            request.form.getlist("min_version"),
                            request.form.getlist("min_version"))

            for requirement_tuple in requirements:
                software = Software.query.filter_by(
                    id=int(requirement_tuple[0])).first()
                if not software:
                    return (render_template(
                        "pyfarm/error.html", error="Software %s not found" %
                        requirement_tuple[0]), NOT_FOUND)
                requirement = JobTypeSoftwareRequirement()
                requirement.software = software
                requirement.jobtype_version = jobtype_version

                if requirement_tuple[1] != "":
                    minimum_version = SoftwareVersion.query.filter_by(
                        id=int(requirement_tuple[1])).first()
                    if not minimum_version:
                        return (render_template(
                            "pyfarm/error.html", error="Software version %s not "
                            "found" % requirement_tuple[1]), NOT_FOUND)
                    if minimum_version.software != software:
                        return (render_template(
                            "pyfarm/error.html", error="Software version %s "
                            "does not belong to software %s" %
                            (minimum_version.version, software.software)),
                            BAD_REQUEST)
                    requirement.min_version = minimum_version

                if requirement_tuple[2] != "":
                    maximum_version = SoftwareVersion.query.filter_by(
                        id=int(requirement_tuple[2])).first()
                    if not maximum_version:
                        return (render_template(
                            "pyfarm/error.html", error="Software version %s not "
                            "found" % requirement_tuple[2]), NOT_FOUND)
                    if maximum_version.software != software:
                        return (render_template(
                            "pyfarm/error.html", error="Software version %s "
                            "does not belong to software %s" %
                            (maximum_version.version, software.software)),
                            BAD_REQUEST)
                    requirement.max_version = maximum_version

                db.session.add(requirement)

            db.session.add(jobtype)
            db.session.add(jobtype_version)
            db.session.commit()

        flash("Jobtype %s created" % jobtype.name)

        return redirect(url_for('jobtypes_index_ui'), SEE_OTHER)
