from ..celery import celery

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

import transaction

def get_model(dbsession):
    from ..models.cycling_models import PredictionModel

    from sqlalchemy.orm.exc import NoResultFound

    try:
        model=dbsession.query(PredictionModel).one()
    except NoResultFound:
        model=PredictionModel()
        dbsession.add(model)

    return model

@celery.task(ignore_result=False)
def train_model():

    from ..celery import session_factory
    from ..models import get_tm_session
    from ..models.cycling_models import Ride
    from sqlalchemy import func

    logger.debug('Received train model task')

    train_dataset_size=None

    with transaction.manager:
        dbsession=get_tm_session(session_factory,transaction.manager)
        dbsession.expire_on_commit=False

        model=get_model(dbsession)

        if model.training_in_progress:
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

    if training_due:

        with transaction.manager:
            dbsession=get_tm_session(session_factory,transaction.manager)
            dbsession.add(model)
            model.training_in_progress=True

        from ..models.prediction import get_data

        predict_columns=['avspeed']
        train_dataset=get_data(dbsession,predict_columns)

        with transaction.manager:
            dbsession=get_tm_session(session_factory,transaction.manager)
            dbsession.add(model)
            try:

                model.train(train_dataset,predict_columns)

                train_dataset_size=model.train_dataset_size

            finally:
                model.training_in_progress=False

    return train_dataset_size
