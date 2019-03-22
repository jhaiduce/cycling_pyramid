from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm import sessionmaker 
from sqlalchemy import engine_from_config, create_engine
from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.orm.exc import NoResultFound
import argparse
import sys

from .. import models

def plot_speed_deltas(session):
    from matplotlib import pyplot as plt
    
    # Fetch the data
    rides=session.query(models.Ride)

    # Convert data to pandas
    import pandas as pd
    import numpy as np
    df=pd.read_sql_query(rides.statement,rides.session.bind)

    rolling_time_hours=df['rolling_time']/np.timedelta64(1,'h')
    df['avspeed_est']=pd.Series(df['distance']/rolling_time_hours,index=df.index)
    ratio=df['avspeed']/df['avspeed_est']

    plt.hist(ratio,bins=500,normed=True)

    print(ratio.quantile(0.1))
    print(ratio.quantile(0.9))
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
        plot_speed_deltas(session)
