from pydantic import BaseModel

from features.auditor.schemas import BaseResponse


class CallRecordingProcessingSchema(BaseResponse):
    call_id: str
    status: str
