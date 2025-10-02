# Chrome音声文字起こしシステム設定

# Whisperモデル設定
WHISPER_MODEL_SIZE = "medium"  # tiny, base, small, medium, large-v1, large-v2, large-v3

# 音声バッファ設定
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01    # 無音検出の閾値（低いほど敏感）
SILENCE_DURATION = 0.7      # 無音検出時間（秒）
MIN_AUDIO_LEVEL = 0.005     # 最小音声レベル（これ以下は無視）
MAX_AUDIO_CHUNK_DURATION = 30  # 音声チャンクの最大長（秒）- 10.24秒制限を解除

# 文字起こし品質設定
MIN_TEXT_LENGTH = 2         # 最小文字数
MAX_TEXT_LENGTH = 2000      # 最大文字数
MAX_REPETITION_CHARS = 4    # 同じ文字の最大連続数
MAX_REPETITION_WORDS = 2    # 同じ単語の最大連続数

# サーバー設定
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 8766

# 文字起こしキュー設定
MAX_QUEUE_SIZE = 10         # 最大キューサイズ
QUEUE_STATUS_UPDATE_INTERVAL = 0.5  # キューステータス更新間隔（秒）

# デバッグ設定
DEBUG_MODE = False          # Trueにすると無効な文字起こしのログが表示される

# Gemini AI設定
import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Notion API設定
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")
