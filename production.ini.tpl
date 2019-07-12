###
# app configuration
# https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html
###

[app:main]
use = egg:cycling_data

pyramid.reload_templates = false
pyramid.debug_authorization = false
pyramid.debug_notfound = false
pyramid.debug_routematch = false
pyramid.default_locale_name = en

retry.attempts = 3

filter-with = proxy-prefix

sqlalchemy.url = mysql://cycling:{mysql_production_password}@cycling_stack_db:3306/cycling

auth.secret={pyramid_auth_secret}

sqlalchemy_admin.url = mysql://root:{mysql_root_password}@cycling_stack_db:3306
mysql_cycling_password={mysql_production_password}
admin_password={cycling_admin_password}

[pshell]
setup = cycling_data.pshell.setup

###
# wsgi server configuration
###

[alembic]
# path to migration scripts
script_location = cycling_data/alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s
# file_template = %%(rev)s_%%(slug)s
sqlalchemy.url = mysql://root:{mysql_root_password}@cycling_stack_db:3306/cycling

[server:main]
use = egg:waitress#main
listen = *:80

###
# logging configuration
# https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/logging.html
###

[loggers]
keys = root, cycling_data, sqlalchemy

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_cycling_data]
level = WARN
handlers =
qualname = cycling_data

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
# "level = INFO" logs SQL queries.
# "level = DEBUG" logs SQL queries and results.
# "level = WARN" logs neither.  (Recommended for production systems.)

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(asctime)s %(levelname)-5.5s [%(name)s:%(lineno)s][%(threadName)s] %(message)s

[filter:proxy-prefix]
use = egg:PasteDeploy#prefix
scheme=http