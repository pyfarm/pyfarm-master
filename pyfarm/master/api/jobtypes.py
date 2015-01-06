# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
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
--------

This module defines an API for managing and querying jobtypes
"""

try:
    from httplib import (
        OK, CREATED, CONFLICT, NOT_FOUND, BAD_REQUEST, NO_CONTENT,
        METHOD_NOT_ALLOWED)
except ImportError:  # pragma: no cover
    from http.client import (
        OK, CREATED, CONFLICT, NOT_FOUND, BAD_REQUEST, NO_CONTENT,
        METHOD_NOT_ALLOWED)

from flask import g, Response
from flask.views import MethodView

from sqlalchemy import or_, func, sql

from pyfarm.core.logger import getLogger
from pyfarm.core.enums import STRING_TYPES, PY3
from pyfarm.models.software import (
    Software, SoftwareVersion, JobTypeSoftwareRequirement)
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.master.application import db
from pyfarm.master.utility import jsonify

logger = getLogger("api.jobtypes")


class ObjectNotFound(Exception):
    pass


def parse_requirements(requirements):
    """
    Takes a list dicts specifying a software and optional min- and max-versions
    and returns a list of :class:`JobRequirement` objects.

    Raises TypeError if the input was not as expected or ObjectNotFound if a
    referenced software of or version was not found.

    :param list requirements:
        A list of of dicts specifying a software and optionally min_version
        and/or max_version.

    :raises TypeError:
        Raised if ``requirements`` is not a list or if an entry in
        ``requirements`` is not a dictionary.

    :raises ValueError:
        Raised if there's a problem with the content of at least one of the
        requirement dictionaries.

    :raises ObjectNotFound:
        Raised if the referenced software or version was not found
    """
    if not isinstance(requirements, list):
        raise TypeError("software_requirements must be a list")

    out = []
    for entry in requirements:
        if not isinstance(entry, dict):
            raise TypeError("Every software_requirement must be a dict")

        requirement = JobTypeSoftwareRequirement()
        software_name = entry.pop("software", None)
        if software_name is None:
            raise ValueError("Software requirement does not specify a software.")
        software = Software.query.filter_by(software=software_name).first()
        if not software:
            raise ObjectNotFound("Software %s not found" % software_name)
        requirement.software = software

        min_version_str = entry.pop("min_version", None)
        if min_version_str is not None:
            min_version = SoftwareVersion.query.filter(
                SoftwareVersion.software == software,
                SoftwareVersion.version == min_version_str).first()
            if not min_version:
                raise ObjectNotFound("Version %s of software %s not found" %
                                        (software_name, min_version_str))
            requirement.min_version = min_version

        max_version_str = entry.pop("max_version", None)
        if max_version_str is not None:
            max_version = SoftwareVersion.query.filter(
                SoftwareVersion.software == software,
                SoftwareVersion.version == max_version_str).first()
            if not max_version:
                raise ObjectNotFound("Version %s of software %s not found" %
                                     (software_name, max_version_str))
            requirement.max_version = max_version

        if entry:
            raise ValueError("Unexpected keys in software requirement: %r" %
                            entry.keys())

        out.append(requirement)
    return out


def schema():
    """
    Returns the basic schema of :class:`.JobType`

    .. http:get:: /api/v1/jobtypes/schema HTTP/1.1

        **Request**

        .. sourcecode:: http

            GET /api/v1/jobtypes/schema HTTP/1.1
            Accept: application/json

        **Response**

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "batch_contiguous": "BOOLEAN",
                "classname": "VARCHAR(64)",
                "code": "TEXT",
                "description": "TEXT",
                "id": "INTEGER",
                "version": "INTEGER",
                "max_batch": "INTEGER",
                "name": "VARCHAR(64)"
            }

    :statuscode 200:
        no error
    """
    schema_dict = JobTypeVersion.to_schema()
    schema_dict.update(JobType.to_schema())
    return jsonify(schema_dict), OK


class JobTypeIndexAPI(MethodView):
    def post(self):
        """
        A ``POST`` to this endpoint will create a new jobtype.

        .. http:post:: /api/v1/jobtypes/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobtypes/ HTTP/1.1
                Accept: application/json

                {
                    "name": "TestJobType",
                    "classname": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "code": "\\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\\n\\nclass TestJobType(JobType):\\n"
                            "    def get_command(self):\\n"
                            "        return \"/usr/bin/touch\"\\n\\n"
                            "    def get_arguments(self):\\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\\n"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "id": 1,
                    "batch_contiguous": true,
                    "software_requirements": [],
                    "version": 1,
                    "max_batch": 1,
                    "name": "TestJobType",
                    "classname": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "code": "\\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\\n\\nclass TestJobType(JobType):\\n"
                            "    def get_command(self):\\n"
                            "        return \"/usr/bin/touch\"\\n\\n"
                            "    def get_arguments(self):\\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\\n"
                }

        :statuscode 201:
            a new jobtype item was created

        :statuscode 400:
            there was something wrong with the request (such as
            invalid columns being included)

        :statuscode 409:
            a conflicting jobtype already exists
        """
        if "name" not in g.json:
            return jsonify(error="Jobtype does not specify a name"), BAD_REQUEST
        jobtype = JobType.query.filter_by(name=g.json["name"]).first()

        if jobtype:
            return (jsonify(error="Jobtype %s already exixts" %
                            g.json["name"]), CONFLICT)

        try:
            jobtype = JobType()
            jobtype.name = g.json.pop("name")
            jobtype.description = g.json.pop("description", None)
            jobtype_version = JobTypeVersion()
            jobtype_version.jobtype = jobtype
            jobtype_version.version = 1
            jobtype_version.code = g.json.pop("code")
            jobtype_version.classname = g.json.pop("classname", None)
            jobtype_version.batch_contiguous = g.json.pop("batch_contiguous",
                                                          None)
            if "max_batch" in g.json and g.json["max_batch"] is None:
                g.json.pop("max_batch")
                jobtype_version.max_batch = sql.null()
            else:
                jobtype_version.max_batch = g.json.pop("max_batch", None)
        except KeyError as e:
            return (jsonify(error="Missing key in input: %r" % e.args),
                    BAD_REQUEST)

        if "software_requirements" in g.json:
            try:
                for r in parse_requirements(g.json["software_requirements"]):
                    r.jobtype_version = jobtype_version
                    db.session.add(r)
            except (TypeError, ValueError) as e:
                return jsonify(error=e.args), BAD_REQUEST
            except ObjectNotFound as e:
                return jsonify(error=e.args), NOT_FOUND
            del g.json["software_requirements"]

        if g.json:
            return (jsonify(error="Unexpected keys in input: %r" %
                            g.json.keys()), BAD_REQUEST)

        db.session.add_all([jobtype, jobtype_version])
        db.session.commit()
        jobtype_data = jobtype_version.to_dict(unpack_relationships=False)
        jobtype_data.update(jobtype.to_dict(
            unpack_relationships=["software_requirements"]))
        del jobtype_data["jobtype_id"]
        logger.info("created jobtype %s: %r", jobtype.name, jobtype_data)

        return jsonify(jobtype_data), CREATED

    def get(self):
        """
        A ``GET`` to this endpoint will return a list of registered jobtypes.

        .. http:get:: /api/v1/jobtypes/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "id": 1,
                        "name": "TestJobType"
                    }
                ]

        :statuscode 200:
            no error
        """
        out = []
        q = db.session.query(JobType.id, JobType.name)

        for id, name in q:
            out.append({"id": id, "name": name})

        return jsonify(out), OK


class SingleJobTypeAPI(MethodView):
    def get(self, jobtype_name):
        """
        A ``GET`` to this endpoint will return the most recent version of the
        referenced jobtype, by name or id.

        .. http:get:: /api/v1/jobtypes/<str:tagname> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "batch_contiguous": true,
                    "classname": null,
                    "code": "\\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\\n\\nclass TestJobType(JobType):\\n"
                            "    def get_command(self):\\n"
                            "        return \"/usr/bin/touch\"\\n\\n"
                            "    def get_arguments(self):\\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\\n",
                    "id": 1,
                    "version": 1,
                    "max_batch": 1,
                    "name": "TestJobType",
                    "software_requirements": [
                        {
                            "max_version": null,
                            "max_version_id": null,
                            "min_version": "8.21",
                            "min_version_id": 1,
                            "software": "/bin/touch",
                            "software_id": 1
                        }
                    ]
                }

        :statuscode 200:
            no error

        :statuscode 404:
            jobtype or version not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by("version desc").first()

        if not jobtype or not jobtype_version:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        # For some reason, sqlalchemy sometimes returns this column as bytes
        # instead of string.  jsonify cannot decode that.
        if PY3 and isinstance(jobtype_version.code, bytes): # pragma: no cover
            jobtype_version.code = jobtype_version.code.decode()

        jobtype_data = jobtype_version.to_dict(
            unpack_relationships=["software_requirements"])
        jobtype_data.update(jobtype.to_dict(unpack_relationships=False))
        del jobtype_data["jobtype_id"]
        return jsonify(jobtype_data), OK

    def put(self, jobtype_name):
        """
        A ``PUT`` to this endpoint will create a new jobtype under the given URI.
        If a jobtype already exists under that URI, a new version will be created
        with the given data.

        You should only call this by id for updating an existing jobtype or if
        you have a reserved jobtype id. There is currently no way to reserve a
        jobtype id.

        .. http:put:: /api/v1/jobtypes/[<str:name>|<int:id>] HTTP/1.1

            **Request**

            .. sourcecode:: http

                PUT /api/v1/jobtypes/TestJobType HTTP/1.1
                Accept: application/json

                {
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "code": "\\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\\n\\nclass TestJobType(JobType):\\n"
                            "    def get_command(self):\\n"
                            "        return \"/usr/bin/touch\"\\n\\n"
                            "    def get_arguments(self):\\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\\n"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 201 CREATED
                Content-Type: application/json

                {
                    "batch_contiguous": true,
                    "classname": null,
                    "code": "\\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\\n\\nclass TestJobType(JobType):\\n"
                            "    def get_command(self):\\n"
                            "        return \"/usr/bin/touch\"\\n\\n"
                            "    def get_arguments(self):\\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\\n",
                    "id": 1,
                    "max_batch": 1,
                    "name": "TestJobType", 
                    "description": "Jobtype for testing inserts and queries",
                    "software_requirements": []
                }

        :statuscode 201:
            a new jobtype was created

        :statuscode 400:
            there was something wrong with the request (such as
            invalid columns being included)
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        max_version = None
        new = False if jobtype else True
        if jobtype:
            logger.debug(
                "jobtype %s will get a new version with data %r on commit",
                jobtype.name, g.json)
            max_version, = db.session.query(func.max(
                JobTypeVersion.version)).filter_by(jobtype=jobtype).first()
        else:
            jobtype = JobType()

        if max_version is not None:
            version = max_version + 1
        else:
            version = 1

        try:
            jobtype.name = g.json.pop("name")
            jobtype.description = g.json.pop("description", None)
            jobtype_version = JobTypeVersion()
            jobtype_version.jobtype = jobtype
            jobtype_version.version = version
            jobtype_version.code = g.json.pop("code")
            jobtype_version.classname = g.json.pop("classname", None)
            jobtype_version.batch_contiguous = g.json.pop("batch_contiguous",
                                                          None)
            if "max_batch" in g.json and g.json["max_batch"] is None:
                g.json.pop("max_batch")
                jobtype_version.max_batch = sql.null()
            else:
                jobtype_version.max_batch = g.json.pop("max_batch", None)
        except KeyError as e:
            return (jsonify(error="Missing key in input: %r" % e.args),
                    BAD_REQUEST)

        if "software_requirements" in g.json:
            try:
                for r in parse_requirements(g.json["software_requirements"]):
                    r.jobtype_version = jobtype_version
                    db.session.add(r)
            except (TypeError, ValueError) as e:
                return jsonify(error=e.args), BAD_REQUEST
            except ObjectNotFound as e:
                return jsonify(error=e.args), NOT_FOUND
            del g.json["software_requirements"]
        elif not new:
            # If the user did not specify a list of software requirements and
            # this jobtype is not new, retain the requirements from the previous
            # version
            previous_version = JobTypeVersion.query.filter(
                JobTypeVersion.jobtype == jobtype,
                JobTypeVersion.version != version).order_by(
                    "version desc").first()

            if previous_version:
                for old_req in previous_version.software_requirements:
                    new_req = JobTypeSoftwareRequirement()
                    new_req.jobtype_version = jobtype_version
                    new_req.software_id = old_req.software_id
                    new_req.min_version_id = old_req.min_version_id
                    new_req.max_version_id = old_req.max_version_id
                    db.session.add(new_req)

        if g.json:
            return (jsonify(error="Unexpected keys in input: %s" %
                            g.json.keys()), BAD_REQUEST)

        db.session.add_all([jobtype, jobtype_version])
        db.session.commit()
        jobtype_data = jobtype_version.to_dict(
            unpack_relationships=["software_requirements"])
        jobtype_data.update(jobtype.to_dict(unpack_relationships=False))
        del jobtype_data["jobtype_id"]
        logger.info("%s jobtype %s in put: %r",
            "created" if new else "updated", jobtype.name, jobtype_data)

        return jsonify(jobtype_data), CREATED

    def delete(self, jobtype_name):
        """
        A ``DELETE`` to this endpoint will delete the requested jobtype

        .. http:delete:: /api/v1/jobtypes/[<str:name>|<int:id>] HTTP/1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/jobtypes/TestJobType HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO CONTENT

        :statuscode 204:
            the jobtype was deleted or didn't exist
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter(JobType.id == jobtype_name).first()

        if jobtype:
            logger.debug("jobtype %s will be deleted",jobtype.name)
            db.session.delete(jobtype)
            db.session.commit()
            logger.info("jobtype %s has been deleted",jobtype.name)

        return jsonify(None), NO_CONTENT


