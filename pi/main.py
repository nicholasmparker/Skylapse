"""
Skylapse Pi - Simple Capture Server

ONE JOB: Take photos when commanded to by the backend.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="Skylapse Capture")


class CaptureSettings(BaseModel):
    """Camera settings for a single capture"""
    iso: int
    shutter_speed: str  # e.g., "1/1000"
    exposure_compensation: float  # e.g., +0.7


class CaptureResponse(BaseModel):
    """Response from a capture request"""
    status: str
    image_path: Optional[str] = None
    message: Optional[str] = None


@app.post("/capture", response_model=CaptureResponse)
async def capture_photo(settings: CaptureSettings):
    """
    Capture a single photo with the provided settings.

    Backend tells us EXACTLY what settings to use.
    We just execute and return the result.
    """
    try:
        # TODO: Implement actual camera capture
        # For now, just log what we would do
        print(f"📸 Capturing with ISO {settings.iso}, shutter {settings.shutter_speed}, EV {settings.exposure_compensation}")

        return CaptureResponse(
            status="success",
            image_path="/tmp/test_image.jpg",
            message="Capture successful (mock)"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Report camera status to backend"""
    return {
        "status": "online",
        "camera_model": "Mock Camera",
        "available": True
    }


@app.get("/health")
async def health_check():
    """Simple health check for monitoring"""
    return {"status": "ok"}


if __name__ == "__main__":
    # Run on all interfaces so backend can reach us
    uvicorn.run(app, host="0.0.0.0", port=8080)
