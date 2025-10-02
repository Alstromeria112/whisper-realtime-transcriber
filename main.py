"""
Main Application
Chrome Audio Transcription Server with AI Summarization and Notion Integration
"""

import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('transcription_server.log')
    ]
)

logger = logging.getLogger(__name__)

# Import components
from backend.config.config import *
from backend.lib.audio_processing import AudioBuffer, WhisperTranscriber
from backend.lib.ai_integration import GeminiSummarizer
from backend.lib.notion_integration import NotionClient
from backend.services.websocket_service import WebSocketServer


def main():
    """Main function"""
    logger.info("Starting Chrome Audio Transcription Server")
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        # Audio processing
        audio_buffer = AudioBuffer(
            sample_rate=SAMPLE_RATE,
            silence_threshold=SILENCE_THRESHOLD,
            silence_duration=SILENCE_DURATION,
            min_audio_level=MIN_AUDIO_LEVEL,
            max_audio_chunk_duration=MAX_AUDIO_CHUNK_DURATION
        )
        
        transcriber = WhisperTranscriber(
            model_size=WHISPER_MODEL_SIZE,
            min_text_length=MIN_TEXT_LENGTH,
            max_text_length=MAX_TEXT_LENGTH,
            max_repetition_chars=MAX_REPETITION_CHARS,
            max_repetition_words=MAX_REPETITION_WORDS
        )
        
        # AI integration
        summarizer = GeminiSummarizer(api_key=GEMINI_API_KEY)
        
        # Notion integration
        notion_client = NotionClient(
            token=NOTION_TOKEN,
            parent_page_id=NOTION_PARENT_PAGE_ID
        )
        
        # WebSocket server
        server = WebSocketServer(
            audio_buffer=audio_buffer,
            transcriber=transcriber,
            summarizer=summarizer,
            notion_client=notion_client,
            host=WEBSOCKET_HOST,
            port=WEBSOCKET_PORT
        )
        
        logger.info("All components initialized successfully")
        
        # Start server
        asyncio.run(server.start_server())
        
    except KeyboardInterrupt:
        logger.info("Stopping server...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