class JobTypeVersionsIndexAPI(MethodView):
    def get(self, jobtype_name):
        """
        A ``GET`` to this endpoint will return a sorted list of of all known
        versions of the specified jobtype.

        .. http:get:: /api/v1/jobtypes/[<str:name>|<int:id>]/versions/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType/versions/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [1, 2]

        :statuscode 200:
            no error

        :statuscode 404:
            jobtype not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter(JobType.id == jobtype_name).first()

        if not jobtype:
            return jsonify(error="jobtype not found"), NOT_FOUND

        out = [x.version for x in jobtype.versions]

        return jsonify(sorted(out)), OK


class VersionedJobTypeAPI(MethodView):
    def get(self, jobtype_name, version):
        """
        A ``GET`` to this endpoint will return the specified version of the
        referenced jobtype, by name or id.

        .. http:get:: /api/v1/jobtypes/[<str:name>|<int:id>]/versions/<int:version> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType/versions/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "batch_contiguous": true,
                    "classname": null,
                    "name": "TestJobType",
                    "code": "\\nfrom pyfarm.jobtypes.core.jobtype import "
                            "JobType\\n\\nclass TestJobType(JobType):\\n"
                            "    def get_command(self):\\n"
                            "        return \"/usr/bin/touch\"\\n\\n"
                            "    def get_arguments(self):\\n"
                            "           return [os.path.join("
                            "self.assignment_data[\"job\"][\"data\"][\"path\"], "
                            "\"%04d\" % self.assignment_data[\"tasks\"]"
                            "[0][\"frame\"])]\\n",
                    "id": 1,
                    "version": 1,
                    "max_batch": 1,
                    "software_requirements": [
                        {
                            "max_version": null,
                            "max_version_id": null,
                            "min_version": "8.21",
                            "min_version_id": 1,
                            "software": "/bin/touch",
                            "software_id": 1
                        }
                    ]
                }

        :statuscode 200:
            no error

        :statuscode 404:
            jobtype or version not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter(JobType.id == jobtype_name).first()

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype, version=version).first()

        if not jobtype or not jobtype_version:
            return (jsonify(error="JobType %s version %s not found" %
                            (jobtype_name, version)), NOT_FOUND)

        # For some reason, sqlalchemy sometimes returns this column as bytes
        # instead of string.  jsonify cannot decode that.
        if PY3 and isinstance(jobtype_version.code, bytes): # pragma: no cover
            jobtype_version.code = jobtype_version.code.decode()

        jobtype_data = jobtype_version.to_dict(
            unpack_relationships=["software_requirements"])
        jobtype_data.update(jobtype.to_dict(unpack_relationships=False))
        del jobtype_data["jobtype_id"]
        return jsonify(jobtype_data), OK

    def delete(self, jobtype_name, version):
        """
        A ``DELETE`` to this endpoint will delete the requested version of the
        specified jobtype.

        .. http:delete:: /api/v1/jobtypes/[<str:name>|<int:id>]/versions/<int:version> HTTP/1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/jobtypes/TestJobType/versions/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO CONTENT

        :statuscode 204:
            the version was deleted or didn't exist
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter(JobType.name == jobtype_name).first()
        else:
            jobtype = JobType.query.filter(JobType.id == jobtype_name).first()

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype, version=version).first()

        if jobtype_version:
            logger.debug("version %s of jobtype %s will be deleted",
                         version, jobtype.name)
            db.session.delete(jobtype_version)
            db.session.commit()
            logger.info("version %s of jobtype %s has been deleted",
                        version, jobtype.name)

        return jsonify(None), NO_CONTENT


class JobTypeCodeAPI(MethodView):
    def get(self, jobtype_name, version):
        """
        A ``GET`` to this endpoint will return just the python code for this
        version of the specified jobtype.

        .. http:get:: /api/v1/jobtypes/[<str:name>|<int:id>]/versions/<int:version>/code HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType/versions/1/code HTTP/1.1
                Accept: text/x-python

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: text/x-python

                from pyfarm.jobtypes.core.jobtype import JobType

                class TestJobType(JobType):
                    def get_command(self):
                        return "/usr/bin/touch"

                    def get_arguments(self):
                        return [os.path.join(
                            self.assignment_data["job"]["data"]["path"], "%04d" %
                            self.assignment_data["tasks"][0]["frame"])]

        :statuscode 200:
            no error

        :statuscode 404:
            jobtype or version not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jt_tuple = db.session.query(
                JobType, JobTypeVersion).filter(
                    JobType.id == JobTypeVersion.jobtype_id,
                    JobType.name == jobtype_name,
                    JobTypeVersion.version == version).first()
        else:
            jt_tuple = db.session.query(
                JobType, JobTypeVersion).filter(
                    JobType.id == JobTypeVersion.jobtype_id,
                    JobType.id == jobtype_name,
                    JobTypeVersion.version == version).first()

        if not jt_tuple:
            return (jsonify(error="JobType %s, version %s not found" %
                            (jobtype_name, version)), NOT_FOUND)

        jobtype, jobtype_version = jt_tuple

        return Response(jobtype_version.code, OK, mimetype="text/x-python")


