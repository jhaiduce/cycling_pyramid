import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession):
    """
    Add or update models / fixtures in the database.

    """
    Base=models.Base
    engine=dbsession.bind
    Base.metadata.create_all(engine)

def create_database(engine,settings):

    from sqlalchemy.sql import text
    from MySQLdb import escape_string
    
    conn=engine.connect()
    conn.execute('commit')
    conn.execute('create database if not exists cycling')
    s=text("create or replace user cycling identified by '{pw}'".format(
        pw=escape_string(settings['mysql_cycling_password']).decode('ascii')))
    conn.execute(s)
    conn.execute("grant all on cycling.* to cycling")
    conn.execute("use cycling")
    
def create_admin_user(dbsession,settings):

    user=models.User(
        name='admin'
    )

    import pprint
    pp=pprint.PrettyPrinter(indent=2)
    pp.pprint(settings)

    user.set_password(settings['admin_password'])
    dbsession.add(user)

def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    return parser.parse_args(argv[1:])

def main(argv=sys.argv):
    args = parse_args(argv)
    setup_logging(args.config_uri)


    env = bootstrap(args.config_uri)
    settings=env['request'].registry.settings

    engine_admin=models.get_engine(settings,prefix='sqlalchemy_admin.')

    try:
        
        create_database(engine_admin,settings)
            
        import transaction
        with transaction.manager:
            admin_session_factory=models.get_session_factory(engine_admin)
            admin_session=models.get_tm_session(admin_session_factory,transaction.manager)
            setup_models(admin_session)
        
        with env['request'].tm:
            
            dbsession = env['request'].dbsession
            create_admin_user(dbsession,settings)
    except OperationalError:
        raise
