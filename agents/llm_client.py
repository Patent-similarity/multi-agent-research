"""Shared interface and Gemini implementation for LLM calls."""

import json
import os
import re
import time
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from google import genai


load_dotenv()


API_RETRIES = 3

# Same retry/backoff pattern used by the retrieval agent.
# Only the waits between attempts are used.
API_RETRY_WAIT = [120, 300, 600]


class LLMResponseParseError(ValueError):
    """Raised when an LLM response cannot be parsed as JSON."""


class LLMClient(ABC):
    """Abstract interface for an LLM client."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send system and user prompts to the LLM and return text."""
        pass


class GeminiClient(LLMClient):
    """LLM client backed by Google's Gemini API."""

    def __init__(self, model: str = "gemini-3.6-flash"):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model = model

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        """Return whether an exception looks like a transient API failure."""

        status_code = getattr(exc, "code", None)

        if status_code in {408, 429, 500, 502, 503, 504}:
            return True

        status_code = getattr(exc, "status_code", None)

        if status_code in {408, 429, 500, 502, 503, 504}:
            return True

        error_text = str(exc).lower()

        transient_terms = (
            "timeout",
            "timed out",
            "deadline exceeded",
            "connection reset",
            "connection aborted",
            "connection error",
            "temporarily unavailable",
            "temporary failure",
            "service unavailable",
            "internal server error",
            "bad gateway",
            "gateway timeout",
            "too many requests",
            "rate limit",
            "resource exhausted",
            "unavailable",
            "503",
            "502",
            "504",
            "429",
        )

        return any(term in error_text for term in transient_terms)

    def complete(self, system: str, user: str) -> str:
        """Send a prompt to Gemini and return the generated text.

        Transient API failures are retried with bounded backoff.
        Non-transient failures are raised immediately.
        """

        last_error = None

        for attempt in range(API_RETRIES):
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    system_instruction=system,
                    input=user,
                )

                return interaction.output_text

            except Exception as exc:
                last_error = exc

                if not self._is_retryable_error(exc):
                    raise RuntimeError(
                        "Gemini API call failed with a non-retryable error "
                        f"for model '{self.model}': {exc}"
                    ) from exc

                print(
                    f"Gemini API attempt "
                    f"{attempt + 1}/{API_RETRIES} failed: {exc}"
                )

                if attempt < API_RETRIES - 1:
                    wait_time = API_RETRY_WAIT[
                        min(
                            attempt,
                            len(API_RETRY_WAIT) - 1,
                        )
                    ]

                    print(
                        f"Retrying Gemini API call in "
                        f"{wait_time} seconds..."
                    )

                    time.sleep(wait_time)

        raise RuntimeError(
            "Gemini API call failed after "
            f"{API_RETRIES} attempts for model '{self.model}'. "
            f"Last error: {last_error}"
        ) from last_error


def parse_json_response(text: str):
    """Strip optional Markdown code fences and parse JSON."""

    cleaned = text.strip()

    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMResponseParseError(
            "LLM response was not valid JSON."
        ) from exc