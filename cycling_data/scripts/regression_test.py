import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models

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

    tf.keras.backend.set_floatx('float64')

    # Fetch the data
    rides=dbsession.query(Ride).filter(Ride.wxdata!=None)
    dataset=pd.read_sql_query(rides.statement,rides.session.bind)

    dataset['fraction_day']=[ride.fraction_day for ride in rides]

    dataset['grade']=[ride.grade for ride in rides]

    dataset['tailwind']=[ride.tailwind for ride in rides]

    dataset['crosswind']=[ride.crosswind for ride in rides]

    dataset['temperature']=[ride.wxdata.temperature for ride in rides]

    dataset['pressure']=[ride.wxdata.pressure for ride in rides]

    dataset['rain']=[ride.wxdata.rain for ride in rides]

    dataset['snow']=[ride.wxdata.snow for ride in rides]

    dataset['startlat']=[ride.startloc.lat if ride.startloc else None
                         for ride in rides]
    dataset['endlat']=[ride.endloc.lat if ride.endloc else None
                       for ride in rides]
    dataset['startlon']=[ride.startloc.lon if ride.startloc else None
                         for ride in rides]
    dataset['endlon']=[ride.endloc.lon if ride.endloc else None
                       for ride in rides]

    dataset['crowdist']=[ride.crowdist for ride in rides]

    ridergroups=dbsession.query(RiderGroup)
    surfacetypes=dbsession.query(SurfaceType)
    equipments=dbsession.query(Equipment)

    dataset['ridergroup']=dataset['ridergroup_id'].map({ridergroup.id:ridergroup.name for ridergroup in ridergroups})

    dataset['surfacetype']=dataset['surface_id'].map({surfacetype.id:surfacetype.name for surfacetype in surfacetypes})

    dataset['equipment']=dataset['equipment_id'].map({equipment.id:equipment.name for equipment in equipments})

    computed_avspeed=dataset.distance/dataset.rolling_time.dt.total_seconds()*3600
    pd.options.mode.use_inf_as_na = True

    dataset.avspeed.fillna(computed_avspeed,inplace=True)

    dataset.trailer.fillna(False,inplace=True)

    dataset.trailer=dataset.trailer.astype(float)

    predict_columns=['avspeed']

    dataset=dataset[predict_columns+['distance','ridergroup','surfacetype','equipment','trailer','grade','tailwind','crosswind','temperature','pressure','rain','snow','startlat','endlat','startlon','endlon','fraction_day','crowdist']]

    dataset=pd.get_dummies(dataset, prefix='', prefix_sep='')

    dataset.dropna(inplace=True)

    train_dataset = dataset.sample(frac=0.8,random_state=0)
    test_dataset = dataset.drop(train_dataset.index)

    train_stats = train_dataset.describe()
    train_stats = train_stats.drop(columns=predict_columns)
    train_stats = train_stats.transpose()
    print(train_stats)

    print(train_dataset.keys())

    train_labels=train_dataset[predict_columns]
    train_dataset = train_dataset.drop(columns=predict_columns)
    test_labels=test_dataset[predict_columns]
    test_dataset=test_dataset.drop(columns=predict_columns)

    def norm(x):
        return (x - train_stats['mean']) / train_stats['std']

    normed_train_data = norm(train_dataset)
    normed_test_data = norm(test_dataset)

    print(normed_train_data.tail())

    # Specify the surrogate posterior over `keras.layers.Dense` `kernel` and `bias`.
    def posterior_mean_field(kernel_size, bias_size=0, dtype=None):
        n = kernel_size + bias_size
        c = np.log(np.expm1(1.))
        return tf.keras.Sequential([
            tfp.layers.VariableLayer(2 * n, dtype=dtype),
            tfp.layers.DistributionLambda(lambda t: tfd.Independent(
                tfd.Normal(loc=t[..., :n],
                           scale=1e-5 + tf.nn.softplus(c + t[..., n:])),
                reinterpreted_batch_ndims=1)),
        ])

    # Specify the prior over `keras.layers.Dense` `kernel` and `bias`.
    def prior_trainable(kernel_size, bias_size=0, dtype=None):
        n = kernel_size + bias_size
        return tf.keras.Sequential([
            tfp.layers.VariableLayer(n, dtype=dtype),
            tfp.layers.DistributionLambda(lambda t: tfd.Independent(
                tfd.Normal(loc=t, scale=1),
                reinterpreted_batch_ndims=1)),
        ])

    def negloglik(y, p_y):
        return -p_y.log_prob(y)

    def build_model():
        c=np.log(np.expm1(1.))

        model = keras.Sequential([
            tfp.layers.DenseVariational(12,
                                        posterior_mean_field, prior_trainable,
                                        kl_weight=1/train_dataset.shape[0],
                                        activation='relu'),
            layers.LeakyReLU(alpha=0.3),
            tfp.layers.DenseVariational(1+1,
                                        posterior_mean_field, prior_trainable,
                                        kl_weight=1/train_dataset.shape[0]),
            tfp.layers.DistributionLambda(lambda t: tfd.Normal(
                loc=t[..., :1],
                scale=1e-5+tf.math.softplus(c * t[...,1:]))),
        ])

        optimizer = tf.optimizers.Adam(learning_rate=0.02,epsilon=0.001)

        model.compile(loss=negloglik,
                      optimizer=optimizer,
                      metrics=['mae', 'mse'])
        return model

    model=build_model()

    example_batch = normed_train_data[:10]
    example_result = model(example_batch.to_numpy())
    assert isinstance(example_result, tfd.Distribution)
    print(example_result)

    print(model.summary())

    EPOCHS=2000

    # The patience parameter is the amount of epochs to check for improvement
    early_stop = keras.callbacks.EarlyStopping(
        monitor='val_loss', min_delta=1e-7, patience=300)

    history=model.fit(normed_train_data, train_labels,
                      epochs=EPOCHS, validation_split = 0.2, verbose = 0,
                      callbacks=[early_stop, tfdocs.modeling.EpochDots()])

    model.save('model.h5')

    hist = pd.DataFrame(history.history)
    hist['epoch'] = history.epoch
    hist.tail()

    plotter = tfdocs.plots.HistoryPlotter(smoothing_std=2)

    plotter.plot({'Basic': history}, metric = "mae")
    plt.ylim([0, 10])
    plt.ylabel('MAE [avspeed]')

    test_predictions = model.predict(normed_test_data).flatten()

    yhats=[model(normed_test_data.to_numpy()) for _ in range(100)]

    test_predictions=np.mean([yhat.mean().numpy().flatten() for yhat in yhats],axis=0)

    test_errors=np.linalg.norm(
        [
            np.mean([yhat.stddev().numpy().flatten() for yhat in yhats],axis=0),
            np.std([yhat.mean().numpy().flatten() for yhat in yhats],axis=0)
        ],
        axis=0)

    plt.figure()
    ax=plt.axes(aspect='equal')
    plt.errorbar(test_labels['avspeed']-test_predictions,test_errors,linestyle='',marker='.',markersize=4,capsize=2)
    lims=[-30,30]
    plt.xlim(lims)
    plt.ylim([0,lims[1]])
    plt.plot([lims[0],0,lims[1]],[abs(lims[0]),0,abs(lims[1])])

    plt.figure()
    ax = plt.axes(aspect='equal')
    plt.errorbar(test_labels['avspeed'], test_predictions,yerr=test_errors,linestyle='',marker='.',markersize=4,capsize=2)
    plt.xlabel('True Values [km/h]')
    plt.ylabel('Predictions [km/h]')
    lims = [0, 50]
    plt.xlim(lims)
    plt.ylim(lims)
    rsquared=np.corrcoef(test_labels.avspeed,test_predictions)[0,1]**2
    plt.text(0.1,0.9,'$R^2$={:0.3f}'.format(rsquared), transform=ax.transAxes)
    _ = plt.plot(lims, lims)

    m=keras.metrics.RootMeanSquaredError()
    m.update_state(test_predictions,test_labels.avspeed)
    mae=m.result().numpy()

    plt.figure()
    error = test_predictions - test_labels.avspeed
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
