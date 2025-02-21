from llm_engine_server.core.config import ml_infra_config
from llm_engine_server.core.loggers import filename_wo_ext, make_logger
from llm_engine_server.domain.entities import BatchJobProgress
from llm_engine_server.infra.gateways import BatchJobProgressGateway, FilesystemGateway

logger = make_logger(filename_wo_ext(__file__))


def get_batch_job_progress_location(user_id: str, batch_job_id: str):
    return f"s3://{ml_infra_config().s3_bucket}/batch_job_progress/{user_id}/{batch_job_id}"


class LiveBatchJobProgressGateway(BatchJobProgressGateway):
    def __init__(self, filesystem_gateway: FilesystemGateway) -> None:
        self.filesystem_gateway = filesystem_gateway

    def get_progress(self, owner: str, batch_job_id: str) -> BatchJobProgress:
        progress = None
        progress_location = get_batch_job_progress_location(
            user_id=owner, batch_job_id=batch_job_id
        )
        try:
            with self.filesystem_gateway.open(
                progress_location, aws_profile=ml_infra_config().profile_ml_worker
            ) as f:
                progress = BatchJobProgress.parse_raw(f.read())
        except Exception:
            logger.exception(f"Error while getting progress for batch job {batch_job_id}.")
        finally:
            if progress is None:
                progress = BatchJobProgress(
                    num_tasks_pending=None,
                    num_tasks_completed=None,
                )
        return progress

    def update_progress(self, owner: str, batch_job_id: str, progress: BatchJobProgress) -> None:
        progress_location = get_batch_job_progress_location(
            user_id=owner, batch_job_id=batch_job_id
        )
        with self.filesystem_gateway.open(
            progress_location, "w", aws_profile=ml_infra_config().profile_ml_worker
        ) as f:
            f.write(progress.json())
