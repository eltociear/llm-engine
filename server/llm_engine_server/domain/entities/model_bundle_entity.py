import datetime
from abc import ABC
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from llm_engine_server.common.constants import DEFAULT_CELERY_TASK_NAME, LIRA_CELERY_TASK_NAME
from llm_engine_server.domain.entities.owned_entity import OwnedEntity
from pydantic import BaseModel, Field, root_validator
from typing_extensions import Literal


class ModelBundlePackagingType(str, Enum):
    """
    The canonical list of possible packaging types for Model Bundles.

    These values broadly determine how the model endpoint will obtain its code & dependencies.
    """

    CLOUDPICKLE = "cloudpickle"
    ZIP = "zip"


class ModelBundleFrameworkType(str, Enum):
    """
    The canonical list of possible machine learning frameworks of Model Bundles.
    """

    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    CUSTOM = "custom_base_image"


class ModelBundleEnvironmentParams(BaseModel):
    """
    This is the entity-layer class for the Model Bundle environment parameters. Being an
    entity-layer class, it should be a plain data object.
    """

    framework_type: ModelBundleFrameworkType
    pytorch_image_tag: Optional[str]  # for pytorch
    tensorflow_version: Optional[str]  # for tensorflow
    ecr_repo: Optional[str]  # for custom base image
    image_tag: Optional[str]  # for custom base image

    @root_validator
    @classmethod
    def validate_fields_present_for_framework_type(cls, field_values):
        """
        This pydantic root validator checks that fields are set according to the specified framework
        type.
        """
        assert field_values["framework_type"] in [
            ModelBundleFrameworkType.PYTORCH,
            ModelBundleFrameworkType.TENSORFLOW,
            ModelBundleFrameworkType.CUSTOM,
        ]
        if field_values["framework_type"] == ModelBundleFrameworkType.PYTORCH:
            assert field_values["pytorch_image_tag"], (
                "Expected `pytorch_image_tag` to be non-null because the Pytorch framework type "
                "was selected."
            )
        elif field_values["framework_type"] == ModelBundleFrameworkType.TENSORFLOW:
            assert field_values["tensorflow_version"], (
                "Expected `tensorflow_version` to be non-null because the Tensorflow framework"
                "type was selected."
            )
        else:  # field_values["framework_type"] == ModelBundleFramework.CUSTOM:
            assert field_values["ecr_repo"] and field_values["image_tag"], (
                "Expected `ecr_repo` and `image_tag` to be non-null because the custom framework "
                "type was selected."
            )
        return field_values

    class Config:
        """
        Model Bundle Environment Params Config class.
        """

        orm_mode = True


class PytorchFramework(BaseModel):
    """
    This is the entity-layer class for a Pytorch framework specification.
    """

    framework_type: Literal[ModelBundleFrameworkType.PYTORCH]
    pytorch_image_tag: str


class TensorflowFramework(BaseModel):
    """
    This is the entity-layer class for a Tensorflow framework specification.
    """

    framework_type: Literal[ModelBundleFrameworkType.TENSORFLOW]
    tensorflow_version: str


class CustomFramework(BaseModel):
    """
    This is the entity-layer class for a custom framework specification.
    """

    framework_type: Literal[ModelBundleFrameworkType.CUSTOM]
    image_repository: str
    image_tag: str


class ModelBundleFlavorType(str, Enum):
    """
    The canonical list of possible flavors of Model Bundles.
    """

    CLOUDPICKLE_ARTIFACT = "cloudpickle_artifact"
    ZIP_ARTIFACT = "zip_artifact"
    RUNNABLE_IMAGE = "runnable_image"
    STREAMING_ENHANCED_RUNNABLE_IMAGE = "streaming_enhanced_runnable_image"
    TRITON_ENHANCED_RUNNABLE_IMAGE = "triton_enhanced_runnable_image"


