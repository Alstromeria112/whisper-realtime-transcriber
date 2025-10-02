# Whisper Realtime Transcriber

## Overview

This project is a Chrome audio real-time transcription server with AI summarization and Notion integration. It enables users to transcribe audio from Chrome tabs in real time, summarize the transcriptions using Gemini AI, and save summaries to Notion.

## Features

- Real-time audio transcription from Chrome tab audio
- Silence detection for segmenting transcriptions
- AI-powered summarization using Gemini
- Save summaries directly to Notion
- WebSocket-based communication between frontend and backend

## Project Structure

- `main.py`: Main server application
- `backend/`
  - `config/`: Configuration files
  - `lib/`: Core libraries (audio processing, AI, Notion)
  - `services/`: WebSocket server for real-time communication
- `frontend/`: Simple web interface for controlling transcription and summaries

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure environment variables**
   - Create a `.env` file in `backend/` with your Gemini and Notion API keys:
     ```env
     GEMINI_API_KEY=your_gemini_api_key
     NOTION_TOKEN=your_notion_token
     NOTION_PARENT_PAGE_ID=your_notion_page_id
     ```
3. **Start the server**
   - On Windows: Double-click `start.bat` or run `python main.py`
   - On Linux/Mac: Run `bash start.sh` or `python main.py`

## Usage

1. Open `frontend/index.html` in your browser.
2. Click "Start Screen Share" and select a Chrome tab with audio.
3. Enable "Share audio".
4. Transcriptions will appear in real time. Use "AI Summary" to generate a summary and "Save to Notion" to store it.

## Requirements

See `requirements.txt` for all Python dependencies:

- faster-whisper
- websockets
- numpy
- soundfile
- webrtcvad
- google-generativeai
- python-dotenv
- notion-client

## Configuration

See `backend/config/config.py` for advanced settings (model size, silence detection, server port, etc).

## Logging

Transcription logs are saved to `transcription_server.log`.

## License

MIT License
