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

from __future__ import with_statement

import sys
assert sys.version_info[0:2] >= (2, 6), "Python 2.6 or higher is required"

from os import walk
from os.path import isfile, join
from setuptools import setup

install_requires = [
    "pyfarm.core", "pyfarm.models",
    "flask-restful", "flask-login", "flask-admin", "flask-sqlalchemy",
    "itsdangerous"]

if sys.version_info[0:2] < (2, 7):
    install_requires.append("simplejson")

if isfile("README.rst"):
    with open("README.rst", "r") as readme:
        long_description = readme.read()
else:
    long_description = ""

def get_package_data():
    parent = join("pyfarm", "master")

    output = []
    for top in (join(parent, "static"), join(parent, "templates")):
        for root, dirs, files in walk(top):
            for filename in files:
                output.append(join(root, filename).split(parent)[-1][1:])

    return output

setup(
    name="pyfarm.master",
    version="0.7.0-dev2",
    packages=[
        "pyfarm", "pyfarm.master", "pyfarm.master.admin"],
    include_package_data=True,
    package_data={"pyfarm.master": get_package_data()},
    install_requires=install_requires,
    url="https://github.com/pyfarm/pyfarm-master",
    license="Apache v2.0",
    author="Oliver Palmer",
    author_email="development@pyfarm.net",
    description="Sub-library which contains the code necessary to "
                "communicate with the database via a REST api.",
    long_description=long_description,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2 :: Only",  # (for now)
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Distributed Computing"])