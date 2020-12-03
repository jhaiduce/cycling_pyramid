import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models


def setup_models(dbsession,ini_file):
    """
    Add or update models / fixtures in the database.

    """
    import alembic.config
    alembicArgs = [
        '-c',ini_file,
        '--raiseerr',
        'upgrade', 'head',
    ]
    alembic.config.main(argv=alembicArgs)

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

    user.set_password(settings['admin_password'])
    dbsession.add(user)

def add_loctype_if_not_exists(dbsession,loctype_id,name):
    from ..models.cycling_models import LocationType

    loctype=dbsession.query(
        LocationType
    ).filter(LocationType.id==loctype_id
    ).filter(LocationType.name==name
    ).first()

    if loctype is None:
        dbsession.add(LocationType(id=loctype_id,name=name))

def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    parser.add_argument(
        '--delete-existing',
        help='Delete existing database',
        action='store_true'
    )
    return parser.parse_args(argv[1:])

def main(argv=sys.argv):
    args = parse_args(argv)
    setup_logging(args.config_uri)


    env = bootstrap(args.config_uri)
    settings=env['request'].registry.settings

    engine_admin=models.get_engine(settings,prefix='sqlalchemy_admin.')

    while True:

        # Here we try to connect to database server until connection succeeds.
        # This is needed because the database server may take longer
        # to start than the application
        
        import sqlalchemy.exc

        try:
            print("Checking database connection")
            conn=engine_admin.connect()
            conn.execute("select 'OK'")

        except sqlalchemy.exc.OperationalError:
            import time
            print("Connection failed. Sleeping.")
            time.sleep(2)
            continue
        
        # If we get to this line, connection has succeeded so we break
        # out of the loop
        break
    try:

        if engine_admin.dialect.name!='sqlite':
            if args.delete_existing:
                conn=engine_admin.connect()
                try:
                    conn.execute('drop database cycling')
                except OperationalError:
                    pass
            create_database(engine_admin,settings)
            
        import transaction
        with transaction.manager:
            admin_session_factory=models.get_session_factory(engine_admin)
            admin_session=models.get_tm_session(admin_session_factory,transaction.manager)
            
        with env['request'].tm:
            
            dbsession = env['request'].dbsession
            setup_models(dbsession,args.config_uri)
            admin_exists=dbsession.query(models.User).filter(
                models.User.name=='admin').count()
            if not admin_exists:
                create_admin_user(dbsession,settings)


            add_loctype_if_not_exists(dbsession,1,None)
            add_loctype_if_not_exists(dbsession,2,'weather station')

    except OperationalError:
        raise
