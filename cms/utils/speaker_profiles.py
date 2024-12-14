import os
import json
import numpy as np
from datetime import datetime
from flask import current_app
from pathlib import Path
import torch
import torchaudio
from speechbrain.pretrained import EncoderClassifier
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path
import soundfile as sf
from pydub import AudioSegment
from threading import Lock
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import parselmouth

class SpeakerProfiles:
    def __init__(self, app=None):
        self.app = app
        self.encoder = None
        self.voice_encoder = None
        self.model_lock = Lock()
        self.profiles = {}
        self.embeddings = {}
        self.praat = None  # Praat interface for voice analysis
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.load_profiles()
        
        # Initialize Praat for voice analysis
        self.praat = parselmouth

    def analyze_voice_characteristics(self, audio):
        """Analyze voice characteristics using Praat"""
        try:
            # Convert audio to format compatible with Praat
            with NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                if isinstance(audio, str):
                    AudioSegment.from_file(audio).export(temp_wav.name, format='wav')
                else:
                    audio.export(temp_wav.name, format='wav')
                
                # Load sound file
                sound = self.praat.Sound(temp_wav.name)
                
                # Extract pitch
                pitch = sound.to_pitch()
                pitch_values = pitch.selected_array['frequency']
                pitch_values = pitch_values[pitch_values != 0]
                
                # Extract intensity
                intensity = sound.to_intensity()
                intensity_values = intensity.values[0]
                
                # Extract formants
                formants = sound.to_formant_burg()
                
                # Calculate voice characteristics
                characteristics = {
                    "pitch": {
                        "mean": float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0,
                        "std": float(np.std(pitch_values)) if len(pitch_values) > 0 else 0,
                        "min": float(np.min(pitch_values)) if len(pitch_values) > 0 else 0,
                        "max": float(np.max(pitch_values)) if len(pitch_values) > 0 else 0
                    },
                    "intensity": {
                        "mean": float(np.mean(intensity_values)),
                        "std": float(np.std(intensity_values)),
                        "min": float(np.min(intensity_values)),
                        "max": float(np.max(intensity_values))
                    },
                    "formants": {
                        f"F{i}": {
                            "mean": float(np.mean([
                                formants.get_value_at_time(i, t)
                                for t in formants.xs()
                                if formants.get_value_at_time(i, t)
                            ]) or 0)
                        }
                        for i in range(1, 5)
                    },
                    "voice_quality": self._analyze_voice_quality(sound),
                    "speech_rate": self._analyze_speech_rate(sound),
                    "articulation": self._analyze_articulation(sound)
                }
                
                # Clean up
                os.unlink(temp_wav.name)
                
                return characteristics
        except Exception as e:
            current_app.logger.error(f"Voice analysis failed: {str(e)}")
            return None

    def _analyze_voice_quality(self, sound):
        """Analyze voice quality metrics"""
        try:
            # Calculate harmonicity (HNR)
            harmonicity = sound.to_harmonicity()
            hnr_values = harmonicity.values[0]
            
            # Calculate jitter
            point_process = sound.to_pitch().to_point_process()
            jitter = point_process.get_jitter(type=1)  # local
            
            # Calculate shimmer
            shimmer = point_process.get_shimmer(type=1)  # local
            
            return {
                "harmonicity": {
                    "mean": float(np.mean(hnr_values)),
                    "std": float(np.std(hnr_values))
                },
                "jitter": float(jitter),
                "shimmer": float(shimmer)
            }
        except:
            return None

    def _analyze_speech_rate(self, sound):
        """Analyze speech rate and rhythm"""
        try:
            # Calculate intensity peaks for syllable estimation
            intensity = sound.to_intensity()
            peaks = self._find_peaks(intensity.values[0])
            
            duration = sound.duration
            syllables = len(peaks)
            
            return {
                "syllables_per_second": syllables / duration,
                "articulation_rate": syllables / (duration * 0.6),  # Excluding pauses
                "speaking_duration": duration
            }
        except:
            return None

    def _analyze_articulation(self, sound):
        """Analyze articulation clarity"""
        try:
            # Calculate spectrum
            spectrum = sound.to_spectrum()
            
            # Get spectral moments
            center_of_gravity = spectrum.get_center_of_gravity()
            standard_deviation = spectrum.get_standard_deviation()
            
            return {
                "spectral_center_of_gravity": float(center_of_gravity),
                "spectral_standard_deviation": float(standard_deviation),
                "clarity_score": float(
                    1.0 - (standard_deviation / (center_of_gravity + 1e-6))
                )
            }
        except:
            return None

    def _find_peaks(self, array):
        """Find peaks in array for syllable detection"""
        peaks = []
        for i in range(1, len(array) - 1):
            if array[i] > array[i-1] and array[i] > array[i+1]:
                peaks.append(i)
        return peaks

    def create_profile(self, name, role, audio_samples):
        """Create a new speaker profile with voice analysis"""
        try:
            self._ensure_models_loaded()
            
            # Generate embeddings from audio samples
            embeddings = []
            voice_characteristics = []
            
            for sample in audio_samples:
                # Convert audio to compatible format
                wav = self._prepare_audio(sample)
                
                # Get embeddings from both models for robustness
                sb_embedding = self._get_speechbrain_embedding(wav)
                rs_embedding = self._get_resemblyzer_embedding(wav)
                
                embeddings.append({
                    "speechbrain": sb_embedding.tolist(),
                    "resemblyzer": rs_embedding.tolist()
                })
                
                # Analyze voice characteristics
                characteristics = self.analyze_voice_characteristics(sample)
                if characteristics:
                    voice_characteristics.append(characteristics)
            
            # Average voice characteristics
            avg_characteristics = self._average_characteristics(voice_characteristics)
            
            # Create profile
            profile = {
                "name": name,
                "role": role,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "embeddings": embeddings,
                "average_embedding": {
                    "speechbrain": np.mean([e["speechbrain"] for e in embeddings], axis=0).tolist(),
                    "resemblyzer": np.mean([e["resemblyzer"] for e in embeddings], axis=0).tolist()
                },
                "voice_characteristics": avg_characteristics,
                "sample_count": len(audio_samples)
            }
            
            # Save profile
            profile_id = self._generate_profile_id(name)
            self.profiles[profile_id] = profile
            self.save_profiles()
            
            return profile_id
        except Exception as e:
            current_app.logger.error(f"Failed to create speaker profile: {str(e)}")
            return None

    def _average_characteristics(self, characteristics_list):
        """Average multiple voice characteristic measurements"""
        if not characteristics_list:
            return None
        
        avg = defaultdict(dict)
        
        # Combine all measurements
        for chars in characteristics_list:
            for category, values in chars.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        if isinstance(value, dict):
                            if category not in avg:
                                avg[category] = defaultdict(dict)
                            for subkey, subvalue in value.items():
                                if subkey not in avg[category][key]:
                                    avg[category][key][subkey] = []
                                avg[category][key][subkey].append(subvalue)
                        else:
                            if key not in avg[category]:
                                avg[category][key] = []
                            avg[category][key].append(value)
        
        # Calculate averages
        result = {}
        for category, values in avg.items():
            result[category] = {}
            for key, value in values.items():
                if isinstance(value, dict):
                    result[category][key] = {
                        subkey: float(np.mean(subvalues))
                        for subkey, subvalues in value.items()
                    }
                else:
                    result[category][key] = float(np.mean(value))
        
        return result

    def _ensure_models_loaded(self):
        """Lazy load the speaker recognition models"""
        if self.encoder is None:
            with self.model_lock:
                if self.encoder is None:
                    # Load SpeechBrain model for speaker recognition
                    self.encoder = EncoderClassifier.from_hparams(
                        source="speechbrain/spkrec-ecapa-voxceleb",
                        savedir=os.path.join(
                            current_app.config['MODELS_DIR'],
                            "speechbrain_spkrec"
                        )
                    )
                    # Load Resemblyzer for voice similarity
                    self.voice_encoder = VoiceEncoder()

    def update_profile(self, profile_id, audio_samples=None, **updates):
        """Update an existing speaker profile"""
        if profile_id not in self.profiles:
            return False
        
        profile = self.profiles[profile_id]
        
        # Update basic information
        for key, value in updates.items():
            if key in ["name", "role"]:
                profile[key] = value
        
        # Update embeddings if new audio samples provided
        if audio_samples:
            try:
                self._ensure_models_loaded()
                
                new_embeddings = []
                for sample in audio_samples:
                    wav = self._prepare_audio(sample)
                    sb_embedding = self._get_speechbrain_embedding(wav)
                    rs_embedding = self._get_resemblyzer_embedding(wav)
                    
                    new_embeddings.append({
                        "speechbrain": sb_embedding.tolist(),
                        "resemblyzer": rs_embedding.tolist()
                    })
                
                # Combine with existing embeddings
                profile["embeddings"].extend(new_embeddings)
                
                # Update average embedding
                profile["average_embedding"] = {
                    "speechbrain": np.mean([e["speechbrain"] for e in profile["embeddings"]], axis=0).tolist(),
                    "resemblyzer": np.mean([e["resemblyzer"] for e in profile["embeddings"]], axis=0).tolist()
                }
            except Exception as e:
                current_app.logger.error(f"Failed to update speaker embeddings: {str(e)}")
                return False
        
        profile["updated_at"] = datetime.utcnow().isoformat()
        self.save_profiles()
        return True

    def identify_speaker(self, audio_segment, min_confidence=0.75):
        """Identify speaker from audio segment"""
        try:
            self._ensure_models_loaded()
            
            # Prepare audio
            wav = self._prepare_audio(audio_segment)
            
            # Get embeddings
            sb_embedding = self._get_speechbrain_embedding(wav)
            rs_embedding = self._get_resemblyzer_embedding(wav)
            
            best_match = None
            highest_confidence = 0
            
            # Compare with all profiles
            for profile_id, profile in self.profiles.items():
                # Calculate similarity scores using both models
                sb_similarity = cosine_similarity(
                    [sb_embedding],
                    [np.array(profile["average_embedding"]["speechbrain"])]
                )[0][0]
                
                rs_similarity = cosine_similarity(
                    [rs_embedding],
                    [np.array(profile["average_embedding"]["resemblyzer"])]
                )[0][0]
                
                # Combined confidence score (weighted average)
                confidence = (0.6 * sb_similarity + 0.4 * rs_similarity)
                
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = profile_id
            
            if highest_confidence >= min_confidence:
                return {
                    "profile_id": best_match,
                    "name": self.profiles[best_match]["name"],
                    "confidence": highest_confidence
                }
            
            return None
        except Exception as e:
            current_app.logger.error(f"Speaker identification failed: {str(e)}")
            return None

    def get_profile(self, profile_id):
        """Get speaker profile by ID"""
        return self.profiles.get(profile_id)

    def list_profiles(self):
        """List all speaker profiles"""
        return {
            profile_id: {
                "name": profile["name"],
                "role": profile["role"],
                "created_at": profile["created_at"],
                "updated_at": profile["updated_at"]
            }
            for profile_id, profile in self.profiles.items()
        }

    def delete_profile(self, profile_id):
        """Delete a speaker profile"""
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            self.save_profiles()
            return True
        return False

    def _prepare_audio(self, audio_input):
        """Prepare audio for embedding generation"""
        if isinstance(audio_input, str):
            # Load from file
            audio = AudioSegment.from_file(audio_input)
        else:
            # Assume AudioSegment
            audio = audio_input
        
        # Convert to WAV format
        with NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            audio.export(temp_wav.name, format='wav')
            wav, _ = sf.read(temp_wav.name)
            os.unlink(temp_wav.name)
        
        return wav

    def _get_speechbrain_embedding(self, wav):
        """Get embedding using SpeechBrain"""
        wav_tensor = torch.FloatTensor(wav)
        embedding = self.encoder.encode_batch(wav_tensor)
        return embedding.squeeze().cpu().numpy()

    def _get_resemblyzer_embedding(self, wav):
        """Get embedding using Resemblyzer"""
        processed_wav = preprocess_wav(wav)
        embedding = self.voice_encoder.embed_utterance(processed_wav)
        return embedding

    def _generate_profile_id(self, name):
        """Generate unique profile ID"""
        base = "".join(c.lower() for c in name if c.isalnum())
        profile_id = base
        counter = 1
        
        while profile_id in self.profiles:
            profile_id = f"{base}_{counter}"
            counter += 1
        
        return profile_id

    def save_profiles(self):
        """Save profiles to disk"""
        try:
            profiles_file = os.path.join(
                current_app.config['DATA_DIR'],
                'speaker_profiles.json'
            )
            
            os.makedirs(os.path.dirname(profiles_file), exist_ok=True)
            
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to save speaker profiles: {str(e)}")
            return False

    def load_profiles(self):
        """Load profiles from disk"""
        try:
            profiles_file = os.path.join(
                current_app.config['DATA_DIR'],
                'speaker_profiles.json'
            )
            
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    self.profiles = json.load(f)
            else:
                self.profiles = {}
            
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to load speaker profiles: {str(e)}")
            self.profiles = {}
            return False

# Example usage:
"""
from flask import Flask, jsonify, request
app = Flask(__name__)

# Initialize speaker profiles
speaker_profiles = SpeakerProfiles(app)

@app.route('/api/speakers/profiles', methods=['POST'])
def create_speaker_profile():
    name = request.form['name']
    role = request.form['role']
    audio_files = request.files.getlist('audio_samples')
    
    audio_samples = []
    for file in audio_files:
        audio = AudioSegment.from_file(file)
        audio_samples.append(audio)
    
    profile_id = speaker_profiles.create_profile(name, role, audio_samples)
    
    if profile_id:
        return jsonify({
            'profile_id': profile_id,
            'profile': speaker_profiles.get_profile(profile_id)
        })
    
    return jsonify({'error': 'Failed to create profile'}), 500

@app.route('/api/speakers/identify', methods=['POST'])
def identify_speaker():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    audio = AudioSegment.from_file(audio_file)
    
    result = speaker_profiles.identify_speaker(audio)
    
    if result:
        return jsonify(result)
    
    return jsonify({'error': 'Speaker not identified'}), 404
"""
