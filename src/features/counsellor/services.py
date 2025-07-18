from features.counsellor.repository import CounsellorRepository


class CounsellorService:
    def __init__(self, repo: CounsellorRepository):
        self.repo = repo

    def process_call_recording(
        self,
        audio_path: str,
        call_start: str,
        call_end: str,
        duration: str,
        call_type: str,
        client_number: str,
        tags: str,
        counsellor_id: str,
    ):
        
        # upload the file to s3
        # update the database with call details
        # Perform ai analysis
        # Update the ai reports
        pass
