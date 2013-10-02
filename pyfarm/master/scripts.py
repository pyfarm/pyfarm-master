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
Scripts
=======

Contains entry points for command line tools.
"""


def user_management(args=None):
    from getpass import getpass
    from textwrap import dedent
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    from pyfarm.models.users import User, Role
    from pyfarm.master.application import db

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(
        help="avaliable subcommands", dest="subcommand")

    def admin_user(value):
        user = User.get(value)

        if user is None:
            parser.error("no such user '%s'" % value)

        return user

    # add standard arguments
    parser.add_argument(
        "--admin-user", type=admin_user,
        help="the administrative user, required for some operations")
    parser.add_argument(
        "--db-uri",
        help="if provided, use this uri instead of the application default")

    # add subparser: user creation
    create = subparsers.add_parser(
        "create", help="create a new user")
    create.add_argument(
        "user", help="name of new user to be created")
    create.add_argument(
        "role", nargs="*", help="role(s) to add the user to")
    create.add_argument(
        "--email", help="optional email to set for the user")

    # add subparser: update user
    update = subparsers.add_parser(
        "update", help="update an existing user's membership(s)",
        formatter_class=RawDescriptionHelpFormatter,
        description=dedent("""
        This subcommand is used to update an existing user.  See below for
        a few usage examples:

        Add 'test_user' to roles 'foo' and 'bar'
            -> pyfarm-user update test_user --add-role=foo --add-role=bar

        Remove 'test_user' from role 'foo'
            -> pyfarm-user update test_user --remove-role=foo

        **NOTE** - some updates may require admin access"""))
    update.add_argument(
        "user", help="name of existing user to update")
    update.add_argument(
        "--add-role", help="name of role to add the user to",
        metavar="role", action="append")
    update.add_argument(
        "--remove-role", help="name of role to remove the user from",
        metavar="role", action="append")

    # add subparser: change password
    change_passsword = subparsers.add_parser(
        "change-password", help="change the password for an existing user")
    change_passsword.add_argument(
        "user", help="the user to change the password for")

    parsed = parser.parse_args(args)

    def is_administrator(required=False):
        if required and not parsed.admin_user:
            parser.error("--admin-user argument required")

        if not parsed.admin_user:
            return False

        elif User.hash_password(getpass("administrator password: ")) != \
                parsed.admin_user.password:
            parser.error("invalid password")

        else:
            return True

    # TODO: use REST api, if we can connect
    if parsed.subcommand == "create" and is_administrator(required=True):
        user = User.get(parsed.user)

        if user is not None:
            parser.error("user '%s' already exists" % parsed.user)

        user = User.create(parsed.user, getpass("new user password: "))
        for role in parsed.role:
            if not Role.query.filter_by(name=role).first():
                user.roles.append(Role.create(role))
                print "creating role: %s" % role

        print "created user: %s" % user.username

        db.session.add(user)
        db.session.commit()

    # TODO: use REST api, if we can connect
    elif parsed.subcommand == "update":
        pass

    # TODO: use REST api, if we can connect
    elif parsed.subcommand == "change-password":
        user = User.get(parsed.user)

        if user is None:
            parser.error("user '%s' does not exist" % parsed.user)

        if not is_administrator():
            current_password = getpass("current password: ")
            if User.hash_password(current_password) != user.password:
                parser.error("invalid password for '%s'" % parsed.user)

        new_password = getpass("new password: ")
        retry_password = getpass("reenter password: ")
        if new_password != retry_password:
            parser.error("new passwords do not match")

        hashed_password = User.hash_password(new_password)
        if hashed_password != user.password:
            user.password = hashed_password
            db.session.add(user)
            db.session.commit()


def run_master():
    from flask.ext.admin.base import MenuLink
    from pyfarm.master.admin.user import UserView
    from pyfarm.master.application import app, admin, db
    from pyfarm.master.login import login_page, logout_page
    from pyfarm.master.initial import setup_page

    # tables to setup
    from pyfarm.models.users import User, Role

    # routes
    app.add_url_rule(
        "/login/", "login_page", login_page, methods=("GET", "POST"))
    app.add_url_rule(
        "/logout/", "logout_page", logout_page)
    app.add_url_rule(
        "/setup/", "setup_page", setup_page, methods=("GET", "POST"))

    # setup the admin interface
    admin.add_link(MenuLink("Preferences", "/preferences"))
    admin.add_link(MenuLink("Log Out", "/logout"))
    admin.add_view(UserView())

    app.run()


if __name__ == "__main__":
    run_master()
