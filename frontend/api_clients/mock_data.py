"""
Shared Mock Data Store — Nagpur, Maharashtra, India

Provides resilient mock data used by all API Service Clients as an offline fallback
when the FastAPI backend is unreachable. This ensures zero UI crashes in disconnected mode.

Location: Nagpur, Maharashtra, India (21.1458° N, 79.0882° E)
"""

from typing import List, Dict, Any

# ============================================================================
# Mock Incidents — Nagpur City
# ============================================================================
MOCK_INCIDENTS: List[Dict[str, Any]] = [
    {
        "incident_id": "INC-8821",
        "tracking_code": "TRK-8821",
        "title": "Major Road Collision & Vehicle Fire on Wardha Road",
        "severity_level": 1,
        "priority_category": "CRITICAL",
        "status": "DISPATCHED",
        "latitude": 21.1285,
        "longitude": 79.0685,
        "address": "Wardha Road near Ajni Square, Nagpur",
        "description": "Multi-vehicle collision involving 3 cars and 1 petrol tanker. Active flame reported near fuel tank.",
        "victims_count": 4,
        "assigned_ambulance": "AMB-101 (ALS Unit)",
        "assigned_hospital": "GMCH Nagpur Level I Trauma",
        "eta_minutes": 4.2,
        "timestamp": "10:12:05"
    },
    {
        "incident_id": "INC-8822",
        "tracking_code": "TRK-8822",
        "title": "Industrial Chemical Spill at Butibori MIDC",
        "severity_level": 2,
        "priority_category": "URGENT",
        "status": "ANALYZING",
        "latitude": 21.0602,
        "longitude": 79.0182,
        "address": "Plot No. 45, Butibori MIDC, Nagpur",
        "description": "Ammonia storage tank leak detected at chemical plant. 2 workers reporting respiratory distress.",
        "victims_count": 2,
        "assigned_ambulance": "AMB-102 (Hazmat Unit)",
        "assigned_hospital": "Wockhardt Hospital Nagpur",
        "eta_minutes": 6.0,
        "timestamp": "10:08:40"
    },
    {
        "incident_id": "INC-8823",
        "tracking_code": "TRK-8823",
        "title": "Pedestrian Struck by Vehicle at Sitabuldi Crossing",
        "severity_level": 2,
        "priority_category": "URGENT",
        "status": "EN_ROUTE",
        "latitude": 21.1504,
        "longitude": 79.0849,
        "address": "Sitabuldi Main Road & Central Avenue, Nagpur",
        "description": "Pedestrian struck at zebra crossing. Patient conscious with suspected leg fracture.",
        "victims_count": 1,
        "assigned_ambulance": "AMB-103 (BLS Unit)",
        "assigned_hospital": "Orange City Hospital Nagpur",
        "eta_minutes": 3.1,
        "timestamp": "10:05:12"
    },
    {
        "incident_id": "INC-8824",
        "tracking_code": "TRK-8824",
        "title": "Residential Fire Alarm — Dharampeth Colony",
        "severity_level": 4,
        "priority_category": "MINOR",
        "status": "COMPLETED",
        "latitude": 21.1390,
        "longitude": 79.0720,
        "address": "Plot 12, Dhantoli Park Road, Nagpur",
        "description": "Kitchen smoke triggered alarm in residential building. False alarm confirmed by Fire Station No. 3.",
        "victims_count": 0,
        "assigned_ambulance": "None",
        "assigned_hospital": "None",
        "eta_minutes": 0.0,
        "timestamp": "09:45:00"
    }
]

# ============================================================================
# Mock Hospitals — Nagpur City
# ============================================================================
MOCK_HOSPITALS: List[Dict[str, Any]] = [
    {
        "hospital_id": "HOSP-01",
        "name": "Government Medical College & Hospital (GMCH) Nagpur",
        "emergency_phone": "7796119389",
        "latitude": 21.1367,
        "longitude": 79.0995,
        "trauma_level": "Level I",
        "total_icu_beds": 60,
        "available_icu_beds": 8,
        "er_occupancy_percent": 82,
        "specialties": ["Trauma", "Burns", "Neurology", "Cardiac", "Pediatrics"],
        "distance_km": 2.4,
        "status": "OPEN"
    },
    {
        "hospital_id": "HOSP-02",
        "name": "Wockhardt Hospital Nagpur",
        "emergency_phone": "7796119389",
        "latitude": 21.1571,
        "longitude": 79.0888,
        "trauma_level": "Level II",
        "total_icu_beds": 30,
        "available_icu_beds": 10,
        "er_occupancy_percent": 61,
        "specialties": ["Hazmat Decontamination", "Orthopedics", "Cardiology", "General Surgery"],
        "distance_km": 4.1,
        "status": "OPEN"
    },
    {
        "hospital_id": "HOSP-03",
        "name": "Orange City Hospital & Research Institute",
        "emergency_phone": "7796119389",
        "latitude": 21.1270,
        "longitude": 79.0632,
        "trauma_level": "Level II",
        "total_icu_beds": 20,
        "available_icu_beds": 3,
        "er_occupancy_percent": 89,
        "specialties": ["Cardiology", "Orthopedics", "Oncology"],
        "distance_km": 1.8,
        "status": "BUSY"
    },
    {
        "hospital_id": "HOSP-04",
        "name": "Lata Mangeshkar Hospital Nagpur",
        "emergency_phone": "7796119389",
        "latitude": 21.1475,
        "longitude": 79.1050,
        "trauma_level": "Level II",
        "total_icu_beds": 25,
        "available_icu_beds": 7,
        "er_occupancy_percent": 70,
        "specialties": ["Cardiac Surgery", "Neurosurgery", "Critical Care"],
        "distance_km": 3.5,
        "status": "OPEN"
    }
]

