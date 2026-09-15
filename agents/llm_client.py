"""Shared interface and Gemini implementation for LLM calls."""

import json
import os
import re
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from google import genai



load_dotenv()


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

    def complete(self, system: str, user: str) -> str:
        """Send a prompt to Gemini and return the generated text."""
        interaction = self.client.interactions.create(
            model=self.model,
            system_instruction=system,
            input=user,
        )

        return interaction.output_text


def parse_json_response(text: str):
    """Strip optional Markdown code fences and parse JSON."""
    cleaned = text.strip()

    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    return json.loads(cleaned)