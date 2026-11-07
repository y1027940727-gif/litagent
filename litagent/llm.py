"""LLM interface. Gemini over REST by default (no SDK needed); swap in any class with .complete()."""
import os
import requests


class LLM:
    def complete(self, system: str, messages: list) -> str:  # messages: [{"role": "user"|"model", "text": str}]
        raise NotImplementedError


class Gemini(LLM):
    def __init__(self, model: str = None, api_key: str = None, session=requests):
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.session = session
        if not self.api_key:
            raise RuntimeError("Set GEMINI_API_KEY")

    def complete(self, system, messages):
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in messages],
            "generationConfig": {"temperature": 0.1},
        }
        r = self.session.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key}, json=body, timeout=180)
        r.raise_for_status()
        data = r.json()
        try:
            return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected Gemini response: {str(data)[:300]}")
