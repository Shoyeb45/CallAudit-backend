from models import Call, CallAnalysis, Counsellor
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class CounsellorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_call(self, call_data: dict) -> str:
        """Create a new call record"""
        try:
            logger.info("Adding call in database")

            counsellor = (
                self.db.query(Counsellor)
                .filter(Counsellor.id == call_data["counsellor_id"])
                .first()
            )

            if not counsellor:
                logger.error(f"Counsellor not found: {call_data['counsellor_id']}")
                return None

            # Automatically set auditor_id and manager_id
            call_data["auditor_id"] = counsellor.auditor_id
            call_data["manager_id"] = counsellor.manager_id

            call = Call(**call_data)
            self.db.add(call)
            self.db.commit()
            self.db.refresh(call)
            logger.info("Succesfully added call in database")
            return call.id
        except Exception as e:
            logger.error(f"Failed to create call record in database, error: {str(e)}")
            return None

    def update_call_recording_url(self, call_id: str, recording_url: str):
        """Update call with S3 recording URL"""
        try:
            logger.info("Updating call recording audio..")
            call = self.db.query(Call).filter(Call.id == call_id).first()
            if call:
                call.recording_url = recording_url
                self.db.commit()
            logger.info("Succesfully updated call")
        except Exception as e:
            logger.error("Failed to update call url")
            raise e

    def save_call_analysis(self, call_id: str, ai_results: dict):
        """Save AI analysis results"""
        try:
            analysis = CallAnalysis(
                call_id=call_id,
                sentiment_score=ai_results.get("sentiment_score", 0.0),
                transcript=ai_results.get("transcript"),
                summary=ai_results.get("summary"),
                anomalies=ai_results.get("anomalies"),
                keywords=ai_results.get("keywords", ""),
                ai_confidence=ai_results.get("ai_confidence", 0.0),
            )
            self.db.add(analysis)
            self.db.commit()
        except Exception as e:
            logger.error("Failed to update AI analysis in database")
            raise e
