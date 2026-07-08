from app.core.config import Settings
from app.core.lifespan import build_location_queues


def test_location_queue_builder_uses_configured_worker_count_and_queue_size() -> None:
    settings = Settings(LOCATION_WORKER_COUNT=3, QUEUE_MAXSIZE=7)

    queues = build_location_queues(settings.location_worker_count, settings.queue_maxsize)

    assert len(queues) == 3
    assert [queue.maxsize for queue in queues] == [7, 7, 7]
