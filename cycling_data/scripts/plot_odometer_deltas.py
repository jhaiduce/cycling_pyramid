from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm import sessionmaker 
from sqlalchemy import engine_from_config, create_engine
from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.orm.exc import NoResultFound
import argparse
import sys

from .. import models

def plot_odometer_deltas(session):
    from matplotlib import pyplot as plt
    
    # Fetch the data
    rides=session.query(models.Ride).filter(
        models.Ride.equipment_id==0
    ).order_by(
        models.Ride.start_time
    ).with_entities(
        'start_time','end_time','odometer','distance')

    # Convert data to pandas
    import pandas as pd
    import numpy as np
    df=pd.read_sql_query(rides.statement,rides.session.bind,index_col='start_time')
    df=df.dropna()
    df=df.sort_values('start_time')

    df['next_odo']=pd.Series(df['odometer']+df['distance'])
    df['odo_delta']=df['odometer']-df['next_odo'].shift()
    print(df)

    #plt.hist(df['distance'],bins=500,normed=True)
    plt.hist(df['odo_delta'],bins=np.linspace(-2,2,400),normed=True)

    print(df['odo_delta'].quantile(0.1))
    print(df['odo_delta'].quantile(0.9))
    plt.show()


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

    engine = create_engine("mysql://cycling:cycling@localhost/cycling")
     
    # mapped classes are now created with names by default
    # matching that of the table name.

    session = sessionmaker(bind=engine)()

    with env['request'].tm:
        session=env['request'].dbsession
        plot_odometer_deltas(session)
