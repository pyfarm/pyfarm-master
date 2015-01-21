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
assert sys.version_info[0:2] >= (2, 7), "Python 2.7 or higher is required"

import os
from os import walk
from os.path import isfile, join
from setuptools import setup

# Version requirements explanations:
#   pyfarm.core: certain enums which are only present in later versions,
#   configuration loader changes
#   sqlalchemy: Bugfix for pymysql in Python 3
#   flask-admin: New form helps that support async JavaScript requests
install_requires = [
    "pyfarm.core>=0.9.1",
    "sqlalchemy>=0.9.3",
    "flask",
    "flask-login",
    "flask-sqlalchemy",
    "itsdangerous",
    "blinker",
    "voluptuous",
    "celery",
    "redis",
    "requests!=2.4.0",
    "netaddr",
    "lockfile",
    "wtforms"]

if "READTHEDOCS" in os.environ:
    install_requires += ["sphinxcontrib-httpdomain", "sphinx"]

if isfile("README.rst"):
    with open("README.rst", "r") as readme:
        long_description = readme.read()
else:
    long_description = ""


def get_package_data():
    master_root = join("pyfarm", "master")
    packge_data_roots = (
        join("pyfarm", "master", "etc"),
        join("pyfarm", "master", "static"),
        join("pyfarm", "master", "templates"),
        join("pyfarm", "master", "api", "templates"),
        join("pyfarm", "master", "api", "static"))

    output = []
    for top in packge_data_roots:
        for root, dirs, files in walk(top):
            for filename in files:
                output.append(join(root, filename).split(master_root)[-1][1:])

    return output

setup(
    name="pyfarm.master",
    version="0.8.1",
    packages=[
        "pyfarm",
        "pyfarm.master",
        "pyfarm.master.api",
        "pyfarm.master.user_interface",
        "pyfarm.models",
        "pyfarm.models.core",
        "pyfarm.scheduler"],
    namespace_packages=["pyfarm"],
    include_package_data=True,
    package_data={"pyfarm.master": get_package_data()},
    data_files=[
        ("etc/pyfarm", [
            "pyfarm/master/etc/master.yml"
        ])
    ],
    entry_points={
        "console_scripts": [
            "pyfarm-master = pyfarm.master.entrypoints:run_master",
            "pyfarm-tables = pyfarm.master.entrypoints:tables"]},
    install_requires=install_requires,
    url="https://github.com/pyfarm/pyfarm-master",
    license="Apache v2.0",
    author="Oliver Palmer",
    author_email="development@pyfarm.net",
    description="Sub-library which contains the code necessary to "
                "communicate with the database via a REST api.",
    long_description=long_description,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: System :: Distributed Computing"])
