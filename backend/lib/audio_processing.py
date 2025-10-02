"""
Audio Processing Library
Handles audio buffering, silence detection, and transcription
"""

import numpy as np
import logging
from collections import deque
from faster_whisper import WhisperModel
import re

logger = logging.getLogger(__name__)


class AudioBuffer:
    """Audio data buffering and silence detection class"""
    
    def __init__(self, sample_rate=16000, silence_threshold=0.01, silence_duration=0.7, 
                 min_audio_level=0.005, max_audio_chunk_duration=30):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_audio_level = min_audio_level
        self.max_audio_chunk_duration = max_audio_chunk_duration
        
        self.buffer = deque()
        self.silence_frames = int(self.silence_duration * self.sample_rate)
        self.current_silence_count = 0
        self.audio_chunk = []
        self.min_chunk_length = int(0.5 * self.sample_rate)  # Minimum 0.5 seconds
        
    def add_audio(self, audio_data):
        """Add audio data and perform silence detection"""
        # Calculate audio level
        audio_level = np.sqrt(np.mean(audio_data ** 2))
        
        # More strict silence detection
        if audio_level < self.silence_threshold:
            self.current_silence_count += len(audio_data)
        else:
            self.current_silence_count = 0
            
        self.audio_chunk.extend(audio_data)
        
        # Return audio chunk if silence continues for specified time and meets minimum length
        if (self.current_silence_count >= self.silence_frames and 
            len(self.audio_chunk) >= self.min_chunk_length):
            
            chunk = np.array(self.audio_chunk, dtype=np.float32)
            
            # Check audio quality
            chunk_level = np.sqrt(np.mean(chunk ** 2))
            if chunk_level > self.min_audio_level:  # Audio level above threshold
                self.audio_chunk = []
                self.current_silence_count = 0
                return chunk
            else:
                # If audio level is too low, reset and wait for next
                self.audio_chunk = []
                self.current_silence_count = 0
        
        # Force split if chunk is too long (configurable maximum duration)
        max_chunk_length = self.sample_rate * self.max_audio_chunk_duration
        if len(self.audio_chunk) > max_chunk_length:
            chunk = np.array(self.audio_chunk, dtype=np.float32)
            self.audio_chunk = []
            self.current_silence_count = 0
            logger.info(f"Audio chunk reached maximum length ({self.max_audio_chunk_duration}s), forced split")
            return chunk
        
        return None


class WhisperTranscriber:
    """Transcription class using faster-whisper"""
    
    def __init__(self, model_size="medium", min_text_length=2, max_text_length=2000, 
                 max_repetition_chars=4, max_repetition_words=2):
        """
        model_size: tiny, base, small, medium, large-v1, large-v2, large-v3
        """
        self.model_size = model_size
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.max_repetition_chars = max_repetition_chars
        self.max_repetition_words = max_repetition_words
        
        logger.info(f"Loading Whisper model '{model_size}'...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model loading completed")
        
    def is_valid_transcription(self, text):
        """Check transcription result validity"""
        if not text or len(text.strip()) < self.min_text_length:
            return False
            
        text = text.strip()
        
        # Length check
        if len(text) > self.max_text_length:
            return False
        
        # Check for excessive character repetition
        for i in range(len(text) - self.max_repetition_chars):
            if text[i] == text[i + 1] == text[i + 2] == text[i + 3]:
                if self.max_repetition_chars == 4:
                    return False
        
        # Check for excessive word repetition
        words = text.split()
        if len(words) >= self.max_repetition_words * 2:
            for i in range(len(words) - self.max_repetition_words):
                if all(words[i] == words[i + j] for j in range(1, self.max_repetition_words + 1)):
                    return False
        
        # Filter patterns that indicate noise or invalid transcription
        noise_patterns = [
            r'^[a-zA-Z]$',  # Single letter
            r'^\d+$',  # Numbers only
            r'^[!@#$%^&*(),.?":{}|<>]+$',  # Symbols only
            r'^(あ|い|う|え|お|ん|っ|。|、)+$',  # Japanese single characters
            r'^(um|uh|ah|oh|mm|hmm)\s*$',  # English filler words
            r'^(えー|あー|うー|んー|あの|その|まあ)\s*$',  # Japanese filler words
            r'^\s*$',  # Whitespace only
        ]
        
        for pattern in noise_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        return True
    
    def transcribe(self, audio_chunk):
        """Transcribe audio chunk to text"""
        try:
            segments, info = self.model.transcribe(
                audio_chunk,
                beam_size=5,
                language="ja",
                task="transcribe",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # Combine all segments
            text = ""
            for segment in segments:
                text += segment.text
            
            text = text.strip()
            
            if self.is_valid_transcription(text):
                return text
            else:
                logger.debug(f"Invalid transcription filtered: {text}")
                return ""
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
