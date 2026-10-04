"""
Vision Analysis and Emergency Dispatch API Router

Exposes REST endpoints for Multimodal VLM image analysis, temporal video analysis,
and immediate automated hospital alerting to emergency trauma desks (target: 7796119389).
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, Depends, status, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from vision.service import vision_detection_service
from services.hospital_call_service import hospital_call_service
from utils.logger import app_logger


router = APIRouter(prefix="/api/v1/vision", tags=["Vision Analysis & Video Triage"])


class VisualDispatchCallRequest(BaseModel):
    incident_id: Optional[str] = Field(default=None, description="Optional associated incident UUID")
    latitude: float = Field(default=21.1458, description="Incident latitude (default Nagpur center)")
    longitude: float = Field(default=79.0882, description="Incident longitude (default Nagpur center)")
    incident_type: str = Field(default="ROAD_TRAFFIC_COLLISION", description="Detected emergency category")
    severity_score: int = Field(default=85, description="Visual severity index (0-100)")
    casualties_count: int = Field(default=2, description="Casualties detected in visual media")
    scene_summary: str = Field(default="Visual analysis confirmed vehicle collision with road obstruction.")
    target_override_phone: Optional[str] = Field(default="7796119389", description="Emergency call destination")


@router.post("/analyze-image", status_code=status.HTTP_200_OK, summary="Analyze Emergency Scene Image via Multimodal VLM")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    prompt_hint: Optional[str] = Form(None)
):
    """
    Ingests an emergency scene photo, performs Quality Gate checks,
    runs Multimodal VLM scene comprehension, and returns structured hazard telemetry
    along with an annotated base64 overlay image.
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        analysis, annotated_b64 = await vision_detection_service.analyze_image_vlm(
            image_source=content,
            prompt_hint=prompt_hint,
            draw_annotations=True
        )

        return {
            "status": "SUCCESS",
            "filename": file.filename,
            "analysis": analysis.model_dump(),
            "annotated_image_base64": annotated_b64
        }
    except Exception as e:
        app_logger.error(f"[VisionRouter] Image analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")


@router.post("/analyze-video", status_code=status.HTTP_200_OK, summary="Analyze Video Footage via Temporal Consistency Engine")
async def analyze_video_endpoint(
    file: UploadFile = File(...),
    sample_interval_sec: float = Form(1.0)
):
    """
    Ingests video footage, extracts keyframes across the duration, applies multi-frame
    persistence voting, and generates a timestamped breakdown of hazard developments.
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded video file is empty.")

        result = await vision_detection_service.analyze_video_temporal(
            video_input=content,
            sample_interval_sec=sample_interval_sec
        )

        return {
            "status": "SUCCESS",
            "filename": file.filename,
            "temporal_analysis": result.model_dump()
        }
    except Exception as e:
        app_logger.error(f"[VisionRouter] Video analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")


@router.post("/dispatch-hospital-call", status_code=status.HTTP_200_OK, summary="Trigger Emergency Hospital Call for Visual Hazard")
async def dispatch_hospital_call_from_vision(
    payload: VisualDispatchCallRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Immediately computes the nearest trauma center to the visual accident site
    and executes an automated emergency telephone alert to target phone 7796119389.
    """
    call_log = await hospital_call_service.dispatch_nearest_hospital_call(
        db=db,
        incident_id=payload.incident_id,
        accident_lat=payload.latitude,
        accident_lon=payload.longitude,
        incident_type=payload.incident_type,
        severity_score=payload.severity_score,
        casualties=payload.casualties_count,
        summary=payload.scene_summary,
        target_phone_override=payload.target_override_phone or "7796119389"
    )

    hosp_name = getattr(call_log, "cached_hospital_name", "Government Medical College & Hospital (GMCH) Nagpur")
    return {
        "status": "DISPATCHED",
        "call_id": str(call_log.id),
        "target_phone": call_log.target_phone,
        "nearest_hospital_name": hosp_name,
        "distance_km": call_log.distance_km,
        "eta_minutes": call_log.eta_minutes,
        "call_status": call_log.status,
        "speech_transcript": call_log.speech_transcript
    }
