import os
import json
import whisper
import speech_recognition as sr
from pydub import AudioSegment
from tempfile import NamedTemporaryFile
from datetime import datetime
from flask import current_app
from threading import Lock
from pyannote.audio import Pipeline

class TranscriptGenerator:
    def __init__(self, app=None):
        self.app = app
        self.model = None
        self.model_lock = Lock()
        self.recognizer = sr.Recognizer()
        self.speaker_detector = None
        self.speaker_profiles = None
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        # Load models on first use
        self.model = None
        self.speaker_detector = None
        
        # Initialize speaker profiles
        from .speaker_profiles import SpeakerProfiles
        self.speaker_profiles = SpeakerProfiles(app)

    def _ensure_models_loaded(self):
        if self.model is None:
            with self.model_lock:
                if self.model is None:  # Double-check pattern
                    self.model = whisper.load_model("base")
                    # Initialize speaker diarization model
                    self.speaker_detector = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization",
                        use_auth_token=self.app.config.get('HUGGINGFACE_TOKEN')
                    )

    def _map_speakers_to_segments(self, diarization, segments):
        """Map speaker labels to transcript segments with speaker identification"""
        speaker_map = {}
        audio_cache = {}
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            start_time = turn.start
            end_time = turn.end
            
            # Try to identify speaker if not already mapped
            if speaker not in speaker_map:
                # Extract audio segment for speaker identification
                if speaker not in audio_cache:
                    audio_cache[speaker] = self._extract_speaker_audio(
                        turn.start,
                        turn.end
                    )
                
                # Identify speaker
                if self.speaker_profiles:
                    identification = self.speaker_profiles.identify_speaker(
                        audio_cache[speaker]
                    )
                    
                    if identification:
                        speaker_map[speaker] = identification["name"]
                    else:
                        speaker_map[speaker] = f"Speaker {len(speaker_map) + 1}"
                else:
                    speaker_map[speaker] = f"Speaker {len(speaker_map) + 1}"
            
            # Assign speakers to segments that overlap with this turn
            for segment in segments:
                seg_start = segment["start"]
                seg_end = segment["end"]
                
                # Check for overlap
                if (seg_start <= end_time and seg_end >= start_time):
                    segment["speaker"] = speaker_map[speaker]
                    if speaker in audio_cache:
                        segment["speaker_confidence"] = audio_cache[speaker].get(
                            "confidence",
                            1.0 if speaker_map[speaker].startswith("Speaker ") else 0.0
                        )
        
        return segments

    def _extract_speaker_audio(self, start_time, end_time):
        """Extract audio segment for speaker identification"""
        try:
            # Get audio segment
            audio = AudioSegment.from_file(self.current_audio_path)
            segment = audio[
                int(start_time * 1000):int(end_time * 1000)
            ]
            return segment
        except Exception as e:
            current_app.logger.error(
                f"Failed to extract speaker audio: {str(e)}"
            )
            return None

    def generate_transcript(self, audio_path, language="en", detect_speakers=True):
        """Generate transcript from audio file with speaker identification"""
        try:
            self._ensure_models_loaded()
            
            # Store audio path for speaker extraction
            self.current_audio_path = audio_path
            
            # Convert audio to WAV if needed
            audio = AudioSegment.from_file(audio_path)
            
            with NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                audio.export(temp_wav.name, format='wav')
                
                # Generate transcript using Whisper
                result = self.model.transcribe(
                    temp_wav.name,
                    language=language,
                    word_timestamps=True
                )
                
                if detect_speakers:
                    # Perform speaker diarization
                    diarization = self.speaker_detector(temp_wav.name)
                    
                    # Map speakers to segments with identification
                    speaker_segments = self._map_speakers_to_segments(
                        diarization,
                        result["segments"]
                    )
                    
                    result["segments"] = speaker_segments
                
                # Clean up temp file
                os.unlink(temp_wav.name)
                
                return self._format_transcript(result)
        except Exception as e:
            current_app.logger.error(f"Transcript generation failed: {str(e)}")
            return None
        finally:
            # Clear current audio path
            self.current_audio_path = None

    def _format_transcript(self, result):
        """Format Whisper result into transcript segments with speakers"""
        segments = []
        
        for segment in result["segments"]:
            segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "speaker": segment.get("speaker", "Unknown Speaker"),
                "speaker_confidence": segment.get("speaker_confidence", 0.0),
                "words": [
                    {
                        "word": word["word"],
                        "start": word["start"],
                        "end": word["end"],
                        "confidence": word["confidence"]
                    }
                    for word in segment.get("words", [])
                ]
            })
        
        return {
            "segments": segments,
            "language": result["language"],
            "generated_at": datetime.utcnow().isoformat(),
            "duration": result["segments"][-1]["end"] if segments else 0,
            "speakers": list(set(s["speaker"] for s in segments))
        }

    def save_transcript(self, transcript, output_path):
        """Save transcript to file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to save transcript: {str(e)}")
            return False

    def load_transcript(self, transcript_path):
        """Load transcript from file"""
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            current_app.logger.error(f"Failed to load transcript: {str(e)}")
            return None

    def generate_and_save(self, audio_path, output_path, language="en"):
        """Generate and save transcript in one operation"""
        transcript = self.generate_transcript(audio_path, language)
        if transcript and self.save_transcript(transcript, output_path):
            return transcript
        return None

    def get_transcript_path(self, episode_id):
        """Get transcript file path for episode"""
        return os.path.join(
            current_app.config['TRANSCRIPTS_DIR'],
            f'episode_{episode_id}',
            'transcript.json'
        )

    def ensure_transcript(self, episode):
        """Ensure transcript exists for episode, generate if needed"""
        transcript_path = self.get_transcript_path(episode.id)
        
        if os.path.exists(transcript_path):
            return self.load_transcript(transcript_path)
        
        return self.generate_and_save(
            episode.audio_path,
            transcript_path,
            episode.language or "en"
        )

# Example usage:
"""
from flask import Flask
app = Flask(__name__)

# Configure transcript directory
app.config['TRANSCRIPTS_DIR'] = 'path/to/transcripts'

# Initialize transcript generator
transcript_generator = TranscriptGenerator(app)

# Generate transcript for episode
@app.route('/api/episodes/<int:episode_id>/transcript', methods=['POST'])
def generate_episode_transcript(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    transcript = transcript_generator.ensure_transcript(episode)
    
    if transcript:
        return jsonify(transcript)
    else:
        return jsonify({'error': 'Failed to generate transcript'}), 500

# Get episode transcript
@app.route('/api/episodes/<int:episode_id>/transcript', methods=['GET'])
def get_episode_transcript(episode_id):
    episode = Episode.query.get_or_404(episode_id)
    transcript_path = transcript_generator.get_transcript_path(episode.id)
    
    if os.path.exists(transcript_path):
        transcript = transcript_generator.load_transcript(transcript_path)
        if transcript:
            return jsonify(transcript)
    
    return jsonify({'error': 'Transcript not found'}), 404
"""
