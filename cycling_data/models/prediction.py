import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
tfd = tfp.distributions
from tensorflow import keras
from tensorflow.keras import layers

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

def build_model(train_set_size,input_size):
    c=np.log(np.expm1(1.))

    model = keras.Sequential([
        layers.Dense(64, input_shape=[input_size],
                         activation='relu'),
        layers.Dense(64, activation='relu'),
        layers.LeakyReLU(alpha=0.3),
        layers.Dense(1)
    ])

    optimizer = tf.optimizers.Adam(learning_rate=0.02,epsilon=0.001)

    model.compile(loss='mse',
                  optimizer=optimizer,
                  metrics=['mae', 'mse'])
    model.build([None,input_size])
    return model

def get_data(dbsession,predict_columns):

    from .cycling_models import Ride
    import pandas as pd

    rides=dbsession.query(Ride).filter(
        Ride.wxdata!=None
    ).filter(
        Ride.rolling_time is not None
    )

    return prepare_model_dataset(rides,dbsession,predict_columns)

def prepare_model_dataset(rides,dbsession,predict_columns):
    from .cycling_models import RiderGroup, SurfaceType, Equipment
    import pandas as pd
    import transaction

    if hasattr(rides,'statement'):
        with transaction.manager:
            dataset=pd.read_sql_query(rides.statement,dbsession.bind)
    else:
        dataset=pd.DataFrame([
            dict(
                distance=ride.distance,
                ridergroup_id=ride.ridergroup_id,
                surface_id=ride.surface_id,
                equipment_id=ride.equipment_id,
                trailer=ride.trailer,
                rolling_time=ride.rolling_time,
                avspeed=ride.avspeed,
            )
            for ride in rides
        ])

    if len(dataset)==0: return

    dataset['fraction_day']=pd.Series([ride.fraction_day for ride in rides],
                                          dtype=float)

    dataset['grade']=pd.Series([ride.grade for ride in rides], dtype=float)

    dataset['tailwind']=pd.Series([ride.tailwind for ride in rides],
                                   dtype=float)

    dataset['crosswind']=pd.Series([ride.crosswind for ride in rides],
                                   dtype=float)

    dataset['temperature']=pd.Series(
        [ride.wxdata.temperature for ride in rides], dtype=float)

    dataset['pressure']=pd.Series([ride.wxdata.pressure for ride in rides],
                                  dtype=float)

    dataset['rain']=pd.Series([ride.wxdata.rain for ride in rides], dtype=float)

    dataset['snow']=pd.Series([ride.wxdata.snow for ride in rides], dtype=float)

    dataset['startlat']=pd.Series(
        [ride.startloc.lat if ride.startloc else None
         for ride in rides], dtype=float)

    dataset['endlat']=pd.Series(
        [ride.endloc.lat if ride.endloc else None
         for ride in rides], dtype=float)

    dataset['startlon']=pd.Series(
        [ride.startloc.lon if ride.startloc else None
         for ride in rides], dtype=float)

    dataset['endlon']=pd.Series(
        [ride.endloc.lon if ride.endloc else None
         for ride in rides], dtype=float)

    dataset['crowdist']=pd.Series(
        [ride.crowdist for ride in rides], dtype=float)

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

    dataset=dataset[predict_columns+['distance','ridergroup','surfacetype','equipment','trailer','grade','tailwind','crosswind','temperature','pressure','rain','snow','startlat','endlat','startlon','endlon','fraction_day','crowdist']]

    for column, values in (
            ('ridergroup',ridergroups),
            ('equipment',equipments),
            ('surfacetype',surfacetypes)
    ):
        dataset=pd.get_dummies(dataset, columns=[column], prefix=column, prefix_sep='_')
        for value in values:
            if value.name not in dataset:
                dataset[column+'_'+value.name]=0.0

    return dataset

def get_model(dbsession):
    from .cycling_models import PredictionModel

    from sqlalchemy.orm.exc import NoResultFound

    try:
        model=dbsession.query(PredictionModel).one()
    except NoResultFound:
        model=PredictionModel()
        dbsession.add(model)

    return model

def get_ride_predictions(session,rides):

    import numpy as np

    model=get_model(session)
    if not hasattr(rides,'statement'):
        filtered_rides=[ride for ride in rides if ride.wxdata is not None]
        filtered_inds=[ind for ind,ride in enumerate(rides)
                       if ride.wxdata is not None]
    else:
        filtered_rides=rides

    prediction_inputs=prepare_model_dataset(filtered_rides,session,model.predict_columns)
    if prediction_inputs is not None:
        predictions=model.predict(prediction_inputs)
    else:
        predictions=np.empty([0,1])

    if not hasattr(rides,'statement'):
        predictions_with_nulls=np.empty([len(rides),1])
        predictions_with_nulls.fill(np.nan)
        predictions_with_nulls[filtered_inds]=predictions
        predictions=predictions_with_nulls

    return predictions
