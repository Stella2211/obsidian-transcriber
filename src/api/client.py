"""Gemini API client wrapper for text summarization"""

from typing import Optional, Any
from google import genai

from src.constants import SUMMARY_MODEL
from src.api.retry import retry_with_backoff
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Wrapper for Gemini API client with retry logic (for summarization)"""

    def __init__(self, api_key: str):
        """
        Initialize Gemini client

        Args:
            api_key: Google API key
        """
        self.api_key = api_key
        self.summary_model = SUMMARY_MODEL
        self.client = genai.Client(api_key=api_key)
        logger.info("Initialized Gemini client")
        logger.info(f"Summary model: {self.summary_model}")

    def generate_content(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate content using Gemini API

        Args:
            prompt: Text prompt
            model: Optional model override
            **kwargs: Additional arguments for generate_content

        Returns:
            Generated text content
        """
        logger.debug(f"Generating content with prompt length: {len(prompt)}")

        # Use provided model or default to summary model
        use_model = model or self.summary_model

        def generate():
            contents = [prompt]

            response = self.client.models.generate_content(
                model=use_model, contents=contents, **kwargs
            )
            # Check if response has text attribute and it's not None
            if hasattr(response, "text") and response.text:
                return response.text
            else:
                # Treat None response as retryable error
                logger.warning("API response has no text content, will retry")
                from src.api.retry import RetryableError

                raise RetryableError("API returned empty response")

        return retry_with_backoff(generate)

    def summarize_text(self, text: str, context: str = "") -> str:
        """
        Summarize text using Gemini API

        Args:
            text: Text to summarize
            context: Optional context for the summary

        Returns:
            Summary text
        """
        logger.info(f"Generating summary for text of length: {len(text)}")

        prompt = f"""以下の音声文字起こしを読んで、構造化された要約を作成してください。

要約の形式：
1. **主要なトピック**: 箇条書き
2. **重要なポイント**: 最も重要な情報を箇条書き
3. **結論・まとめ**: 完結かつ要点を押さえた文章
4. **キーワード**: 重要な用語やコンセプトとそれぞれの説明を箇条書きで

{f"コンテキスト: {context}" if context else ""}

文字起こし内容：
---
{text}
---

要約は明確で読みやすく、マークダウン形式で作成してください。"""

        # Use summary model (already default in generate_content)
        summary = self.generate_content(prompt, model=self.summary_model)

        # Note: None check is now handled in generate_content with retry
        logger.info("Summary generated successfully")

        return summary