class ArtifactLike(BaseModel, ABC):
    """An abstract base for flavors that are related to bundles defined by artifacts."""

    requirements: List[str]
    framework: Union[PytorchFramework, TensorflowFramework, CustomFramework] = Field(
        ..., discriminator="framework_type"
    )
    app_config: Optional[Dict[str, Any]]
    location: str


class CloudpickleArtifactFlavor(ArtifactLike):
    """
    This is the entity-layer class for the Model Bundle flavor of a cloudpickle artifact.
    """

    flavor: Literal[ModelBundleFlavorType.CLOUDPICKLE_ARTIFACT]
    load_predict_fn: str
    load_model_fn: str


class ZipArtifactFlavor(ArtifactLike):
    """
    This is the entity-layer class for the Model Bundle flavor of a zip artifact.
    """

    flavor: Literal[ModelBundleFlavorType.ZIP_ARTIFACT]
    load_predict_fn_module_path: str
    load_model_fn_module_path: str


class RunnableImageLike(BaseModel, ABC):
    """An abstract base for flavors that are related to bundles defined by runnable images."""

    repository: str
    tag: str
    command: List[str]
    predict_route: str = "/predict"
    healthcheck_route: str = "/readyz"
    env: Optional[Dict[str, str]]
    protocol: Literal["http"]  # TODO: add support for other protocols (e.g. grpc)
    readiness_initial_delay_seconds: int = 120


class RunnableImageFlavor(RunnableImageLike):
    """
    This is the entity-layer class for the Model Bundle flavor of a runnable image.
    """

    flavor: Literal[ModelBundleFlavorType.RUNNABLE_IMAGE]


class TritonEnhancedRunnableImageFlavor(RunnableImageLike):
    """For deployments that require tritonserver running in a container."""

    flavor: Literal[ModelBundleFlavorType.TRITON_ENHANCED_RUNNABLE_IMAGE]
    triton_model_repository: str
    triton_model_replicas: Optional[Dict[str, int]]
    triton_num_cpu: float
    triton_commit_tag: str
    triton_storage: Optional[str]
    triton_memory: Optional[str]
    triton_readiness_initial_delay_seconds: int = 300  # will default to 300 seconds


class StreamingEnhancedRunnableImageFlavor(RunnableImageLike):
    """For deployments that expose a streaming route in a container."""

    flavor: Literal[ModelBundleFlavorType.STREAMING_ENHANCED_RUNNABLE_IMAGE]
    streaming_command: List[str]
    command: List[str] = []
    streaming_predict_route: str = "/stream"


ModelBundleFlavors = Union[
    CloudpickleArtifactFlavor,
    ZipArtifactFlavor,
    RunnableImageFlavor,
    StreamingEnhancedRunnableImageFlavor,
    TritonEnhancedRunnableImageFlavor,
]
"""Union type exhaustively representing all valid model bundle flavors.
"""


class ModelBundle(OwnedEntity):
    """
    This is the entity-layer class for the Model Bundle abstraction. Being an entity-layer class,
    it should be a plain data object.
    """

    id: str
    name: str
    created_by: str
    created_at: datetime.datetime
    metadata: Dict[str, Any]
    model_artifact_ids: List[str]
    schema_location: Optional[str]
    owner: str
    flavor: ModelBundleFlavors = Field(..., discriminator="flavor")

    # LEGACY FIELDS
    requirements: Optional[List[str]]  # FIXME: Delete
    location: Optional[str]  # FIXME: Delete
    env_params: Optional[ModelBundleEnvironmentParams]  # FIXME: Delete
    packaging_type: Optional[ModelBundlePackagingType]  # FIXME: Delete
    app_config: Optional[Dict[str, Any]]  # FIXME: Delete

    class Config:
        """
        Model Bundle Config class.
        """

        orm_mode = True

    def is_runnable(self) -> bool:
        """True iff the model bundle calls for it."""
        return isinstance(self.flavor, RunnableImageLike)

    def celery_task_name(self):
        return LIRA_CELERY_TASK_NAME if self.is_runnable() else DEFAULT_CELERY_TASK_NAME
