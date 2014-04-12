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

import uuid
from json import dumps

from flask.ext.admin import BaseView, expose

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.entrypoints import load_authentication, load_index
from pyfarm.master.admin.baseview import AuthMixins
from pyfarm.master.login import load_token, load_user
from pyfarm.master.application import (
    db, get_login_manager, get_admin)
from pyfarm.models.user import User, Role


class AdminRequiredView(AuthMixins, BaseView):
    access_roles = set(["admin"])

    @expose("/")
    def index(self):
        return self.render("pyfarm/tests/admin_required.html")


class TestLogin(BaseTestCase):
    def setup_app(self):
        super(TestLogin, self).setup_app()
        admin = get_admin(app=self.app)
        admin.add_view(
            AdminRequiredView(
                name="AdminRequired", endpoint="admin_required_test/"))

        # setup the login manager and the callbacks
        # necessary to load hte user
        login_manger = get_login_manager(
            app=self.app, login_view="/login/")
        login_manger.token_callback = load_token
        login_manger.user_callback = load_user
        load_authentication(self.app)

        # add an index url because the login page
        # will redirect there if there's not a 'next'
        load_index(self.app)

    def setUp(self):
        super(TestLogin, self).setUp()

        # create a normal user
        self.normal_username = uuid.uuid4().hex
        self.normal_password = uuid.uuid4().hex
        self.normal_user = User.create(
            self.normal_username, self.normal_password)

        # create an admin
        self.admin_username = uuid.uuid4().hex
        self.admin_password = uuid.uuid4().hex
        self.admin_user = User.create(
            self.admin_username, self.admin_password)
        self.admin_user.roles.append(Role.create("admin"))

        # commit the changes to the database
        db.session.commit()

    def test_login_bad_content_type(self):
        response = self.client.get(
            "/login/", method="GET",
            headers=[("Content-Type", "application/json")])
        self.assert_bad_request(response)

    def test_get_login(self):
        response = self.client.get("/login/")
        self.assert_ok(response)
        self.assertIn(
            '<input id="password" name="password" type="password" value="">',
            response.data.decode("utf-8"))
        self.assertIn(
            '<input id="username" name="username" type="text" value="">',
            response.data.decode("utf-8"))

    def test_post_login(self):
        # ensure admin page redirects to the login page
        response = self.client.get(
            "/admin/admin_required_test/", follow_redirects=True)
        self.assert_ok(response)
        self.assertIn("<title>PyFarm - Login</title>",
                      response.data.decode("utf-8"))
        
        # login as a normal user
        response = self.client.post(
            "/login/", data={
                "username": self.normal_username,
                "password": self.normal_password},
            follow_redirects=True)
        self.assert_ok(response)
        self.assertIn("Set-Cookie", response.headers)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])

        # attempt to access protected page
        response = self.client.get(
            "/admin/admin_required_test/", follow_redirects=True)
        self.assert_forbidden(response)
        
        # login as admin
        response = self.client.post(
            "/login/", data={
                "username": self.admin_username,
                "password": self.admin_password},
            follow_redirects=True)
        self.assert_ok(response)
        self.assertIn("Set-Cookie", response.headers)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])

        # since we've posted as admin, this should work now
        response = self.client.get(
            "/admin/admin_required_test/", follow_redirects=True)
        self.assert_ok(response)
        self.assertIn("Hello world!", response.data.decode("utf-8"))

    def test_post_login_json(self):
        response = self.client.post(
            "/login/",
            headers=[("Content-Type", "application/json")],
            follow_redirects=True,
            data=dumps({
                "username": self.normal_username,
                "password": self.normal_password}))
        self.assert_ok(response)
        self.assertIn("Set-Cookie", response.headers)
        self.assertEqual(response.content_type, "application/json")

    def test_logout(self):
        response = self.client.get("/logout/")
        self.assert_ok(response)
        self.assertIn(
            "<title>PyFarm - Already Logged Out</title>",
            response.data.decode("utf-8"))
        self.test_post_login()
        response = self.client.get("/logout/")
        self.assert_ok(response)
        self.assertIn(
            "<title>PyFarm - Logged Out</title>", response.data.decode("utf-8"))
