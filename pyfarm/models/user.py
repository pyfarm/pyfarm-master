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
Permissions
===========

Stores users and their roles in the database.
"""

from hashlib import sha256
from datetime import datetime
from textwrap import dedent

from flask.ext.login import UserMixin

from pyfarm.core.enums import STRING_TYPES, PY3
from pyfarm.master.application import app, db, login_serializer
from pyfarm.models.core.mixins import ReprMixin
from pyfarm.models.core.functions import split_and_extend
from pyfarm.models.core.cfg import (
    TABLE_USER, TABLE_ROLE, TABLE_USER_ROLE,
    MAX_USERNAME_LENGTH, SHA256_ASCII_LENGTH, MAX_EMAILADDR_LENGTH,
    MAX_ROLE_LENGTH)

__all__ = ("User", )

# roles the user is a member of
UserRole = db.Table(
    TABLE_USER_ROLE,
    db.Column("user_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_USER)),
    db.Column("role_id", db.Integer,
              db.ForeignKey("%s.id" % TABLE_ROLE)))


class User(db.Model, UserMixin, ReprMixin):
    """
    Stores information about a user including the roles they belong to
    """
    __tablename__ = TABLE_USER
    REPR_COLUMNS = ("id", "username")

    id = db.Column(db.Integer, primary_key=True, nullable=False)

    active = db.Column(db.Boolean, default=True,
                       doc=dedent("""
                       Enables or disables a particular user across the
                       entire system"""))

    username = db.Column(
        db.String(MAX_USERNAME_LENGTH), unique=True, nullable=False,
        doc="The username used to login.")

    password = db.Column(db.String(SHA256_ASCII_LENGTH),
                         doc="The password used to login")

    email = db.Column(db.String(MAX_EMAILADDR_LENGTH), unique=True,
                      doc=dedent("""
                      Contact email for registration and possible
                      notifications"""))

    expiration = db.Column(db.DateTime,
                           doc=dedent("""
                           User expiration.  If this value is set then the user
                           will no longer be able to access PyFarm past the
                           expiration."""))

    onetime_code = db.Column(db.String(SHA256_ASCII_LENGTH),
                             doc=dedent("""
                             SHA256 one time use code which can be used for
                             unique urls such as for password resets."""))

    last_login = db.Column(db.DateTime,
                           doc=dedent("""
                           The last date that this user was logged in."""))

    roles = db.relationship("Role", secondary=UserRole,
                            backref=db.backref("users", lazy="dynamic"))

    @classmethod
    def create(cls, username, password, email=None, roles=None):
        # create the list or roles to add
        if roles is None:
            roles = []

        elif isinstance(roles, STRING_TYPES):
            roles = [roles]

        # create the user with the proper initial values
        user = cls(
            username=username,
            password=cls.hash_password(password),
            email=email)
        user.roles.extend(map(Role.create, roles))

        # commit and return
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def get(cls, id_or_username):
        """Get a user model either by id or by the user's username"""
        try:
            id_or_username = int(id_or_username)
        except ValueError:
            pass

        if isinstance(id_or_username, int):
            return cls.query.filter_by(id=id_or_username).first()
        elif isinstance(id_or_username, STRING_TYPES):
            return cls.query.filter_by(username=id_or_username).first()
        else:
            raise TypeError("string or integer required for User.get()")

    @classmethod
    def hash_password(cls, value):
        value = app.secret_key + value

        if PY3:
            value = value.encode("utf-8")

        return sha256(value).hexdigest()

    def get_auth_token(self):
        return login_serializer.dumps([str(self.id), self.password])

    def get_id(self):
        return self.id

    def check_password(self, password):
        """checks the password provided against the stored password"""
        assert isinstance(password, STRING_TYPES)
        return self.hash_password(password) == self.password

    def is_active(self):
        """returns true if the user and the roles it belongs to are active"""
        now = datetime.utcnow()

        # user is not active
        if not self.active:
            return False

        # user has expired
        if self.expiration is not None and now > self.expiration:
            return False

        # TODO: there's probably some way to cache this information
        return all(role.is_active() for role in self.roles)

    def has_roles(self, allowed=None, required=None):
        """checks the provided arguments against the roles assigned"""
        if not allowed and not required:
            return True

        allowed = split_and_extend(allowed)
        required = split_and_extend(required)

        if allowed:
            # Ask the database if the user has any of the allowed roles.  For
            # smaller numbers of roles this is very slightly slower with
            # SQLite in :memory: but is a good amount faster over the network
            # or with large role sets.
            return bool(
                User.query.filter(
                    User.roles.any(
                        Role.name.in_(allowed))
                ).filter(User.id == self.id).count())

        if required:
            # Ask the database for all roles matching ``required``.  In order
            # for this to return True is the number of entries found must
            # be equal to len(required).
            count = Role.query.filter(
                Role.name.in_(required)).filter(User.id == self.id).count()
            return count == len(required)


class Role(db.Model):
    """
    Stores role information that can be used to give a user access
    to individual resources.
    """
    __tablename__ = TABLE_ROLE

    id = db.Column(db.Integer, primary_key=True, nullable=False)

    active = db.Column(db.Boolean, default=True,
                       doc=dedent("""
                       Enables or disables a role.  Disabling a role
                       will prevent any users of this role from accessing
                       PyFarm"""))

    name = db.Column(db.String(MAX_ROLE_LENGTH), unique=True, nullable=False,
                     doc="The name of the role")

    expiration = db.Column(db.DateTime,
                       doc=dedent("""
                       Role expiration.  If this value is set then the role, and
                       anyone assigned to it, will no longer be able to access
                       PyFarm past the expiration."""))

    description = db.Column(db.Text, doc="Human description of the role.")

    @classmethod
    def create(cls, name, description=None):
        """
        Creates a role by the given name or returns an existing
        role if it already exists.
        """
        if isinstance(name, Role):
            return name

        role = Role.query.filter_by(name=name).first()

        if role is None:
            role = cls(name=name, description=description)
            db.session.add(role)
            db.session.commit()

        return role

    def is_active(self):
        if self.expiration is None:
            return self.active
        return self.active and datetime.utcnow() < self.expiration
