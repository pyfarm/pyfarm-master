# No shebang line, this module is meant to be imported
#
# Copyright 2014 Oliver Palmer
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
Job Types
=========

Objects and classes for working with the job type models.
"""

import ast
import logging

from flask import flash
from flask.ext.admin.babel import gettext
from wtforms import Form, StringField, TextAreaField, IntegerField, BooleanField
from wtforms.validators import ValidationError, DataRequired, required

from pyfarm.master.admin.baseview import SQLModelView
from pyfarm.master.application import SessionMixin
from pyfarm.models.jobtype import JobType, JobTypeVersion
from pyfarm.models.core.cfg import MAX_JOBTYPE_LENGTH


admin_log = logging.getLogger("flask-admin.sqla")


class LimitedLength(DataRequired):
    """Validates that a given field is the proper length"""
    def __init__(self, length):
        super(LimitedLength, self).__init__()
        self.length = length

    def __call__(self, _, field):
        if len(field.data) > self.length:
            raise ValidationError(
                "Max length for %s is %s" % (repr(field.name), self.length))


def unique_name(_, field):
    """Validates that a unique job type name is being created"""
    model = JobType.query.filter_by(name=field.data).first()
    if model is not None:
        raise ValidationError("%r is not a unique name" % field.data)


def check_python_source(form, field):
    """
    Validate that the provided source code is valid Python code
    and that it contains the expected class name.  This won't
    catch everything but it will catch the most obvious
    issues.

    .. note::
        Although this function is parsing the code we're
        using the abstract syntax tree to do so.  Internally
        the :mod:`.ast` module executes the :func:`compile`
        function so we're not directly evaluating the code.
    """
    try:
        parsed = ast.parse(field.data)
    except SyntaxError as e:
        raise ValidationError(
            "There was a problem parsing the provided source code: %s" % e)

    classname = form.classname.data.strip() or form.name.strip()
    for node in ast.walk(parsed):
        if isinstance(node, ast.ClassDef):
            if node.name == classname:
                break
    else:
        raise ValidationError(
            "Source code provided does not "
            "contain the %r class" % form.classname.data)


class CreateJobTypeForm(Form):
    """The form used to create new job types"""
    name = StringField(
        validators=[
            required(), unique_name, LimitedLength(MAX_JOBTYPE_LENGTH)],
        description=JobType.name.__doc__)
    classname = StringField(
        label="Class Name",
        validators=[LimitedLength(MAX_JOBTYPE_LENGTH)],
        description=JobTypeVersion.classname.__doc__)
    code = TextAreaField(
        label="Source Code",
        validators=[required(), check_python_source],
        description=JobTypeVersion.code.__doc__)
    description = TextAreaField(
        description=JobType.description.__doc__)
    max_batch = IntegerField(
        default=JobTypeVersion.max_batch.default.arg,
        description=JobTypeVersion.max_batch.__doc__)
    batch_contiguous = BooleanField(
        default=JobTypeVersion.batch_contiguous.default.arg,
        description=JobTypeVersion.batch_contiguous.__doc__)


class RolesMixin(object):
    access_roles = ("admin.db.jobtype", )


class IgnoredList(list):
    """
    A subclass of :class:`list` in which all updates are ignored.  This
    is necessary because :mod:`wtforms` will always include the
    required validator based on the model's required validator.
    """
    def append(self, p_object):
        pass

    def extend(self, iterable):
        pass


# TODO: align the editor fields in this view with those in JobTypeView
class JobTypeVersionView(SessionMixin, RolesMixin, SQLModelView):
    """SQL model editor for job type versions"""
    model = JobTypeVersion
    form_args = {
        "software_requirements": {"validators": IgnoredList()},
        "jobs": {"validators": IgnoredList()}}


class JobTypeView(SessionMixin, RolesMixin, SQLModelView):
    """
    SQL model view for an individual job type with a custom form for
    initial creation.
    """
    model = JobType
    create_form_class = CreateJobTypeForm

    def create_model(self, form):
        try:
            jobtype = JobType(
                name=form.name.data,
                description=form.description.data)
            self._session.add(jobtype)
            version = JobTypeVersion(
                jobtype=jobtype,
                version=1,
                code=form.code.data,
                max_batch=form.max_batch.data,
                batch_contiguous=form.batch_contiguous.data,
                classname=form.classname.data)
            self._session.add(version)
            self._session.commit()

        except Exception as e:
            if self._debug:
                raise

            flash(gettext(
                "Failed to create model. %(error)s", error=str(e)), "error")
            admin_log.exception("Failed to create model")
            self._session.rollback()
            return False

        else:
            self.after_model_change(form, jobtype, True)

        return True
