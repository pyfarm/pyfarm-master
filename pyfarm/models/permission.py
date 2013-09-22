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
from datetime import datetime, timedelta
from textwrap import dedent
from flask.ext.login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from pyfarm.models.core.db import db
from pyfarm.core.app.loader import package
from pyfarm.models.core.cfg import (
    TABLE_PERMISSION_USER, TABLE_PERMISSION_ROLE, TABLE_PERMISSION_USER_ROLES,
    MAX_USERNAME_LENGTH, SHA256_ASCII_LENGTH, MAX_EMAILADDR_LENGTH,
    MAX_ROLE_LENGTH)


UserRoles = db.Table(
    TABLE_PERMISSION_USER_ROLES,
    db.Column("user_id", db.Integer(),
              db.ForeignKey("%s.id" % TABLE_PERMISSION_USER)),
    db.Column("role_id", db.Integer(),
              db.ForeignKey("%s.id" % TABLE_PERMISSION_ROLE)))

app = package.application()

# login serializer used to encrypt and decrypt the token for the remember
# me option of flask-login
login_serializer = URLSafeTimedSerializer(app.secret_key)


class IsActiveMixin(object):
    """simple mixin to override :meth:`is_active`"""
    def is_active(self):
        now = datetime.now()

        if isinstance(self, Role):
            return self.active and now < self.expiration

        if isinstance(self, User):
            # nothing else to do if the user itself has expired
            if not self.active or now > self.expiration:
                return False

            # TODO: verify this works as expected in sessions
            # We either have not asked the roles if they're active or its
            # been a while since we've asked.
            if (self.last_active_check is None
                or (now - self.last_active_check) > self.ACTIVE_CHECK_INTERVAL):
                self.roles_active = all(role.is_active() for role in self.roles)
                self.last_active_check = datetime.now()

            return self.roles_active


class User(db.Model, IsActiveMixin, UserMixin):
    """
    Stores information about a user including the roles they belong to
    """
    __tablename__ = TABLE_PERMISSION_USER
    ACTIVE_CHECK_INTERVAL = timedelta(seconds=120)

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

    roles = db.relationship("Role", secondary=UserRoles,
                            backref=db.backref("users", lazy="dynamic"))

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self.last_active_check = None
        self.roles_active = False

    @classmethod
    def create(cls, username, password, email=None, roles=None):
        # create the list or roles to add
        if roles is None:
            roles = []
        elif isinstance(roles, basestring):
            roles = [roles]

        # ensure the user will be added to "everyone"
        if "everyone" not in roles:
            roles.append("everyone")

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
        elif isinstance(id_or_username, basestring):
            return cls.query.filter_by(username=id_or_username).first()
        else:
            raise TypeError("string or integer required for User.get()")

    def check_password(self, password):
        """checks the password provided against the stored password"""
        return self.hash_password(str(password)) == self.password

    @classmethod
    def hash_password(cls, value):
        return sha256(app.secret_key + value).hexdigest()

    def get_auth_token(self):
        return login_serializer.dumps([str(self.id), self.password])

    def get_id(self):
        return unicode(self.username)


class Role(db.Model, IsActiveMixin):
    """
    Stores role information that can be used to give a user access
    to individual resources.
    """
    __tablename__ = TABLE_PERMISSION_ROLE

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
        role = Role.query.filter_by(name=name).first()

        if role is None:
            role = cls(name=name, description=description)
            db.session.add(role)

        return role
