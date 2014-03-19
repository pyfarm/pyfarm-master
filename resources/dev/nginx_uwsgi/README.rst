Overview
========

This directory contains files for use by developers.  They are meant to
assist in setting up nginx and uwsgi so you can execute PyFarm's master web
application and api with minimal effort.

Setup
=====

These are just basic instructions to get started.  They are not comprehensive
and assume you already have uwsgi and nginx on your system.

#. Create you own copies of ``nginx.conf.template`` and ``uwsgi.ini.template``.
   For our purposes we'll be referring to these copies as ``nginx.conf`` and
   ``uwsgi.ini`` respectively.
#. Edit ``nginx.conf`` to point to the your own static files.  For example

   ::

       location /static/ {
           alias /home/foo/repos/pyfarm-master/pyfarm/master/static/;
       }

       location /admin/static/ {
           alias /home/foo/virtualenv/pyfarm-master/lib/python3.3/site-packages/Flask_Admin-1.0.7-py3.3.egg/flask_admin/static/;
       }
   Be sure that the permissions are setup correctly for these directories.  If
   they are not nginx won't be able to use them to serve static content.
#. Edit ``uwsgi.ini`` to your own virtualenv root so that it can source the
   virtual environment and run the web application.

   ::

       virtualenv = /home/foo/repos/pyfarm-master/
#. Make nginx aware of your configuration either by merging the contents of
   ``nginx.conf`` with an existing config or by linking it into
   ``sites-enabled```.  This will vary by platform so use your best judgement
   here.  After this step has been completed reload nginx's configuration.
#. Launch uwsgi using ``uwsgi <your .ini file>``.  This should startup the
   master's web application and REST endpoints.
#. Try accessing http://127.0.0.1/setup/, assuming everything went well you'll
   either be prompted to setup an admin user or be shown the existing admin.