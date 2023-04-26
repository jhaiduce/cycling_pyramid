import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
tfd = tfp.distributions
from tensorflow import keras
from tensorflow.keras import layers
from sqlalchemy import func

predict_vars=['avspeed','maxspeed','total_time']

tf.keras.backend.set_floatx('float64')

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

def build_model(train_set_size,input_size,output_size):
    c=np.log(np.expm1(1.))

    model = keras.Sequential([
        layers.Dense(32, input_shape=[input_size],
                         activation='relu'),
        layers.Dense(16, activation='relu'),
        layers.LeakyReLU(alpha=0.3),
        layers.Dense(output_size)
    ])

    optimizer = tf.keras.optimizers.RMSprop(0.001)

    model.compile(loss='mse',
                  optimizer=optimizer,
                  metrics=['mae', 'mse'])
    model.build([None,input_size])
    return model

def get_data(dbsession,predict_columns,extra_fields=[],tm=None):

    from .cycling_models import Ride
    import pandas as pd

    rides=dbsession.query(Ride)

    return prepare_model_dataset(rides,dbsession,predict_columns,extra_fields=extra_fields,tm=tm)

def get_average_interval(dbsession, ride, field):
    from .cycling_models import Ride

    from sqlite3 import Connection as sqliteConnection

    conn=dbsession.bind

    if isinstance(conn, sqliteConnection):
        avg_expr=func.avg(func.strftime('%s',getattr(Ride,field)))
    else:
        avg_expr=func.avg(getattr(Ride,field))

    avg=dbsession.query(avg_expr).filter(
        Ride.startloc==ride.startloc, Ride.endloc==ride.endloc
    ).scalar()

    if not avg:
        avg=dbsession.query(avg_expr).scalar()

    return avg

def est_total_time(ride, dbsession):

    from .cycling_models import Ride
    from datetime import timedelta

    if ride.start_time and ride.end_time:
        return ride.end_time - ride.start_time

    else:
        avg_rolling_time=get_average_interval(dbsession, ride, 'rolling_time')
        avg_total_time=get_average_interval(dbsession, ride, 'total_time')

        if ride.rolling_time:
            rolling_time=ride.rolling_time
        else:
            avg_speed=dbsession.query(func.avg(Ride.avspeed)).scalar()
            rolling_time=timedelta(hours=ride.distance/avg_speed)

        return rolling_time*float(avg_total_time/avg_rolling_time)

