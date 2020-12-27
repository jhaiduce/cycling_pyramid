import argparse
import sys
import os
import h5py
import json

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models

from ..models.prediction import build_model, get_data, get_model, prepare_model_dataset

from ..models.cycling_models import Ride, RiderGroup, SurfaceType, Equipment

def regress(dbsession):

    import tensorflow as tf
    import tensorflow_probability as tfp
    tfd = tfp.distributions
    from tensorflow import keras
    from tensorflow.keras import layers
    import pandas as pd
    import seaborn as sns
    from matplotlib import pyplot as plt
    import tensorflow_docs as tfdocs
    import tensorflow_docs.plots
    import tensorflow_docs.modeling
    import numpy as np
    from sqlalchemy.sql.expression import func

    tf.keras.backend.set_floatx('float64')

    predict_columns=['avspeed']

    from cycling_data.processing.regression import train_model
    from cycling_data import celery
    from unittest.mock import patch

    with patch.object(
                celery,'session_factory',
                return_value=dbsession) as session_factory:
        train_model()

    model_wrapper=get_model(dbsession)

    # Fetch the data
    dataset=get_data(dbsession,predict_columns)

    dataset=dataset.dropna()

    test_dataset = dataset.copy()

    test_predictions = model_wrapper.predict(test_dataset).flatten()

    plt.figure()
    ax = plt.axes(aspect='equal')
    plt.plot(test_dataset['avspeed'], test_predictions,linestyle='',marker='.',markersize=4)
    plt.xlabel('True Values [km/h]')
    plt.ylabel('Predictions [km/h]')
    lims = [0, 50]
    plt.xlim(lims)
    plt.ylim(lims)
    rsquared=np.corrcoef(test_dataset.avspeed,test_predictions)[0,1]**2
    plt.text(0.1,0.9,'$R^2$={:0.3f}'.format(rsquared), transform=ax.transAxes)
    _ = plt.plot(lims, lims)

    m=keras.metrics.RootMeanSquaredError()
    m.update_state(test_predictions,test_dataset.avspeed)
    mae=m.result().numpy()

    plt.figure()
    error = test_predictions - test_dataset.avspeed
    plt.hist(error, bins = 200)
    plt.xlabel("Prediction Error [km/h]")
    plt.text(0.1,0.9,'MAE={:0.3f}'.format(mae), transform=ax.transAxes)
    _ = plt.ylabel("Count")

    plt.show()


    #sns.pairplot(train_dataset,diag_kind='kde')
    #plt.show()

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

        with env['request'].tm:
            
            dbsession = env['request'].dbsession

            regress(dbsession)

    except OperationalError:
        raise
