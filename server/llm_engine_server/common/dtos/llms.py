"""
DTOs for LLM APIs.
"""

from typing import Any, Dict, List, Optional

from llm_engine_server.common.dtos.model_endpoints import (
    CpuSpecificationType,
    GetModelEndpointV1Response,
    GpuType,
    ModelEndpointType,
    StorageSpecificationType,
)
from llm_engine_server.domain.entities import (
    BatchJobStatus,
    CallbackAuth,
    LLMInferenceFramework,
    LLMSource,
    Quantization,
)
from pydantic import BaseModel, Field, HttpUrl

from .tasks import TaskStatus


class CreateLLMModelEndpointV1Request(BaseModel):
    name: str

    # LLM specific fields
    model_name: str
    source: LLMSource = LLMSource.HUGGING_FACE
    inference_framework: LLMInferenceFramework = LLMInferenceFramework.DEEPSPEED
    inference_framework_image_tag: str
    num_shards: int = 1
    """
    Number of shards to distribute the model onto GPUs. Only affects behavior for text-generation-inference models
    """

    quantize: Optional[Quantization] = None
    """
    Whether to quantize the model. Only affect behavior for text-generation-inference models
    """

    checkpoint_path: Optional[str] = None
    """
    Path to the checkpoint to load the model from. Only affects behavior for text-generation-inference models
    """

    # General endpoint fields
    metadata: Dict[str, Any]  # TODO: JSON type
    post_inference_hooks: Optional[List[str]]
    endpoint_type: ModelEndpointType = ModelEndpointType.SYNC
    cpus: CpuSpecificationType
    gpus: int
    memory: StorageSpecificationType
    gpu_type: GpuType
    storage: Optional[StorageSpecificationType]
    optimize_costs: Optional[bool]
    min_workers: int
    max_workers: int
    per_worker: int
    labels: Dict[str, str]
    prewarm: Optional[bool]
    high_priority: Optional[bool]
    default_callback_url: Optional[HttpUrl]
    default_callback_auth: Optional[CallbackAuth]
    public_inference: Optional[bool] = True  # LLM endpoints are public by default.


class CreateLLMModelEndpointV1Response(BaseModel):
    endpoint_creation_task_id: str


class GetLLMModelEndpointV1Response(BaseModel):
    id: str
    """
    The autogenerated ID of the LLMEngine endpoint.
    """

    name: str
    model_name: str
    source: LLMSource
    inference_framework: LLMInferenceFramework
    inference_framework_image_tag: str
    num_shards: int
    quantize: Optional[Quantization] = None
    spec: GetModelEndpointV1Response


class ListLLMModelEndpointsV1Response(BaseModel):
    model_endpoints: List[GetLLMModelEndpointV1Response]


# Delete and update use the default LLMEngine endpoint APIs.


class CompletionSyncV1Request(BaseModel):
    """
    Request object for a synchronous prompt completion task.
    """

    prompts: List[str]
    max_new_tokens: int
    temperature: float = Field(gt=0, le=100)


class CompletionOutput(BaseModel):
    text: str
    num_completion_tokens: int


class CompletionSyncV1Response(BaseModel):
    """
    Response object for a synchronous prompt completion task.
    """

    status: TaskStatus
    outputs: List[CompletionOutput]
    traceback: Optional[str] = None


class CompletionStreamV1Request(BaseModel):
    """
    Request object for a stream prompt completion task.
    """

    prompt: str
    max_new_tokens: int
    temperature: float = Field(gt=0, le=100)


class CompletionStreamOutput(BaseModel):
    text: str
    finished: bool
    num_completion_tokens: Optional[int] = None


class CompletionStreamV1Response(BaseModel):
    """
    Response object for a stream prompt completion task.
    """

    status: TaskStatus
    output: Optional[CompletionStreamOutput] = None
    traceback: Optional[str] = None


class CreateFineTuneJobRequest(BaseModel):
    training_file: str
    validation_file: str
    model_name: str
    base_model: str  # TODO enum
    fine_tuning_method: str  # TODO enum
    hyperparameters: Dict[str, str]  # TODO validated somewhere else


class CreateFineTuneJobResponse(BaseModel):
    fine_tune_id: str


class GetFineTuneJobResponse(BaseModel):
    fine_tune_id: str
    status: BatchJobStatus


class ListFineTuneJobResponse(BaseModel):
    jobs: List[GetFineTuneJobResponse]


class CancelFineTuneJobResponse(BaseModel):
    success: bool
