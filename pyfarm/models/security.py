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
Models dedicated to providing security, login information, roles,
and other related information.
"""

from flask.ext.security import UserMixin, RoleMixin
from pyfarm.models.core.app import db
from pyfarm.models.core.types import IPv4Address
from pyfarm.models.core.cfg import (
    TABLE_SECURITY_USER, TABLE_SECURITY_USER_ROLES, TABLE_SECURITY_ROLE)

UserRoles = db.Table(
    TABLE_SECURITY_USER_ROLES,
    db.Column("user_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_SECURITY_USER)),
    db.Column("role_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_SECURITY_ROLE)))


class Role(db.Model, RoleMixin):
    __tablename__ = TABLE_SECURITY_ROLE
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)


class User(db.Model, UserMixin):
    __tablename__ = TABLE_SECURITY_USER
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    confirmed_at = db.Column(db.DateTime)

    # tracking
    current_login_at = db.Column(db.String(255))
    current_login_ip = db.Column(IPv4Address)
    last_login_at = db.Column(db.String(255))
    last_login_ip = db.Column(IPv4Address)
    login_count = db.Column(db.Integer, default=0)

    roles = db.relationship(
        'Role', secondary=UserRoles,
        backref=db.backref('users', lazy='dynamic'))
