from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status,
    BackgroundTasks,
    Request,
)
import logging, os

from features.counsellor.dependency import get_counsellor_service
from features.counsellor.services import CounsellorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/counsellor", tags=["counsellor"])


@router.post(
    "/upload-audio",
    description="API endpoint to upload the audio in s3 and perform AI analysis.",
)
async def upload_audio_and_perform_ai_analysis(
    request: Request,
    call_recording: UploadFile = File(...),
    call_start: str = Form(...),
    call_end: str = Form(...),
    duration: str = Form(...),
    call_type: str = Form(...),
    client_number: str = Form(...),
    tags: str = Form(...),
    counsellor_id: str = Form(...),
    service: CounsellorService = Depends(get_counsellor_service),
):
    try:

        os.makedirs("temp", exist_ok=True)
        temp_path = os.path.join("temp", call_recording.filename)
        content = await call_recording.read()
        with open(temp_path, "wb") as buffer:
            buffer.write(content)
        logger.info("Successfully saved call recoding file in temp directory")

        return service.process_call_recording(
            request.app.state.s3_saver,
            temp_path,
            call_start,
            call_end,
            duration,
            call_type,
            client_number,
            tags,
            counsellor_id,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error occurred while processing audio, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process audio",
        )
