"""Pipeline operation endpoints."""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from api.schemas import PipelineRunRequest, PipelineRunResponse
from api.services.pipeline import check_quality, run_stage

router = APIRouter(prefix="/api/v1", tags=["operations"])


@router.get("/quality")
def quality() -> dict[str, Any]:
    try:
        return check_quality()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Quality check failed: {exc}") from exc


@router.post("/pipeline/run", response_model=PipelineRunResponse)
def pipeline_run(request: PipelineRunRequest) -> PipelineRunResponse:
    started = datetime.now(timezone.utc)
    try:
        run_stage(request.stage)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Pipeline {request.stage.value} failed: {exc}"
        ) from exc
    return PipelineRunResponse(
        stage=request.stage,
        status="completed",
        started_at=started,
        completed_at=datetime.now(timezone.utc),
    )
