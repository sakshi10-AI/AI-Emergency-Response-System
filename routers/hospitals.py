"""
FastAPI Hospital Network & Capacity Router

Provides endpoints for querying hospital capacity, trauma levels, specialty departments,
reserving ICU beds, and updating live emergency department metrics.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/hospitals", tags=["Hospitals & Trauma Network"])

# In-memory hospital repository (initial state)
_HOSPITALS_DB: List[Dict[str, Any]] = [
    {
        "hospital_id": "HOSP-01",
        "name": "SF General Level I Trauma Center",
        "latitude": 37.7554,
        "longitude": -122.4055,
        "trauma_level": "Level I",
        "total_icu_beds": 40,
        "available_icu_beds": 6,
        "er_occupancy_percent": 85,
        "specialties": ["Trauma", "Burn", "Neuro", "Cardiac"],
        "distance_km": 2.4,
        "status": "OPEN"
    },
    {
        "hospital_id": "HOSP-02",
        "name": "St. Jude Medical Center",
        "latitude": 37.7850,
        "longitude": -122.4350,
        "trauma_level": "Level II",
        "total_icu_beds": 25,
        "available_icu_beds": 9,
        "er_occupancy_percent": 64,
        "specialties": ["Hazmat Decon", "Pediatric", "General Surgery"],
        "distance_km": 4.1,
        "status": "OPEN"
    },
    {
        "hospital_id": "HOSP-03",
        "name": "City Central Emergency Hospital",
        "latitude": 37.7700,
        "longitude": -122.4250,
        "trauma_level": "Level III",
        "total_icu_beds": 15,
        "available_icu_beds": 2,
        "er_occupancy_percent": 92,
        "specialties": ["Cardiology", "Orthopedics"],
        "distance_km": 1.8,
        "status": "BUSY"
    }
]


class CapacityUpdateRequest(BaseModel):
    available_icu_beds: Optional[int] = Field(None, ge=0)
    er_occupancy_percent: Optional[int] = Field(None, ge=0, le=100)


@router.get("/", response_model=List[Dict[str, Any]])
async def get_hospitals(
    specialty: Optional[str] = Query(None, description="Filter by medical specialty"),
    trauma_level: Optional[str] = Query(None, description="Filter by trauma level"),
    status: Optional[str] = Query(None, description="Filter by operational status")
):
    """Retrieves list of regional trauma centers with optional filters."""
    result = list(_HOSPITALS_DB)
    if specialty:
        result = [h for h in result if specialty.lower() in [s.lower() for s in h.get("specialties", [])]]
    if trauma_level:
        result = [h for h in result if h.get("trauma_level").lower() == trauma_level.lower()]
    if status:
        result = [h for h in result if h.get("status").lower() == status.lower()]
    return result


@router.get("/{hospital_id}", response_model=Dict[str, Any])
async def get_hospital_by_id(hospital_id: str):
    """Retrieves details of a specific hospital."""
    for h in _HOSPITALS_DB:
        if h["hospital_id"] == hospital_id:
            return h
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hospital '{hospital_id}' not found.")


@router.post("/{hospital_id}/reserve-bed", response_model=Dict[str, Any])
async def reserve_icu_bed(hospital_id: str):
    """Reserves one available ICU bed at the specified hospital."""
    for h in _HOSPITALS_DB:
        if h["hospital_id"] == hospital_id:
            if h["available_icu_beds"] <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No ICU beds available at this hospital.")
            h["available_icu_beds"] -= 1
            return {
                "status": "success",
                "message": f"Reserved ICU bed at {h['name']}.",
                "hospital_id": hospital_id,
                "available_icu_beds": h["available_icu_beds"]
            }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hospital '{hospital_id}' not found.")


@router.put("/{hospital_id}/capacity", response_model=Dict[str, Any])
async def update_hospital_capacity(hospital_id: str, req: CapacityUpdateRequest):
    """Updates live ICU bed availability or ER occupancy percentage."""
    for h in _HOSPITALS_DB:
        if h["hospital_id"] == hospital_id:
            if req.available_icu_beds is not None:
                h["available_icu_beds"] = req.available_icu_beds
            if req.er_occupancy_percent is not None:
                h["er_occupancy_percent"] = req.er_occupancy_percent
            return {"status": "success", "hospital": h}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hospital '{hospital_id}' not found.")


@router.get("/{hospital_id}/incoming-ambulances", response_model=List[Dict[str, Any]])
async def get_incoming_ambulances(hospital_id: str):
    """Retrieves pre-arrival ambulance notifications heading to target hospital."""
    return [
        {"unit": "AMB-101 (Medic 101)", "eta_minutes": 4.2, "condition": "Severe Burn & Trauma", "vitals": "BP 110/70, HR 115"},
        {"unit": "AMB-102 (Medic 102)", "eta_minutes": 6.0, "condition": "Chemical Inhalation", "vitals": "SpO2 91%, HR 98"},
    ]
