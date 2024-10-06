import contextlib
import datetime
import os

from bson import ObjectId
from google.api_core.exceptions import AlreadyExists
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from api.schemas.conversation import ConversationStage, PregenerateOptions

_SELF_URI = os.getenv("SELF_URI", "")
_GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
_GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "")
_GCP_QUEUE = os.getenv("GOOGLE_CLOUD_QUEUE", "")

_INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

DEFER_PREGENERATION = bool(_SELF_URI and _GCP_PROJECT and _GCP_LOCATION and _GCP_QUEUE)


async def create_pregenerate_task(user_id: ObjectId, stage: ConversationStage) -> None:
    client = tasks_v2.CloudTasksAsyncClient()

    name = client.task_path(
        _GCP_PROJECT, _GCP_LOCATION, _GCP_QUEUE, f"{str(user_id)}_{str(stage)}"
    )

    options = PregenerateOptions(user_id=user_id, stage=stage)

    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=f"{_SELF_URI}/conversations/pregenerate",
            headers={
                "Content-type": "application/json",
                "Authorization": f"Bearer {_INTERNAL_API_KEY}",
            },
            body=options.model_dump_json().encode(),
        ),
        name=name,
        schedule_time=timestamp_pb2.Timestamp().FromDatetime(
            datetime.datetime.now(datetime.timezone.utc)
        ),
    )

    with contextlib.suppress(AlreadyExists):
        task = await client.create_task(
            parent=client.queue_path(_GCP_PROJECT, _GCP_LOCATION, _GCP_QUEUE), task=task
        )
