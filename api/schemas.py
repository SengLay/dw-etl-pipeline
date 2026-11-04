"""Request and response models used by the API."""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class Layer(str, Enum):
    staging = "staging"
    dwh = "dwh"
    dmart = "dmart"


class PipelineStage(str, Enum):
    raw = "raw"
    extract = "extract"
    transform = "transform"
    datamart = "datamart"
    all = "all"


class PipelineRunRequest(BaseModel):
    stage: PipelineStage = PipelineStage.all


class PipelineRunResponse(BaseModel):
    stage: PipelineStage
    status: str
    started_at: datetime
    completed_at: datetime


class TableRowsResponse(BaseModel):
    layer: str
    table: str
    items: list[dict[str, Any]]
    limit: int
    offset: int
    total: int
