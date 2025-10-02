"""
WebSocket Service
Handles WebSocket connections and real-time communication
"""

import asyncio
import websockets
import json
import logging
import threading
import time
import numpy as np
import io
from collections import deque

logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server for real-time transcription"""
    
    def __init__(self, audio_buffer, transcriber, summarizer, notion_client, 
                 host="localhost", port=8766):
        self.host = host
        self.port = port
        self.clients = set()
        
        # Components
        self.audio_buffer = audio_buffer
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.notion_client = notion_client
        
        # Server state
        self.event_loop = None
        self.full_transcription = []  # Store all transcription content
        self.transcription_lock = threading.Lock()  # Thread-safe lock
        
        # Transcription queue management
        self.transcription_queue = asyncio.Queue()
        self.processing_count = 0
        self.currently_processing = False  # Flag to track if currently processing a task
        self.queue_lock = threading.Lock()
        self.queue_id_counter = 0
        
    async def register_client(self, websocket):
        """Register client"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        
    async def unregister_client(self, websocket):
        """Unregister client"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected: {websocket.remote_address}")
        
    async def broadcast_transcription(self, text, server_timestamp=None, queue_id=None):
        """Send transcription result to all clients"""
        if self.clients and text.strip():
            # Use current time if no server timestamp provided
            if server_timestamp is None:
                server_timestamp = time.time()
            
            # Add to full transcription
            with self.transcription_lock:
                self.full_transcription.append({
                    "text": text,
                    "timestamp": server_timestamp
                })
            
            message = {
                "type": "transcription",
                "text": text,
                "server_timestamp": server_timestamp,
                "client_timestamp": time.time()
            }
            
            if queue_id is not None:
                message["queue_id"] = queue_id
            
            await self.broadcast_message(message)
            
        # Task completion processing outside the if block
        if queue_id is not None:
            await self.finish_transcription_task(queue_id)
    
    async def broadcast_message(self, message):
        """Send message to all clients"""
        if not self.clients:
            return
            
        # Remove disconnected clients
        disconnected = []
        for client in self.clients:
            try:
                await client.send(json.dumps(message, ensure_ascii=False))
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(client)
        
        for client in disconnected:
            self.clients.discard(client)
    
    async def send_full_transcription(self, websocket):
        """Send full transcription content"""
        with self.transcription_lock:
            full_text = " ".join([item["text"] for item in self.full_transcription])
        
        message = {
            "type": "full_transcription",
            "text": full_text,
            "count": len(self.full_transcription)
        }
        
        try:
            await websocket.send(json.dumps(message, ensure_ascii=False))
        except websockets.exceptions.ConnectionClosed:
            pass
    
    async def clear_transcription(self):
        """Clear all transcription data"""
        with self.transcription_lock:
            self.full_transcription.clear()
        logger.info("Transcription history cleared")
    
    async def handle_summarize_request(self, websocket, custom_prompt, client_text):
        """Handle summarization request"""
        try:
            # Use client text if provided, otherwise use full transcription
            if client_text and client_text.strip():
                full_text = client_text
            else:
                with self.transcription_lock:
                    full_text = " ".join([item["text"] for item in self.full_transcription])
            
            if not full_text.strip():
                await websocket.send(json.dumps({
                    "type": "summary_result",
                    "success": False,
                    "message": "No text available for summarization."
                }, ensure_ascii=False))
                return
            
            # Send processing message
            await websocket.send(json.dumps({
                "type": "summary_processing",
                "message": "AI summarization in progress..."
            }, ensure_ascii=False))
            
            # Generate summary with Gemini AI
            summary = await self.summarizer.summarize(full_text, custom_prompt)
            
            # Save to Notion if configured
            notion_result = None
            if self.notion_client.is_available():
                try:
                    await websocket.send(json.dumps({
                        "type": "notion_processing",
                        "message": "Saving to Notion..."
                    }, ensure_ascii=False))
                    
                    notion_result = await self.notion_client.save_summary(summary)
                    
                except Exception as e:
                    logger.error(f"Notion save error: {e}")
                    notion_result = {"success": False, "message": str(e)}
            
            # Send final result
            response = {
                "type": "summary_result",
                "success": True,
                "summary": summary,
                "notion_result": notion_result
            }
            
            await websocket.send(json.dumps(response, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            await websocket.send(json.dumps({
                "type": "summary_result",
                "success": False,
                "message": str(e)
            }, ensure_ascii=False))
    
    async def handle_audio_data(self, data):
        """Process received audio data"""
        try:
            # Convert binary data to numpy array
            audio_data = np.frombuffer(data, dtype=np.float32)
            
            # Add to audio buffer and detect silence
            audio_chunk = self.audio_buffer.add_audio(audio_data)
            
            if audio_chunk is not None:
                # Record server reception timestamp
                server_timestamp = time.time()
                
                logger.info(f"Processing audio chunk... Length: {len(audio_chunk)/16000:.2f}s")
                
                # Add transcription task to queue
                with self.queue_lock:
                    self.queue_id_counter += 1
                    queue_id = self.queue_id_counter
                
                # Add transcription task to queue
                await self.add_transcription_task(audio_chunk, server_timestamp, queue_id)
                
                # Notify clients of queue status (queue size will be calculated in broadcast_queue_status)
                await self.broadcast_queue_status()
                
        except Exception as e:
            logger.error(f"Audio data processing error: {e}")
    
    async def add_transcription_task(self, audio_chunk, server_timestamp, queue_id):
        """Add transcription task to queue"""
        task_data = {
            "audio_chunk": audio_chunk,
            "server_timestamp": server_timestamp,
            "queue_id": queue_id
        }
        await self.transcription_queue.put(task_data)
        logger.info(f"Task added to queue: ID={queue_id}")

    async def finish_transcription_task(self, queue_id):
        """Complete transcription task processing"""
        # Processing completion is handled in queue_worker, just log completion
        logger.info(f"Completed task: ID={queue_id}")
        
        # Queue status is updated in queue_worker after processing completes
    
    async def broadcast_queue_status(self):
        """Notify clients of queue status"""
        with self.queue_lock:
            # Calculate total: pending tasks in queue + currently processing task (if any)
            pending_tasks = self.transcription_queue.qsize()
            total_tasks = pending_tasks + (1 if self.currently_processing else 0)
            
        message = {
            "type": "queue_status",
            "processing_count": total_tasks,
            "pending_count": pending_tasks,
            "currently_processing": self.currently_processing,
            "timestamp": time.time()
        }
        await self.broadcast_message(message)
    
    async def handle_client(self, websocket):
        """Handle client connection"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    # Process binary data (audio)
                    await self.handle_audio_data(message)
                else:
                    # Process text messages
                    try:
                        data = json.loads(message)
                        message_type = data.get("type")
                        
                        if message_type == "ping":
                            await websocket.send(json.dumps({"type": "pong"}))
                        elif message_type == "get_full_transcription":
                            await self.send_full_transcription(websocket)
                        elif message_type == "summarize":
                            custom_prompt = data.get("prompt", "")
                            client_text = data.get("text", "")
                            await self.handle_summarize_request(websocket, custom_prompt, client_text)
                        elif message_type == "clear_transcription":
                            await self.clear_transcription()
                            await self.broadcast_message({
                                "type": "transcription_cleared",
                                "message": "Transcription history cleared"
                            })
                            
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON message received")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed")
        except Exception as e:
            logger.error(f"Client processing error: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Start server"""
        logger.info(f"Starting WebSocket server: ws://{self.host}:{self.port}")
        
        # Save event loop
        self.event_loop = asyncio.get_running_loop()
        
        # Start queue processing worker
        asyncio.create_task(self.queue_worker())
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("Server started. Press Ctrl+C to stop.")
            # Run server forever
            await asyncio.Future()  # run forever
    
    async def queue_worker(self):
        """Queue processing worker (sequential processing to maintain order)"""
        logger.info("Queue worker started")
        while True:
            try:
                # Wait for next task from queue
                task_data = await self.transcription_queue.get()
                logger.info(f"Processing task: ID={task_data['queue_id']}")
                
                # Mark as currently processing
                with self.queue_lock:
                    self.currently_processing = True
                
                # Notify clients of updated queue status
                await self.broadcast_queue_status()
                
                # Process transcription synchronously to maintain order
                try:
                    # Transcribe audio on separate thread but wait for completion
                    text = await asyncio.get_event_loop().run_in_executor(
                        None, self.transcriber.transcribe, task_data["audio_chunk"]
                    )
                    
                    if text and text.strip():
                        logger.info(f"Transcription result: {text}")
                        # Broadcast transcription result
                        await self.broadcast_transcription(text, task_data["server_timestamp"], task_data["queue_id"])
                    else:
                        logger.info(f"Empty transcription for task ID={task_data['queue_id']}")
                        
                except Exception as e:
                    logger.error(f"Transcription error: {e}")
                
                # Mark as no longer processing and update queue status
                with self.queue_lock:
                    self.currently_processing = False
                
                # Notify clients of updated queue status
                await self.broadcast_queue_status()
                
                # Mark task as done
                self.transcription_queue.task_done()
                
            except Exception as e:
                logger.error(f"Queue worker error: {e}")
                # Ensure processing flag is reset on error
                with self.queue_lock:
                    self.currently_processing = False
                await self.broadcast_queue_status()
                await asyncio.sleep(1)  # Wait on error
