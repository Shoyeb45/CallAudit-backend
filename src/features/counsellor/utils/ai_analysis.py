import os
from pathlib import Path
from typing import Dict, List
from elevenlabs.client import ElevenLabs
from openai import AzureOpenAI
from config import get_llm_config

llm_config = get_llm_config()


class ElevenLabsSpeechService:
    """ElevenLabs Speech-to-Text service wrapper"""

    def __init__(self):

        self.client = ElevenLabs(api_key=llm_config.elevenlabs_api_key)

    def transcribe_audio(self, audio_path: Path, language_code: str = "en") -> Dict:
        try:
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()

            transcription = self.client.speech_to_text.convert(
                file=audio_data,
                model_id="scribe_v1",
                tag_audio_events=True,
                language_code=language_code if language_code != "hi-IN" else "en",
                diarize=True,
            )

            return self._process_transcription_response(transcription)

        except Exception as e:
            raise Exception(f"ElevenLabs transcription failed: {str(e)}")

    def _process_transcription_response(self, transcription) -> Dict:
        result = {
            "full_transcript": "",
            "segments": [],
            "speakers": {},
            "word_timings": [],
            "confidence_scores": [],
        }

        if hasattr(transcription, "text"):
            result["full_transcript"] = transcription.text
        elif hasattr(transcription, "transcript"):
            result["full_transcript"] = transcription.transcript
        else:
            result["full_transcript"] = str(transcription)

        if hasattr(transcription, "segments") and transcription.segments:
            for i, segment in enumerate(transcription.segments):
                segment_data = {
                    "start_time": getattr(segment, "start_time", i * 5.0),
                    "end_time": getattr(segment, "end_time", (i + 1) * 5.0),
                    "text": getattr(segment, "text", ""),
                    "speaker": getattr(segment, "speaker", f"Speaker {i % 2}"),
                    "confidence": getattr(segment, "confidence", 0.9),
                }
                segment_data["duration"] = (
                    segment_data["end_time"] - segment_data["start_time"]
                )
                result["segments"].append(segment_data)

        if not result["segments"] and result["full_transcript"]:
            words = result["full_transcript"].split()
            words_per_segment = 20
            for i in range(0, len(words), words_per_segment):
                segment_words = words[i : i + words_per_segment]
                segment_text = " ".join(segment_words)
                segment_data = {
                    "start_time": i * 0.5,
                    "end_time": (i + len(segment_words)) * 0.5,
                    "text": segment_text,
                    "speaker": f"Speaker {i // words_per_segment % 2}",
                    "confidence": 0.9,
                    "duration": len(segment_words) * 0.5,
                }
                result["segments"].append(segment_data)

        if result["segments"]:
            result["speakers"] = self._extract_speaker_segments(result["segments"])

        if result["segments"]:
            confidences = [seg["confidence"] for seg in result["segments"]]
            result["overall_confidence"] = sum(confidences) / len(confidences)
        else:
            result["overall_confidence"] = 0.9

        return result

    def _extract_speaker_segments(self, segments: List[Dict]) -> Dict:
        speakers = {}
        for segment in segments:
            speaker_id = segment["speaker"]
            if speaker_id not in speakers:
                speakers[speaker_id] = {
                    "words": [],
                    "total_duration": 0,
                    "word_count": 0,
                    "confidence_scores": [],
                    "text": "",
                    "avg_confidence": 0.0,
                }

            speaker_data = speakers[speaker_id]
            if segment["text"]:
                speaker_data["text"] += " " + segment["text"]
                speaker_data["word_count"] += len(segment["text"].split())
                speaker_data["total_duration"] += segment["duration"]
                speaker_data["confidence_scores"].append(segment["confidence"])

        for speaker_id, data in speakers.items():
            if data["confidence_scores"]:
                data["avg_confidence"] = sum(data["confidence_scores"]) / len(
                    data["confidence_scores"]
                )
            data["text"] = data["text"].strip()

        return speakers

    def get_supported_languages(self) -> List[str]:
        return [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "tr",
            "ru",
            "nl",
            "cs",
            "ar",
            "zh",
            "ja",
            "hu",
            "ko",
            "hi",
        ]


class AzureOpenAIService:
    def __init__(self):
        try:
            self.client = AzureOpenAI(
                azure_endpoint=llm_config.azure_openai_endpoint,
                api_key=llm_config.azure_openai_api_key,
                api_version=llm_config.azure_openai_api_version,
            )
            self.deployment = llm_config.azure_openai_deployment
        except Exception as e:
            print(f"Warning: Could not initialize Azure OpenAI client: {str(e)}")
            self.client = None
            self.deployment = None

    def analyze_conversation(self, transcript: str, speakers_data: Dict) -> Dict:
        try:
            if self.client is None:
                return {"analysis": "Azure OpenAI service not available", "usage": None}
            system_prompt = (
                "You are an expert conversation analyst. Analyze the provided conversation transcript and provide "
                "comprehensive insights including: 1. Overall conversation summary 2. Key topics discussed 3. Emotional "
                "journey and tone changes 4. Communication patterns 5. Conflict resolution or tension points 6. "
                "Decision-making moments 7. Relationship dynamics 8. Important insights and recommendations"
            )
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Transcript:\n{transcript}\n\nSpeaker Info:\n{self._format_speaker_info(speakers_data)}",
                    },
                ],
                max_tokens=1500,
                temperature=0.3,
            )
            return {
                "analysis": response.choices[0].message.content,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as e:
            return {"analysis": f"Analysis failed: {str(e)}", "usage": None}

    def generate_conversation_summary(
        self, transcript: str, speakers_data: Dict
    ) -> Dict:
        try:
            system_prompt = (
                "Create a concise but comprehensive summary of this conversation including: "
                "1. Main topics discussed 2. Key decisions made 3. Action items or next steps "
                "4. Overall tone and outcome 5. Important quotes or statements"
            )
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Summarize this conversation:\n{transcript}",
                    },
                ],
                max_tokens=800,
                temperature=0.3,
            )
            return {
                "summary": response.choices[0].message.content,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as e:
            return {"summary": f"Summary generation failed: {str(e)}", "usage": None}

    def _format_speaker_info(self, speakers_data: Dict) -> str:
        formatted = []
        for speaker_tag, data in speakers_data.items():
            formatted.append(f"Speaker {speaker_tag}:")
            formatted.append(f"  - Total words: {data.get('word_count', 0)}")
            formatted.append(
                f"  - Speaking time: {data.get('total_duration', 0):.2f} seconds"
            )
            formatted.append(
                f"  - Average confidence: {data.get('avg_confidence', 0):.2f}\n"
            )
        return "\n".join(formatted)
