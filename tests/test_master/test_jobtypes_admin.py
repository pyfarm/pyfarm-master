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

import os
from binascii import hexlify
from collections import namedtuple
from textwrap import dedent

from wtforms import ValidationError

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.models.jobtype import JobType
from pyfarm.master.admin.jobtypes import (
    LimitedLength, unique_name, check_python_source)
from pyfarm.master.application import db


def dummy_object(**kwargs):
    return namedtuple("DummyObject", list(kwargs.keys()))(**kwargs)


class TestValidators(BaseTestCase):
    def test_fixed_length(self):
        field = dummy_object(data="12345", name="foo")
        validator = LimitedLength(5)
        validator(None, field)

        field = dummy_object(data="123456", name="foo")
        with self.assertRaises(ValidationError):
            validator(None, field)

    def test_unique_name(self):
        unused_name = hexlify(os.urandom(8)).decode("utf-8")
        name = hexlify(os.urandom(8)).decode("utf-8")
        jobtype = JobType(name=name)
        db.session.add(jobtype)
        db.session.commit()
        db.session.remove()
        unique_name(None, dummy_object(data=unused_name))

        with self.assertRaises(ValidationError):
            unique_name(None, dummy_object(data=name))

    def test_check_python_source(self):
        sourcecode = dedent("""
        class Foobar(object):
            pass
        """.strip())
        field = dummy_object(data=sourcecode)
        form = dummy_object(classname=dummy_object(data="Foobar"))
        check_python_source(form, field)

    def test_check_python_source_syntax_error(self):
        sourcecode = dedent("""
        class
        """.strip())
        field = dummy_object(data=sourcecode)
        form = dummy_object(classname=dummy_object(data="Foobar"))
        with self.assertRaises(ValidationError):
            check_python_source(form, field)

    def test_check_python_source_missing_class(self):
        sourcecode = dedent("""
        class Foo(object):
            pass
        """.strip())
        field = dummy_object(data=sourcecode)
        form = dummy_object(classname=dummy_object(data="Foobar"))
        with self.assertRaises(ValidationError):
            check_python_source(form, field)
