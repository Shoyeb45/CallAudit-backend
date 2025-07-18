from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/counsellor", tags=["counsellor"])


@router.post(
    "/upload-audio",
    description="API endpoint to upload the audio in s3 and perform AI analysis.",
)
def upload_audio_and_perform_ai_analysis():
    pass
