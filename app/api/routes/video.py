import tempfile
import os

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(tags=["Video"])

# Pixels with all channels below this value are considered "black".
BLACK_THRESHOLD = 10
# If the fraction of black pixels exceeds this ratio the frame is black.
BLACK_RATIO_THRESHOLD = 0.99


@router.post(
    "/api/v1/video/check-black-frame",
    summary="Check whether a video's first frame is black",
    description=(
        "Accepts a video file upload, extracts the first frame, and returns "
        "whether that frame is (almost entirely) black."
    ),
)
async def check_black_frame(file: UploadFile = File(...)):
    """
    Returns ``{"black": true}`` when the first frame of the uploaded video is
    considered black (i.e. >= 99% of pixels have all channel values <= 10),
    and ``{"black": false}`` otherwise.
    """
    # Write the upload to a temp file so OpenCV can open it by path.
    suffix = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=422, detail="Could not open the video file.")

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            raise HTTPException(status_code=422, detail="Could not read the first frame of the video.")

        # Convert to grayscale for a straightforward black-pixel check.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        total_pixels = gray.size
        black_pixels = int(np.sum(gray <= BLACK_THRESHOLD))
        black_ratio = black_pixels / total_pixels

        return {"black": black_ratio >= BLACK_RATIO_THRESHOLD}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
