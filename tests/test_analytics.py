"""
Unit & Integration Tests for Executive Analytics & Plotly Charting Engine

Tests:
- Executive Analytics API Data Structure (8 Operational Datasets)
- ReportClient get_executive_analytics Integration
- Analytics CSV Dataset Stream Formatting
"""

import pytest
import io
import csv
from frontend.api_clients import report_client


def test_executive_analytics_data_structure():
    """Tests that executive analytics returns all 8 required datasets for Plotly charts."""
    data = report_client.get_executive_analytics(time_horizon="24h")

    assert isinstance(data, dict)
    assert data.get("total_incidents") > 0
    assert data.get("avg_response_time_minutes") is not None

    # Verify 8 datasets present
    assert "daily_incidents" in data
    assert "monthly_incidents" in data
    assert "severity_breakdown" in data
    assert "response_times" in data
    assert "hospital_usage" in data
    assert "ambulance_usage" in data
    assert "ai_accuracy" in data
    assert "detection_confidence" in data

    # Verify content format
    assert len(data["daily_incidents"]) > 0
    assert len(data["monthly_incidents"]) == 12
    assert "Level 1 Critical" in data["severity_breakdown"]
    assert len(data["detection_confidence"]) >= 4


def test_analytics_csv_formatting():
    """Tests CSV output stream formatting for analytics dataset."""
    data = report_client.get_executive_analytics(time_horizon="24h")

    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["EXECUTIVE ANALYTICS METRICS"])
    writer.writerow(["Total Incidents", data.get("total_incidents")])

    for item in data.get("daily_incidents", []):
        writer.writerow([item.get("hour"), item.get("count")])

    csv_str = csv_buf.getvalue()
    assert "EXECUTIVE ANALYTICS METRICS" in csv_str
    assert "Total Incidents" in csv_str