# ============================================================================
# Mock Ambulances — Nagpur EMS Fleet
# ============================================================================
MOCK_AMBULANCES: List[Dict[str, Any]] = [
    {
        "unit_id": "AMB-101",
        "call_sign": "Nagpur Medic 101",
        "unit_type": "ALS (Advanced Life Support)",
        "status": "DISPATCHED",
        "latitude": 21.1320,
        "longitude": 79.0750,
        "fuel_level_percent": 88,
        "equipment": ["Defibrillator", "Ventilator", "Trauma Kit", "Cardiac Monitor"],
        "assigned_incident": "INC-8821",
        "eta_minutes": 4.2
    },
    {
        "unit_id": "AMB-102",
        "call_sign": "Nagpur Medic 102",
        "unit_type": "Hazmat Response",
        "status": "DISPATCHED",
        "latitude": 21.0700,
        "longitude": 79.0250,
        "fuel_level_percent": 95,
        "equipment": ["SCBA Masks", "Decon Shower", "Antidotes", "Chemical Sensors"],
        "assigned_incident": "INC-8822",
        "eta_minutes": 6.0
    },
    {
        "unit_id": "AMB-103",
        "call_sign": "Nagpur Medic 103",
        "unit_type": "BLS (Basic Life Support)",
        "status": "EN_ROUTE",
        "latitude": 21.1480,
        "longitude": 79.0830,
        "fuel_level_percent": 74,
        "equipment": ["AED", "Oxygen Cylinder", "Splints", "First Aid Kit"],
        "assigned_incident": "INC-8823",
        "eta_minutes": 3.1
    },
    {
        "unit_id": "HELI-01",
        "call_sign": "NMC Air Rescue 1",
        "unit_type": "Air Ambulance",
        "status": "AVAILABLE",
        "latitude": 21.1001,
        "longitude": 79.0472,
        "fuel_level_percent": 100,
        "equipment": ["Surgical Suite", "Blood Supply", "Advanced ICU", "Neonatal Support"],
        "assigned_incident": "None",
        "eta_minutes": 0.0
    }
]

# ============================================================================
# Mock Camera Streams — Nagpur Traffic & CCTV Network
# ============================================================================
MOCK_CAMERA_STREAMS = [
    {"cam_id": "CAM-101", "location": "Wardha Road & Ajni Square, Nagpur", "status": "ALERT", "hazards_detected": ["Vehicle Fire", "Traffic Congestion"]},
    {"cam_id": "CAM-102", "location": "Butibori MIDC Gate No. 2, Nagpur", "status": "WARNING", "hazards_detected": ["Vapor Cloud", "Worker Hazard"]},
    {"cam_id": "CAM-103", "location": "Sitabuldi Flyover & Central Avenue", "status": "ONLINE", "hazards_detected": ["None"]},
    {"cam_id": "CAM-104", "location": "Dharampeth Colony & Amravati Road Junction", "status": "ONLINE", "hazards_detected": ["None"]}
]

# ============================================================================
# Mock Notifications — Nagpur EOC
# ============================================================================
MOCK_NOTIFICATIONS = [
    {"id": "NOTIF-001", "type": "DISPATCH", "message": "AMB-101 dispatched to INC-8821 (Wardha Road)", "priority": "HIGH", "timestamp": "10:12:15"},
    {"id": "NOTIF-002", "type": "HOSPITAL_ALERT", "message": "GMCH Nagpur ICU capacity at 82% — Rerouting advised", "priority": "MEDIUM", "timestamp": "10:10:30"},
    {"id": "NOTIF-003", "type": "PUBLIC_SMS", "message": "Traffic alert: Wardha Road near Ajni Square blocked. Avoid area.", "priority": "LOW", "timestamp": "10:08:00"},
]
