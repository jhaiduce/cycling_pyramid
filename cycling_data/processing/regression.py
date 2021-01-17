from ..celery import celery

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

import transaction

from ..models.prediction import get_model
from sqlalchemy.orm.exc import NoResultFound

import numpy as np

@celery.task(ignore_result=False)
def train_model(*args,epochs=1000,patience=100):

    from ..celery import session_factory
    from ..models import get_tm_session
    from ..models.cycling_models import Ride, PredictionModelResult
    from sqlalchemy import func

    logger.debug('Received train model task')

    train_dataset_size=None

    dbsession=session_factory()
    dbsession.expire_on_commit=False

    with transaction.manager:

        model=get_model(dbsession)

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

        with transaction.manager:
            model.training_in_progress=True

        dbsession.commit()

        from ..models.prediction import get_data

        predict_columns=['avspeed']
        train_dataset=get_data(dbsession,predict_columns)

        if train_dataset is None:
            raise ValueError('Empty training dataset')

        try:

            with transaction.manager:
                model.train(train_dataset,predict_columns,
                            epochs=epochs,patience=patience)

                train_dataset_size=model.train_dataset_size

        finally:
            with transaction.manager:
                model.training_in_progress=False
                dbsession.commit()

        predictions=model.predict(train_dataset)

        for ride_id,prediction in zip(train_dataset['id'],predictions):
            logger.debug('Recording regression result for ride {}'.format(ride_id))
            with transaction.manager:
                try:
                    ride_prediction=dbsession.query(PredictionModelResult).filter(
                        PredictionModelResult.model_id==model.id,
                        PredictionModelResult.ride_id==ride_id).one()
                except NoResultFound:
                    ride_prediction=PredictionModelResult(
                        model_id=model.id, ride_id=ride_id)

                ride_prediction.result=prediction[0] if not np.isnan(prediction[0]) else None
                dbsession.add(ride_prediction)
                dbsession.commit()

        dbsession.commit()

    return train_dataset_size
