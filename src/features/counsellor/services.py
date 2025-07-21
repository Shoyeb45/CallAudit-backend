from typing import Any, Dict
from core.save_to_s3 import S3Saver
from features.counsellor.repository import CounsellorRepository
from fastapi import BackgroundTasks, HTTPException, status
from datetime import datetime
import logging, os
from threading import Thread
from functools import wraps
import time
from features.counsellor.schemas import CallRecordingProcessingSchema
from features.counsellor.utils.ai_analysis import (
    AzureOpenAIService,
    ElevenLabsSpeechService,
)

logger = logging.getLogger(__name__)


def retry(max_attempts=3, delay=60):
    """Decorator for retry logic"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == max_attempts - 1:
                        raise e
                    time.sleep(delay)
            return None

        return wrapper

    return decorator


class CounsellorService:
    def __init__(self, repo: CounsellorRepository):
        self.repo = repo

    def process_call_recording(
        self,
        s3_saver: S3Saver,
        audio_path: str,
        call_start: str,
        call_end: str,
        duration: str,
        call_type: str,
        client_number: str,
        tags: str,
        counsellor_id: str,
    ):
        try:
            logger.info("Processing call recording and adding the call in database")
            call_data = {
                "counsellor_id": counsellor_id,
                "call_start": datetime.fromisoformat(call_start),
                "call_end": datetime.fromisoformat(call_end),
                "duration": int(duration),
                "call_type": call_type,
                "client_number": client_number,
                "tags": tags,
            }

            call_id = self.repo.create_call(call_data)

            if not call_id:
                logger.error("call_id is none")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while saving the call in database, please try again",
                )

            # Add background task
            thread = Thread(
                target=self.process_audio_background,
                args=(s3_saver, call_id, audio_path),
                daemon=True,
                name="AudioProcessor",
            )

            logger.info("Starting thread for call analysis")
            thread.start()

            return CallRecordingProcessingSchema(
                success=True,
                message="Call recording uploaded successfully",
                call_id=call_id,
                status="processing",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to process call recording, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while processing audio.",
            )

    @retry(max_attempts=5)
    def process_audio_background(
        self, s3_saver: S3Saver, call_id: str, audio_path: str
    ):
        """Background processing function"""
        try:
            # Step 1: Upload to S3
            s3_url = self.upload_to_s3(s3_saver, audio_path, call_id)

            # Step 2: Update database with S3 URL
            self.repo.update_call_recording_url(call_id, s3_url)

            # Step 3: Perform AI analysis
            ai_results = self.perform_ai_analysis(audio_path)

            # Step 4: Save AI analysis results
            self.repo.save_call_analysis(call_id, ai_results)

            # Step 5: Clean up temp file
            if os.path.exists(audio_path):
                os.remove(audio_path)

            logger.info(f"Successfully processed audio for call {call_id}")

        except Exception as e:
            logger.error(f"Failed to process audio for call {call_id}: {e}")
            raise e

    def upload_to_s3(self, s3_saver: S3Saver, audio_path: str, call_id: str):
        try:
            logger.info("Uploading audio in s3.")
            audio_url = s3_saver.upload_audio_to_s3(audio_path)
            logger.info("Succesfully uploaded audio in S3.")
            return audio_url
        except Exception as e:
            logger.info(f"Failed to upload audio file in S3, error: {str(e)}")
            raise e

    def perform_ai_analysis(self, audio_path: str) -> Dict[str, Any]:
        try:
            logger.info("Performing AI analysis for audio")
            speech_service = ElevenLabsSpeechService()
            logger.info("Extracting transcription from audio")
            transcription_result = speech_service.transcribe_audio(audio_path)
            logger.info("Succesfully transcripted from audio")

            speaker_analysis = {
                "Speaker_0": {
                    "text": transcription_result["full_transcript"],
                    "word_count": len(transcription_result["full_transcript"].split()),
                    "total_duration": 60.0,  # you can keep rough estimate
                    "avg_confidence": 0.95,
                }
            }

            azure_service = AzureOpenAIService()

            logger.info("Analyzing conversation")
            analysis_result = azure_service.analyze_conversation(
                transcript=transcription_result["full_transcript"],
                speakers_data=speaker_analysis,
            )
            logger.info("Succesfully anlayzed conversation")

            logger.info("Generating summary")
            summary_result = azure_service.generate_conversation_summary(
                transcript=transcription_result["full_transcript"],
                speakers_data=speaker_analysis,
            )
            logger.info("Succesfully generated summary")

            logger.info("Getting sentiment score")
            sentiment_score = azure_service.get_customer_sentiment_score(
                transcription_result["full_transcript"]
            )
            logger.info("Succesfully generated sentiment score")

            logger.info("Getting anomalies")
            anomalies = azure_service.detect_anomalies(
                transcription_result["full_transcript"]
            )
            logger.info("Succesfully generated anomalies")

            logger.info("Extracting keywords")
            keywords = azure_service.extract_keywords(
                transcription_result["full_transcript"]
            )
            logger.info("Succesfully extracted keywords")

            logger.info("Getting ai confidence score")
            confidence = azure_service.estimate_ai_confidence(
                analysis_result.get("usage", {})
            )
            logger.info("Succesfully got ai confidence score")

            return {
                "sentiment_score": sentiment_score,
                "transcript": transcription_result["full_transcript"].strip(),
                "summary": summary_result["summary"].strip(),
                "anomalies": anomalies,
                "keywords": keywords,
                "ai_confidence": confidence,
            }
        except Exception as e:
            logger.error(f"Failed to perform AI analysis on audio, error: {str(e)}")
            raise e
