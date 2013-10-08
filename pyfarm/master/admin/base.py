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
Admin Index
===========

Setup the administrative index.
"""


from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from flask import redirect, abort
from flask.ext.admin.contrib.sqla import tools
from flask.ext.login import current_user, current_app
from flask.ext.admin.contrib import sqla
from flask.ext.admin import AdminIndexView


def current_user_authorized(required=None, allowed=None, redirect=True):
    """
    Simple function which take into account roles, enabled/disabled login system
    and various other bits of information.  In the event a user does not
    have access when this function is call a 401 will e raised using
    :func:`abort`
    """
    if current_app.login_manager._login_disabled:
        return True

    if not current_user.is_authenticated():
        return False

    if not (current_user.has_roles(allowed=allowed, required=required)
              and redirect):
            abort(401)

    return False


class AuthMixins(object):
    access_roles = set()

    def _has_access(self, default):
        if current_app.login_manager._login_disabled:
            return True
        elif current_user.is_authenticated():
            return current_user.has_roles(allowed=self.access_roles)
        else:
            return default

    def is_visible(self):
        return self._has_access(False)

    def is_accessible(self):
        return self._has_access(True)

    def render(self, template, **kwargs):
        if not current_app.login_manager._login_disabled:
            if not current_user.is_authenticated():
                return redirect("/login/?next=%s" % self.url)

            if not current_user.has_roles(allowed=self.access_roles):
                abort(401)

        return super(AuthMixins, self).render(template, **kwargs)


class AdminIndex(AuthMixins, AdminIndexView):
    access_roles = (
        "admin", "admin.db", "admin.db.user", "admin.db.agent"
        "admin.db.work.job", "admin.db.work.task")


class BaseModelView(AuthMixins, sqla.ModelView):
    edit_form_class = None
    create_form_class = None

    def __init__(self, name=None, category=None, endpoint=None, url=None):

        try:
            self.access_roles
        except AttributeError:
            raise NotImplementedError("you must override `access_roles`")

        try:
            self._session
        except AttributeError:
            raise NotImplementedError("you must provide a `_session` attribute")

        super(BaseModelView, self).__init__(
            self.model, self._session, name=name,
            category=(category or "Database"),
            endpoint="db/%s" % (endpoint or self.model.__name__),
            url=url)

    def get_create_form(self):
        if self.create_form_class is not None:
            return self.create_form_class
        else:
            return self.get_form()

    def get_edit_form(self):
        if self.edit_form_class is not None:
            return self.edit_form_class
        else:
            return self.get_form()

    def get_list(self, page, sort_column, sort_desc, search, filters,
                 execute=True):
        """
        Override of :meth:`sqla.ModelView.get_list` which uses count() instead
        of scalar() to determine the number of results.  This generally
        prevents the majority of problems scalar() creates with using
        a relationship column in a query.
        """

        # Will contain names of joined tables to avoid duplicate joins
        joins = set()

        query = self.get_query()
        count_query = self.get_count_query()

        # Apply search criteria
        if self._search_supported and search:
            # Apply search-related joins
            if self._search_joins:
                for jn in self._search_joins.values():
                    query = query.join(jn)
                    count_query = count_query.join(jn)

                joins = set(self._search_joins.keys())

            # Apply terms
            terms = search.split(' ')

            for term in terms:
                if not term:
                    continue

                stmt = tools.parse_like_term(term)
                filter_stmt = [c.ilike(stmt) for c in self._search_fields]
                query = query.filter(or_(*filter_stmt))
                count_query = count_query.filter(or_(*filter_stmt))

        # Apply filters
        if filters and self._filters:
            for idx, value in filters:
                flt = self._filters[idx]

                # Figure out joins
                tbl = flt.column.table.name

                join_tables = self._filter_joins.get(tbl, [])

                for table in join_tables:
                    if table.name not in joins:
                        query = query.join(table)
                        count_query = count_query.join(table)
                        joins.add(table.name)

                # Apply filter
                query = flt.apply(query, value)
                count_query = flt.apply(count_query, value)

        # Calculate number of rows
        count = count_query.count()

        # Auto join
        for j in self._auto_joins:
            query = query.options(joinedload(j))

        # Sorting
        if sort_column is not None:
            if sort_column in self._sortable_columns:
                sort_field = self._sortable_columns[sort_column]

                query, joins = self._order_by(query, joins, sort_field, sort_desc)
        else:
            order = self._get_default_order()

            if order:
                query, joins = self._order_by(query, joins, order[0], order[1])

        # Pagination
        if page is not None:
            query = query.offset(page * self.page_size)

        query = query.limit(self.page_size)

        # Execute if needed
        if execute:
            query = query.all()

        return count, query

