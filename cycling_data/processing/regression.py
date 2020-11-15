from ..celery import celery

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

import transaction

@celery.task(ignore_result=False)
def train_model():

    from ..celery import session_factory
    from ..models import get_tm_session
    from ..models.cycling_models import PredictionModel, Ride
    from sqlalchemy.orm.exc import NoResultFound
    from sqlalchemy import func

    with transaction.manager:
        dbsession=get_tm_session(session_factory,transaction.manager)

        logger.debug('Received update weather task for ride {}'.format(ride_id))

        try:
            model=dbsession.query(PredictionModel).one()
        except NoResultFound:
            model=PredictionModel()

        if model.training_in_progress:
            return

        data_modified_date = dbsession.query(func.max(Ride.modified_date).label('last_modified')).last_modified

    if (
            data_modified_date > model.modified_date
            and not model.training_in_progress
    ):
        try:

            with transaction.manager:
                dbsession=get_tm_session(session_factory,transaction.manager)
                model.training_in_progress=True

            with transaction.manager:
                dbsession=get_tm_session(session_factory,transaction.manager)
                model.train(dbsession)

        finally:
            with transaction.manager:
                dbsession=get_tm_session(session_factory,transaction.manager)
                model.training_in_progress=False

    return model.train_dataset_size
