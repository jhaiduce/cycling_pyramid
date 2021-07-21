from ..celery import celery

from celery.utils.log import get_task_logger

from celery import group

logger = get_task_logger(__name__)

import transaction

from ..models.prediction import get_model, predict_vars
from sqlalchemy.orm.exc import NoResultFound

import numpy as np

@celery.task(ignore_result=False)
def train_model(predict_var='avspeed',epochs=None,patience=100):

    from ..celery import session_factory, settings
    from ..models import get_tm_session
    from ..models.cycling_models import Ride, PredictionModel, PredictionModelResult
    from sqlalchemy import func
    from ..models.prediction import get_data

    if epochs is None:
        epochs=settings.get('celery','train_model_default_epochs',fallback=1000)

    logger.debug('Received train model task')

    train_dataset_size=None

    if not(isinstance(predict_var,str)):
        raise TypeError('predict_var should be a string, got {} (type {})'.format(predict_var, type(predict_var)))

    import transaction

    dbsession=session_factory()
    tm=transaction.manager

    with tm:

        model=get_model(dbsession,predict_var)
        dbsession.flush()
        model_id=model.id

        if model.training_in_progress:
            logger.debug('Training already in progress, exiting.')
            return

        data_modified_date = dbsession.query(func.max(Ride.modified_date).label('last_modified')).one().last_modified

        training_due=(
            (
                model.modified_date is None
                or model.weightsbuf is None
                or data_modified_date is None
                or data_modified_date > model.modified_date
            )
            and not model.training_in_progress
        )

    if not training_due:
        logger.debug('Training is not due, exiting.')

    if training_due:

        with tm:
            model=dbsession.query(PredictionModel).filter(
                PredictionModel.id==model_id).one()
            model.training_in_progress=True

        predict_columns=[predict_var]

        with tm:
            train_dataset=get_data(dbsession,predict_columns,tm=tm)

        if train_dataset is None:
            raise ValueError('Empty training dataset')

        try:

            with tm:
                model=dbsession.query(PredictionModel).filter(
                    PredictionModel.id==model_id).one()
                model.train(train_dataset,predict_columns,
                            epochs=epochs,patience=patience)

                train_dataset_size=model.train_dataset_size

        finally:
            with tm:
                try:
                    model=dbsession.query(PredictionModel).filter(
                        PredictionModel.id==model_id).one()
                except NoResultFound:
                    pass
                else:
                    model.training_in_progress=False

        with tm:
            model=dbsession.query(PredictionModel).filter(
                PredictionModel.id==model_id).one()
            predictions=model.predict(train_dataset)

        for ride_id,prediction in zip(train_dataset['id'],predictions):
            logger.debug('Recording regression result for ride {}'.format(ride_id))
            with tm:
                try:
                    ride_prediction=dbsession.query(PredictionModelResult).filter(
                        PredictionModelResult.model_id==model_id,
                        PredictionModelResult.ride_id==ride_id).one()
                except NoResultFound:
                    ride_prediction=PredictionModelResult(
                        model_id=model_id, ride_id=ride_id)

                if predict_var=='avspeed':
                    ride_prediction.result=prediction[0] if not np.isnan(prediction[0]) else None

                setattr(ride_prediction,predict_var,prediction[0] if not np.isnan(prediction[0]) else None)

                dbsession.add(ride_prediction)

    return train_dataset_size

train_all_models=group(train_model.s(var) for var in predict_vars)