def prepare_model_dataset(rides,dbsession,predict_columns,extra_fields=[],tm=None):
    from .cycling_models import Ride, RiderGroup, SurfaceType, Equipment, Location
    import pandas as pd
    import transaction
    from sqlalchemy.orm import joinedload, subqueryload
    from sqlalchemy.orm.exc import NoResultFound
    from pytz import utc

    if tm is None:
        tm=transaction.manager

    if hasattr(rides,'statement'):
        q=rides.with_entities(Ride.id,Ride.distance,Ride.ridergroup_id,Ride.surface_id,Ride.equipment_id,Ride.trailer,Ride.rolling_time,Ride.avspeed,Ride.maxspeed,Ride.total_time,*extra_fields)
        with tm:
            dataset=pd.read_sql_query(q.statement,dbsession.bind)
    else:
        dataset=pd.DataFrame([
            dict(
                id=ride.id,
                distance=ride.distance,
                ridergroup_id=ride.ridergroup.id,
                surface_id=ride.surface.id,
                equipment_id=ride.equipment.id,
                trailer=ride.trailer,
                rolling_time=ride.rolling_time,
                avspeed=ride.avspeed,
                maxspeed=ride.maxspeed,
                total_time=ride.total_time
            )
            for ride in rides
        ])

    if len(dataset)==0: return

    for column_name in 'fraction_day','tailwind','crosswind','temperature','pressure','rain','snow','startlat','endlat','startlon','endlon','crowdist':
        dataset[column_name]=pd.Series(np.nan, index=dataset.index, dtype=float)

    for i,ride_id in enumerate(dataset['id']):
        with tm:
            try:
                ride=dbsession.query(Ride).filter(Ride.id==ride_id).one()
            except NoResultFound:
                ride=rides[i]
                ride.id=-1
                dataset.loc[i,'id']=-1

            if not ride.total_time:
                ride.total_time=est_total_time(ride, dbsession)
            if not ride.end_time:
                ride.end_time=ride.start_time+ride.total_time

            dataset.loc[i,'fraction_day']=ride.fraction_day
            dataset.loc[i,'grade']=ride.grade
            dataset.loc[i,'crowdist']=ride.crowdist
            if ride.start_time:
                dataset.loc[i,'start_time']=pd.to_datetime(
                    ride.start_time.astimezone(utc))
            if ride.end_time:
                dataset.loc[i,'end_time']=pd.to_datetime(
                    ride.end_time.astimezone(utc))
            elif ride.total_time and ride.start_time:
                dataset.loc[i,'end_time']=pd.to_datetime(
                    (ride.start_time+ride.total_time).astimezone(utc))

            if ride.wxdata:
                dataset.loc[i,'tailwind']=ride.tailwind
                dataset.loc[i,'crosswind']=ride.crosswind
                dataset.loc[i,'temperature']=ride.wxdata.temperature
                dataset.loc[i,'pressure']=ride.wxdata.pressure
                dataset.loc[i,'rain']=ride.wxdata.rain
                dataset.loc[i,'snow']=ride.wxdata.snow

            if ride.startloc:
                dataset.loc[i,'startlat']=ride.startloc.lat
                dataset.loc[i,'startlon']=ride.startloc.lon

            if ride.endloc:
                dataset.loc[i,'endlat']=ride.endloc.lat
                dataset.loc[i,'endlon']=ride.endloc.lon

    dataset.start_time=pd.to_datetime(dataset.start_time)
    dataset.end_time=pd.to_datetime(dataset.end_time)

    with transaction.manager:
        ridergroups=dbsession.query(RiderGroup)
        surfacetypes=dbsession.query(SurfaceType)
        equipments=dbsession.query(Equipment)

    dataset['ridergroup']=dataset['ridergroup_id'].map({ridergroup.id:ridergroup.name for ridergroup in ridergroups})

    dataset['surfacetype']=dataset['surface_id'].map({surfacetype.id:surfacetype.name for surfacetype in surfacetypes})

    dataset['equipment']=dataset['equipment_id'].map({equipment.id:equipment.name for equipment in equipments})

    rolling_time=pd.to_timedelta(dataset.rolling_time,errors='coerce')
    computed_avspeed=(dataset.distance/rolling_time.dt.total_seconds()*3600).astype('float64')
    pd.options.mode.use_inf_as_na = True

    dataset.total_time=(pd.to_timedelta(
        dataset.total_time,errors='coerce').dt.total_seconds()/60)

    dataset.avspeed.fillna(computed_avspeed,inplace=True)

    computed_total_time=(dataset.end_time-dataset.start_time).dt.total_seconds()/60

    dataset.total_time.fillna(computed_total_time,inplace=True)

    dataset.trailer.fillna(False,inplace=True)

    dataset.trailer=dataset.trailer.astype(float)

    dataset.start_time=(dataset.start_time-pd.Timestamp('1970-01-01',tz=utc))/pd.Timedelta('1d')

    dataset=dataset[set(predict_columns+['id','start_time','distance','ridergroup','surfacetype','equipment','trailer','grade','tailwind','crosswind','temperature','pressure','rain','snow','startlat','endlat','startlon','endlon','fraction_day','crowdist']+[field.name for field in extra_fields])]

    for column, values in (
            ('ridergroup',ridergroups),
            ('equipment',equipments),
            ('surfacetype',surfacetypes)
    ):
        dataset=pd.get_dummies(dataset, columns=[column], prefix=column, prefix_sep='_')
        for value in values:
            dummy_name=column+'_'+value.name
            if dummy_name not in dataset:
                dataset[dummy_name]=0

    return dataset

def get_model(dbsession,predict_var='avspeed'):
    from .cycling_models import PredictionModel

    from sqlalchemy.orm.exc import NoResultFound

    try:
        model=dbsession.query(PredictionModel).filter(PredictionModel.predict_columns_.like('%{}%'.format(predict_var))).one()
    except NoResultFound:
        model=PredictionModel()
        dbsession.add(model)

    return model

def get_ride_predictions(session,rides,predict_var='avspeed'):

    import numpy as np

    model=get_model(session)

    prediction_inputs=prepare_model_dataset(rides,session,model.predict_columns)
    if prediction_inputs is not None:
        predictions=model.predict(prediction_inputs)
    else:
        predictions=np.empty([0,1])

    return predictions