class JobTypeSoftwareRequirementsIndexAPI(MethodView):
    def get(self, jobtype_name, version=None):
        """
        A ``GET`` to this endpoint will return a list of all the software
        requirements of the specified jobtype

        .. http:get:: /api/v1/jobtypes/[<str:name>|<int:id>]/software_requirements/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType/software_requirements/ HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                [
                    {
                        "software": {
                            "software": "/bin/touch",
                            "id": 1
                        },
                        "max_version": null,
                        "min_version": {
                            "version": "8.21",
                            "id": 1
                        },
                        "jobtype_version": {
                            "version": 7,
                            "jobtype": "TestJobType"
                        }
                    }
                ]

        :statuscode 200:
            no error

        :statuscode 404:
            jobtype or version not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        if version:
            jobtype_version = JobTypeVersion.query.filter(
                JobTypeVersion.jobtype == jobtype,
                JobTypeVersion.version == version).first()
        else:
            jobtype_version = JobTypeVersion.query.filter_by(
                jobtype=jobtype).order_by("version desc").first()

        if not jobtype_version:
            return jsonify(error="JobType version not found"), NOT_FOUND

        out = []
        for requirement in jobtype_version.software_requirements:
            rq_data = requirement.to_dict()
            del rq_data["jobtype_version_id"]
            del rq_data["software_id"]
            del rq_data["min_version_id"]
            del rq_data["max_version_id"]
            out.append(rq_data)

        return jsonify(out), OK

    def post(self, jobtype_name, version=None):
        """
        A ``POST`` to this endpoint will create a new software_requirement for
        the specified jobtype.
        This will transparently create a new jobtype version

        .. http:post:: /api/v1/jobtypes/[<str:name>|<int:id>]/software_requirements/ HTTP/1.1

            **Request**

            .. sourcecode:: http

                POST /api/v1/jobtypes/TestJobType/software_requirements/ HTTP/1.1
                Accept: application/json

                {
                    "software": "blender",
                    "min_version": "2.69"
                }

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "jobtype_version": {
                        "id": 8,
                        "jobtype": "TestJobType",
                        "version": 7
                    },
                    "max_version": null,
                    "min_version": {
                        "id": 2,
                        "version": "1.69"
                    },
                    "software": {
                        "id": 2,
                        "software": "blender"
                    }
                }

        :statuscode 201:
            a new software requirement was created

        :statuscode 400:
            there was something wrong with the request (such as
            invalid columns being included)

        :statuscode 405:
            you tried calling this method on a specific version

        :statuscode 409:
            a conflicting software requirement already exists
        """
        if version is not None:
            return (jsonify(
                error="POST not allowed for specific jobtype versions"),
                METHOD_NOT_ALLOWED)

        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by("version desc").first()
        if not jobtype_version:
            return jsonify(error="JobType has no versions"), NOT_FOUND

        if ("software" not in g.json or
            not isinstance(g.json["software"], STRING_TYPES)):
            return (jsonify(error="Software not specified or not a string"),
                    BAD_REQUEST)

        software = Software.query.filter_by(software=g.json["software"]).first()
        if not software:
            return jsonify(error="Software not found"), NOT_FOUND

        existing_requirement = JobTypeSoftwareRequirement.query.filter(
            JobTypeSoftwareRequirement.jobtype_version == jobtype_version,
            JobTypeSoftwareRequirement.software == software).first()
        if existing_requirement:
            return jsonify(error="A software requirement for this jobtype "
                                 "version and this software exists"), CONFLICT

        new_version = JobTypeVersion()
        for name in JobTypeVersion.types().columns:
            if name not in JobTypeVersion.types().primary_keys:
                setattr(new_version, name, getattr(jobtype_version, name))
        new_version.version += 1
        db.session.add(new_version)
        for old_req in jobtype_version.software_requirements:
            new_req = JobTypeSoftwareRequirement()
            for name in JobTypeSoftwareRequirement.types().columns:
                setattr(new_req, name, getattr(old_req, name))
            new_req.jobtype_version = new_version
            db.session.add(new_req)

        min_version = None
        if "min_version" in g.json:
            if not isinstance(g.json["min_version"], STRING_TYPES):
                return jsonify(error="min_version not a string"), BAD_REQUEST
            min_version = SoftwareVersion.query.filter_by(
                version=g.json["min_version"]).first()
            if not min_version:
                return jsonify(error="min_version not found"), NOT_FOUND

        max_version = None
        if "max_version" in g.json:
            if not isinstance(g.json["max_version"], STRING_TYPES):
                return jsonify(error="max_version not a string"), BAD_REQUEST
            max_version = SoftwareVersion.query.filter_by(
                version=g.json["max_version"]).first()
            if not max_version:
                return jsonify(error="max_version not found"), NOT_FOUND

        requirement = JobTypeSoftwareRequirement()
        requirement.jobtype_version = new_version
        requirement.software = software
        requirement.min_version = min_version
        requirement.max_version = max_version

        db.session.add(requirement)
        db.session.commit()
        requirement_data = requirement.to_dict()
        del requirement_data["jobtype_version_id"]
        del requirement_data["software_id"]
        del requirement_data["min_version_id"]
        del requirement_data["max_version_id"]
        logger.info("Created new software requirement for jobtype %s: %r",
                    jobtype.id, requirement_data)

        return jsonify(requirement_data), CREATED


class JobTypeSoftwareRequirementAPI(MethodView):
    def get(self, jobtype_name, software):
        """
        A ``GET`` to this endpoint will return the specified software requirement
        from the newest version of the requested jobtype.

        .. http:get:: /api/v1/jobtypes/[<str:name>|<int:id>]/software_requirements/<int:id> HTTP/1.1

            **Request**

            .. sourcecode:: http

                GET /api/v1/jobtypes/TestJobType/software_requirements/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 200 OK
                Content-Type: application/json

                {
                    "software": {
                        "software": "/bin/touch",
                        "id": 1
                    },
                    "max_version": null,
                    "min_version": {
                        "version": "8.21",
                        "id": 1
                    },
                    "jobtype_version": {
                        "version": 7,
                        "jobtype": "TestJobType"
                    }
                }

        :statuscode 200:
            no error

        :statuscode 404:
            jobtype or software requirement not found
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        current_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by("version desc").first()
        if not current_version:
            return jsonify(error="JobType has no versions"), NOT_FOUND

        requirement = JobTypeSoftwareRequirement.query.filter(
            JobTypeSoftwareRequirement.jobtype_version == current_version,
            JobTypeSoftwareRequirement.software.has(
                Software.software == software)).first()

        if not requirement:
            return (jsonify(error="JobType software requirement %s for jobtype "
                            "%s not found" % (software, jobtype_name)),
                    NOT_FOUND)

        requirement_data = requirement.to_dict()
        del requirement_data["jobtype_version_id"]
        del requirement_data["software_id"]
        del requirement_data["min_version_id"]
        del requirement_data["max_version_id"]
        return jsonify(requirement_data), OK

    def delete(self, jobtype_name, software):
        """
        A ``DELETE`` to this endpoint will delete the requested software
        requirement from the specified jobtype, creating a new version of the
        jobtype in the process

        .. http:delete:: /api/v1/jobtypes/[<str:name>|<int:id>]/software_requirements/<int:id> HTTP/1.1

            **Request**

            .. sourcecode:: http

                DELETE /api/v1/jobtypes/TestJobType/software_requirements/1 HTTP/1.1
                Accept: application/json

            **Response**

            .. sourcecode:: http

                HTTP/1.1 204 NO CONTENT

        :statuscode 204:
            the software requirement was deleted or didn't exist
        """
        if isinstance(jobtype_name, STRING_TYPES):
            jobtype = JobType.query.filter_by(name=jobtype_name).first()
        else:
            jobtype = JobType.query.filter_by(id=jobtype_name).first()

        if not jobtype:
            return (jsonify(error="JobType %s not found" % jobtype_name),
                    NOT_FOUND)

        jobtype_version = JobTypeVersion.query.filter_by(
            jobtype=jobtype).order_by("version desc").first()
        if not jobtype_version:
            return jsonify(error="JobType has no versions"), NOT_FOUND

        new_version = JobTypeVersion()
        for name in JobTypeVersion.types().columns:
            if name not in JobTypeVersion.types().primary_keys:
                setattr(new_version, name, getattr(jobtype_version, name))
        new_version.version += 1
        for old_req in jobtype_version.software_requirements:
            if old_req.software.software != software:
                new_req = JobTypeSoftwareRequirement()
                for name in JobTypeSoftwareRequirement.types().columns:
                    setattr(new_req, name, getattr(old_req, name))
                new_req.jobtype_version = new_version
                db.session.add(new_req)

        db.session.add(new_version)
        db.session.commit()
        logger.info("Deleted software requirement %s for jobtype %s, creating "
                    "new version %s", software, jobtype.id, new_version.version)

        return jsonify(None), NO_CONTENT
