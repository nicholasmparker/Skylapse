"""
Skylapse Backend - The Brain

Responsibilities:
1. Store schedules (hardcoded for now)
2. Calculate sunrise/sunset times
3. Determine when to capture
4. Calculate optimal camera settings
5. Send capture commands to Pi
6. Process and stack images
"""

from fastapi import FastAPI
import uvicorn
from datetime import datetime
import asyncio

app = FastAPI(title="Skylapse Backend")


# Hardcoded schedules (simple!)
SCHEDULES = {
    "sunrise": {
        "type": "solar",
        "offset_minutes": -30,  # Start 30min before sunrise
        "duration_minutes": 60,  # Capture for 1 hour
        "interval_seconds": 30,  # Every 30 seconds
    },
    "daytime": {
        "type": "time_of_day",
        "start_time": "09:00",
        "end_time": "15:00",
        "interval_seconds": 300,  # Every 5 minutes
    },
    "sunset": {
        "type": "solar",
        "offset_minutes": -30,  # Start 30min before sunset
        "duration_minutes": 60,
        "interval_seconds": 30,
    }
}


@app.get("/")
async def root():
    return {
        "app": "Skylapse Backend",
        "schedules": list(SCHEDULES.keys()),
        "status": "running"
    }


@app.get("/schedules")
async def get_schedules():
    """Return all schedules"""
    return SCHEDULES


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# TODO: Add scheduler loop
# TODO: Add exposure calculator
# TODO: Add Pi communication
# TODO: Add image processing


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)