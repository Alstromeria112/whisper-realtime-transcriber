"""
AI Integration Library
Handles Gemini AI summarization and processing
"""

import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiSummarizer:
    """Gemini AI summarization class"""
    
    def __init__(self, api_key=None, model_name="gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                logger.info("Gemini AI initialized")
            except Exception as e:
                logger.error(f"Gemini initialization failed: {e}")
                self.model = None
        else:
            logger.warning("Gemini API key missing")
            self.model = None
    
    async def summarize(self, text, custom_prompt=""):
        """Summarize text using Gemini AI"""
        if not self.model:
            return "AI summarization not available (API key missing)"
        
        try:
            # Default prompt if none provided
            if not custom_prompt.strip():
                custom_prompt = """
以下の文字起こしテキストを要約してください。

要約のルール:
1. **タイトル**: 簡潔で分かりやすいタイトルを最初の行に # で記載
2. **構造化**: 見出しと箇条書きを使って整理
3. **重要ポイント**: 太文字(**text**)で強調
4. **詳細情報**: 必要に応じてネストした箇条書きで詳細を記載

出力形式はマークダウンで、以下のような構造にしてください:

# [適切なタイトル]

## 概要
- 主要な話題の概要

## 重要なポイント
- **重要事項1**: 詳細説明
    - 補足情報
    - 具体例
- **重要事項2**: 詳細説明

## 結論・まとめ
- 最終的な結論やまとめ
"""
            
            full_prompt = f"{custom_prompt}\n\n文字起こしテキスト:\n{text}"
            
            response = await self.model.generate_content_async(full_prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini summarization error: {e}")
            return f"Summarization error: {str(e)}"
    
    def is_available(self):
        """Check if Gemini AI is available"""
        return self.model is not None
