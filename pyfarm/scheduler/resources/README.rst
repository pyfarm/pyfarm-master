PyFarm Scheduler
================

To allow pyfarm to run its scheduler, you need a celery worker and a redis
instance as a message queue

Install redis using your distribution's package manager and run it with a default
configuration:

/etc/init.d/redis start

Depending on distribution, you might need to use systemctl or some other command
instead.

Install celery with redis support:

pip install celery[redis]

Run a celery worker for the pyfarm application:

celery -A pyfarm.scheduler.celery_app:celery_app worker -b 'redis://'

If the pyfarm installation changes, the worker needs to be restarted.
