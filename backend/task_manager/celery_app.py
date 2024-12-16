from celery import Celery

# Configure the Celery app
celery = Celery(
    "sazman_tasks",
    broker="redis://redis:6379/0",  # Redis as the message broker
    backend="redis://redis:6379/0",  # Redis as the result backend
)

# Celery configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery.task
def add_numbers(a, b):
    return a + b
