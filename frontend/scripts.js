class ChromeAudioTranscriber {
  constructor() {
    this.ws = null;
    this.mediaStream = null;
    this.audioContext = null;
    this.processor = null;
    this.isRecording = false;
    this.fullText = "";

    this.initWebSocket();
    this.initUI();
  }

  initWebSocket() {
    this.connectWebSocket();
  }

  connectWebSocket() {
    try {
      this.ws = new WebSocket("ws://localhost:8766");

      this.ws.onopen = () => {
        console.log("WebSocket connected");
        this.updateStatus("connected", "Connected to server");
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("Received:", data);

          switch (data.type) {
            case "transcription":
              this.displayTranscription(
                data.text,
                data.server_timestamp || data.timestamp
              );
              break;
            case "queue_status":
              this.updateQueueStatus(data.processing_count);
              break;
            case "summary_processing":
              this.showSummaryProcessing(data.message);
              break;
            case "summary_result":
              this.displaySummaryResult(data);
              break;
            case "transcription_cleared":
              this.handleTranscriptionCleared(data.message);
              break;
            default:
              console.log("Unhandled message type:", data.type);
          }
        } catch (e) {
          console.error("Message parsing error:", e);
        }
      };

      this.ws.onclose = () => {
        console.log("WebSocket connection closed");
        this.updateStatus("disconnected", "Disconnected from server");

        setTimeout(() => this.connectWebSocket(), 3000);
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.updateStatus("disconnected", "Server connection error occurred");
      };
    } catch (e) {
      console.error("WebSocket initialization error:", e);
      this.updateStatus("disconnected", "Failed to initialize WebSocket");
    }
  }

  initUI() {
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const clearBtn = document.getElementById("clearBtn");
    const summaryBtn = document.getElementById("summaryBtn");

    startBtn.addEventListener("click", () => this.startScreenCapture());
    stopBtn.addEventListener("click", () => this.stopScreenCapture());
    clearBtn.addEventListener("click", () => this.clearTranscriptions());
    summaryBtn.addEventListener("click", () => this.summarizeTranscription());
  }

  async startScreenCapture() {
    try {
      this.updateStatus("connecting", "Starting Chrome screen sharing...");

      this.mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          sampleRate: 16000,
          channelCount: 1,
        },
      });

      const audioTracks = this.mediaStream.getAudioTracks();
      if (audioTracks.length === 0) {
        throw new Error(
          "No audio track found. Please enable audio sharing when selecting screen."
        );
      }

      this.startAudioProcessing();

      this.updateStatus("recording", "🎙️ Recording - Real-time transcription");
      document.getElementById("startBtn").disabled = true;
      document.getElementById("stopBtn").disabled = false;

      this.mediaStream.getVideoTracks()[0].addEventListener("ended", () => {
        this.stopScreenCapture();
      });
    } catch (error) {
      console.error("Screen capture error:", error);
      this.showError("Failed to start screen sharing: " + error.message);
      this.updateStatus("connected", "Connected to server");
    }
  }

  startAudioProcessing() {
    try {
      this.audioContext = new AudioContext({ sampleRate: 16000 });
      const source = this.audioContext.createMediaStreamSource(
        this.mediaStream
      );

      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

      this.processor.onaudioprocess = (event) => {
        if (!this.isRecording) return;

        const inputData = event.inputBuffer.getChannelData(0);

        const level = this.calculateAudioLevel(inputData);
        this.updateAudioLevel(level);

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(inputData.buffer);
        }
      };

      source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);

      this.isRecording = true;
    } catch (error) {
      console.error("Audio processing error:", error);
      this.showError("Failed to start audio processing: " + error.message);
    }
  }

  calculateAudioLevel(data) {
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      sum += data[i] * data[i];
    }
    return Math.sqrt(sum / data.length);
  }

  updateAudioLevel(level) {
    const bar = document.getElementById("audioLevelBar");
    const percentage = Math.min(level * 1000, 100);
    bar.style.width = percentage + "%";
  }

  stopScreenCapture() {
    try {
      this.isRecording = false;

      if (this.processor) {
        this.processor.disconnect();
        this.processor = null;
      }

      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = null;
      }

      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach((track) => track.stop());
        this.mediaStream = null;
      }

      this.updateStatus("connected", "Connected to server");
      document.getElementById("startBtn").disabled = false;
      document.getElementById("stopBtn").disabled = true;

      document.getElementById("audioLevelBar").style.width = "0%";
    } catch (error) {
      console.error("Stop error:", error);
      this.showError("Error occurred during stop process: " + error.message);
    }
  }

  displayTranscription(text, timestamp) {
    const time = new Date(timestamp * 1000).toLocaleTimeString();
    const newText = `[${time}] ${text}`;

    if (this.fullText) {
      this.fullText += "\n" + newText;
    } else {
      this.fullText = newText;
    }

    const area = document.getElementById("transcriptionArea");
    area.innerHTML = `<div class="text" style="white-space: pre-wrap; line-height: 1.6;">${this.escapeHtml(
      this.fullText
    )}</div>`;
    area.scrollTop = area.scrollHeight;
  }

  clearTranscriptions() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "clear_transcription" }));
    }

    this.fullText = "";
    const area = document.getElementById("transcriptionArea");
    area.innerHTML = "Transcription results will appear here...";

    const summaryArea = document.getElementById("summaryArea");
    summaryArea.style.display = "none";
  }

  updateQueueStatus(processingCount) {
    const queueStatus = document.getElementById("queueStatus");
    const queueCount = document.getElementById("queueCount");

    if (processingCount > 0) {
      queueCount.textContent = processingCount;
      queueStatus.className = "queue-status processing";
      queueStatus.style.display = "block";
    } else {
      queueStatus.style.display = "none";
    }
  }

  summarizeTranscription() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const promptInput = document.getElementById("promptInput");
      const customPrompt = promptInput.value.trim();

      const summaryBtn = document.getElementById("summaryBtn");
      summaryBtn.disabled = true;
      summaryBtn.textContent = "🤖 Processing...";

      this.ws.send(
        JSON.stringify({
          type: "summarize",
          prompt: customPrompt,
          text: this.fullText,
        })
      );
    } else {
      this.showError("Not connected to server");
    }
  }

  showSummaryProcessing(message) {
    const summaryArea = document.getElementById("summaryArea");
    const summaryContent = document.getElementById("summaryContent");

    summaryContent.textContent = message;
    summaryArea.style.display = "block";
  }

  displaySummaryResult(data) {
    const summaryBtn = document.getElementById("summaryBtn");
    summaryBtn.disabled = false;
    summaryBtn.textContent = "🤖 AI Summary";

    const summaryArea = document.getElementById("summaryArea");
    const summaryContent = document.getElementById("summaryContent");
    const notionResult = document.getElementById("notionResult");
    const notionContent = document.getElementById("notionContent");

    if (data.success) {
      const originalLength = this.fullText ? this.fullText.length : 0;
      const summaryLength = data.summary ? data.summary.length : 0;
      const compressionRate =
        originalLength > 0
          ? Math.round((1 - summaryLength / originalLength) * 100)
          : 0;
      const stats = `Characters: ${originalLength} → ${summaryLength} (${compressionRate}% compressed)`;

      summaryContent.innerHTML = `
                        <div style="color: #666; font-size: 12px; margin-bottom: 10px;">${stats}</div>
                        <div>${this.escapeHtml(data.summary)}</div>
                    `;

      if (data.notion_result && data.notion_result.success) {
        notionContent.innerHTML = `
                            <div>✅ Successfully saved to Notion</div>
                            <div style="margin-top: 5px;">
                                <strong>Title:</strong> ${this.escapeHtml(
                                  data.notion_result.title
                                )}<br>
                                <strong>Page:</strong> <a href="${
                                  data.notion_result.url
                                }" target="_blank">Open in Notion</a>
                            </div>
                        `;
        notionResult.style.display = "block";
      } else if (data.notion_result && !data.notion_result.success) {
        notionContent.innerHTML = `❌ Failed to save to Notion: ${this.escapeHtml(
          data.notion_result.message
        )}`;
        notionResult.style.display = "block";
      } else {
        notionResult.style.display = "none";
      }

      summaryArea.style.display = "block";
    } else {
      this.showError("Summary processing failed: " + data.message);
      summaryArea.style.display = "none";
    }
  }

  handleTranscriptionCleared(message) {
    this.fullText = "";
    const area = document.getElementById("transcriptionArea");
    area.innerHTML = "Transcription results will appear here...";

    const summaryArea = document.getElementById("summaryArea");
    summaryArea.style.display = "none";

    this.showInfo(message);
  }

  showInfo(message) {
    const area = document.getElementById("transcriptionArea");
    const info = document.createElement("div");
    info.className = "info message";
    info.innerHTML = `✅ ${this.escapeHtml(message)}`;
    area.appendChild(info);
    area.scrollTop = area.scrollHeight;

    setTimeout(() => {
      if (info.parentNode) {
        info.parentNode.removeChild(info);
      }
    }, 3000);
  }

  updateStatus(type, message) {
    const status = document.getElementById("status");
    const startBtn = document.getElementById("startBtn");

    status.className = `status ${type}`;
    status.textContent = message;

    if (type === "connected") {
      startBtn.disabled = false;
    } else if (type === "disconnected") {
      startBtn.disabled = true;
    }
  }

  showError(message) {
    const area = document.getElementById("transcriptionArea");
    const error = document.createElement("div");
    error.className = "error";
    error.textContent = "❌ " + message;
    area.appendChild(error);
    area.scrollTop = area.scrollHeight;
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new ChromeAudioTranscriber();
});
