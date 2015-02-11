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

from flask import render_template, request, redirect, url_for, flash

from sqlalchemy import or_
from sqlalchemy.sql.expression import func

from pyfarm.models.software import (
    Software, SoftwareVersion, JobSoftwareRequirement,
    JobTypeSoftwareRequirement)
from pyfarm.master.application import db

def software():
    software = Software.query.order_by("software desc").all()

    return render_template("pyfarm/user_interface/software.html",
                           software=software)

def software_item(software_id):
    software = Software.query.filter_by(id=software_id).first()
    if not software:
        return (render_template("pyfarm/error.html",
                                error="Software %s not found" % software_id),
                NOT_FOUND)

    versions = SoftwareVersion.query.filter_by(
        software=software).order_by("rank desc").all()

    max_rank, = db.session.query(func.max(SoftwareVersion.rank)).\
        filter(SoftwareVersion.software == software).first()

    if not max_rank:
        max_rank = 0

    # Next full hundred after max_rank, or the next full hundred after that if
    # the difference would be <= 50
    next_rank = int((round((float(max_rank) + 100) / 100) * 100))

    return render_template("pyfarm/user_interface/software_item.html",
                           software=software, versions=versions,
                           next_rank=next_rank)

def add_software():
    software = Software(software=request.form["software"])

    db.session.add(software)
    db.session.commit()

    flash("Software %s created" % software.software)

    return redirect(url_for("single_software_ui", software_id=software.id),
                    SEE_OTHER)

def remove_software(software_id):
    software = Software.query.filter_by(id=software_id).first()
    if not software:
        return (render_template("pyfarm/error.html",
                                error="Software %s not found" % software_id),
                NOT_FOUND)

    job_requirements = JobSoftwareRequirement.query.filter(
        JobSoftwareRequirement.software == software).all()
    jobtype_requirements = JobTypeSoftwareRequirement.query.filter(
        JobTypeSoftwareRequirement.software == software).all()
    if job_requirements or jobtype_requirements:
        error = ("This software cannot be deleted, it is still in use by the "
                 "following jobs or jobtypes: ")
        first = True
        for job_requirement in job_requirements:
            if not first:
                error.append(", ")
            first = False
            error.append("job %s" % job_requirement.job.title)
        for jobtype_requirements in jobtype_requirements:
            if not first:
                error.append(", ")
            first = False
            error.append("jobtype %s" %
                         jobtype_requirements.jobtype_version.jobtype.name)
        return render_template("pyfarm/error.html", error=error), BAD_REQUEST

    db.session.delete(software)
    db.session.commit()

    flash("Software %s has been removed" % software.software)

    return redirect(url_for("software_index_ui"), SEE_OTHER)

def update_version_rank(software_id, version_id):
    software = Software.query.filter_by(id=software_id).first()
    if not software:
        return (render_template("pyfarm/error.html",
                                error="Software %s not found" % software_id),
                NOT_FOUND)

    version = SoftwareVersion.query.filter_by(
        software=software, id=version_id).first()
    if not version:
        return (render_template("pyfarm/error.html",
                                error="Software %s version %s not found" %
                                    (software_id, version_id)),
                NOT_FOUND)

    version.rank = int(request.form["rank"])

    db.session.add(version)
    db.session.commit()

    flash("Rank for verson %s has been updated." % version.version)

    return redirect(url_for("single_software_ui", software_id=software.id),
                    SEE_OTHER)

def remove_software_version(software_id, version_id):
    software = Software.query.filter_by(id=software_id).first()
    if not software:
        return (render_template("pyfarm/error.html",
                                error="Software %s not found" % software_id),
                NOT_FOUND)

    version = SoftwareVersion.query.filter_by(
        software=software, id=version_id).first()
    if not version:
        return redirect(url_for("single_software_ui", software_id=software.id),
                    SEE_OTHER)

    job_requirements = JobSoftwareRequirement.query.filter(
        or_(JobSoftwareRequirement.min_version == version,
            JobSoftwareRequirement.max_version == version)).all()
    jobtype_requirements = JobTypeSoftwareRequirement.query.filter(
        or_(JobTypeSoftwareRequirement.min_version == version,
            JobTypeSoftwareRequirement.max_version == version)).all()
    if job_requirements or jobtype_requirements:
        error = ("This version cannot be deleted, it is still in use by the "
                 "following jobs or jobtypes: ")
        dependencies = []
        for job_requirement in job_requirements:
            dependencies.append("job %s" % job_requirement.job.title)
        for jobtype_requirements in jobtype_requirements:
            dependencies.append(
                "jobtype %s" % jobtype_requirements.jobtype_version.jobtype.name)
        error.append(", ".join(dependencies))
        return render_template("pyfarm/error.html", error=error), BAD_REQUEST

    db.session.delete(version)
    db.session.commit()

    flash("Version %s has been removed" % version.version)

    return redirect(url_for("single_software_ui", software_id=software.id),
                    SEE_OTHER)

def add_software_version(software_id):
    software = Software.query.filter_by(id=software_id).first()
    if not software:
        return (render_template("pyfarm/error.html",
                                error="Software %s not found" % software_id),
                NOT_FOUND)

    version = SoftwareVersion(software=software,
                              version=request.form["version"],
                              rank=int(request.form["rank"]))
    db.session.add(version)
    db.session.commit()

    flash("Version %s has been added." % version.version)

    return redirect(url_for("single_software_ui", software_id=software.id),
                    SEE_OTHER)
