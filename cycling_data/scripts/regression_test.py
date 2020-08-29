import argparse
import sys

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from .. import models

from ..models.cycling_models import Ride, RiderGroup, SurfaceType, Equipment

def regress(dbsession):

    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    import pandas as pd
    import seaborn as sns
    from matplotlib import pyplot as plt
    import tensorflow_docs as tfdocs
    import tensorflow_docs.plots
    import tensorflow_docs.modeling

    # Fetch the data
    rides=dbsession.query(Ride)
    dataset=pd.read_sql_query(rides.statement,rides.session.bind)

    dataset['grade']=[ride.grade for ride in rides]

    dataset['tailwind']=[ride.tailwind for ride in rides]

    dataset['crosswind']=[ride.crosswind for ride in rides]

    dataset['temperature']=[ride.wxdata.temperature for ride in rides]

    print(dataset.tail())

    print(dataset.columns)

    print(dataset.ridergroup_id.tail())

    ridergroups=dbsession.query(RiderGroup)
    surfacetypes=dbsession.query(SurfaceType)
    equipments=dbsession.query(Equipment)

    dataset['ridergroup']=dataset['ridergroup_id'].map({ridergroup.id:ridergroup.name for ridergroup in ridergroups})

    dataset['surfacetype']=dataset['surface_id'].map({surfacetype.id:surfacetype.name for surfacetype in surfacetypes})

    dataset['equipment']=dataset['equipment_id'].map({equipment.id:equipment.name for equipment in equipments})

    computed_avspeed=dataset.distance/dataset.rolling_time.dt.total_seconds()*3600
    print('Max avspeed:',dataset.avspeed.max())

    pd.options.mode.use_inf_as_na = True

    dataset.avspeed.fillna(computed_avspeed,inplace=True)

    dataset.trailer.fillna(False,inplace=True)

    dataset.trailer=dataset.trailer.astype(float)

    predict_columns=['avspeed']

    dataset=dataset[predict_columns+['distance','ridergroup','surfacetype','equipment','trailer','grade','tailwind','crosswind','temperature']]

    dataset=pd.get_dummies(dataset, prefix='', prefix_sep='')

    dataset.dropna(inplace=True)

    print('Max avspeed:',dataset.avspeed.max())

    train_dataset = dataset.sample(frac=0.8,random_state=0)
    test_dataset = dataset.drop(train_dataset.index)

    train_stats = train_dataset.describe()
    train_stats.drop(columns=predict_columns)
    train_stats = train_stats.transpose()
    print(train_stats)

    print(train_dataset.tail())

    print(train_dataset.keys())

    train_labels=train_dataset[predict_columns]
    train_dataset.drop(columns=predict_columns)
    test_labels=test_dataset[predict_columns]
    test_labels.drop(columns=predict_columns)

    def norm(x):
        return (x - train_stats['mean']) / train_stats['std']

    normed_train_data = norm(train_dataset)
    normed_test_data = norm(test_dataset)

    print(normed_train_data.tail())

    def build_model():
        model = keras.Sequential([
            layers.Dense(64, activation='relu', input_shape=[len(train_dataset.keys())]),
            layers.Dense(64, activation='relu'),
            layers.Dense(1)
        ])

        optimizer = tf.keras.optimizers.RMSprop(0.001)

        model.compile(loss='mse',
                      optimizer=optimizer,
                      metrics=['mae', 'mse'])
        return model

    model=build_model()

    example_batch = normed_train_data[:10]
    example_result = model.predict(example_batch)
    print(example_result)

    print(model.summary())

    EPOCHS=1000

    # The patience parameter is the amount of epochs to check for improvement
    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', patience=10)

    history=model.fit(normed_train_data, train_labels,
                      epochs=EPOCHS, validation_split = 0.2, verbose = 0,
                      callbacks=[early_stop, tfdocs.modeling.EpochDots()])

    hist = pd.DataFrame(history.history)
    hist['epoch'] = history.epoch
    hist.tail()

    plotter = tfdocs.plots.HistoryPlotter(smoothing_std=2)

    plotter.plot({'Basic': history}, metric = "mae")
    plt.ylim([0, 10])
    plt.ylabel('MAE [avspeed]')

    test_predictions = model.predict(normed_test_data).flatten()

    a = plt.axes(aspect='equal')
    plt.scatter(test_labels, test_predictions)
    plt.xlabel('True Values [km/h]')
    plt.ylabel('Predictions [km/h]')
    lims = [0, 50]
    plt.xlim(lims)
    plt.ylim(lims)
    _ = plt.plot(lims, lims)

    plt.figure()
    error = test_predictions - test_labels.avspeed
    plt.hist(error, bins = 200)
    plt.xlabel("Prediction Error [km/h]")
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
