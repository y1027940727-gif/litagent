"""LLM interface. Gemini over REST (no SDK needed); swap in any class with .complete()."""
import os
import time
import requests


class LLM:
    def complete(self, system: str, messages: list) -> str:  # messages: [{"role": "user"|"model", "text": str}]
        raise NotImplementedError


class Gemini(LLM):
    RETRY_CODES = {429, 500, 502, 503, 504}

    def __init__(self, model: str = None, api_key: str = None, session=requests, retries: int = 4):
        self.model = (model or os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")).replace("models/", "")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.session, self.retries = session, retries
        if not self.api_key:
            raise RuntimeError("Set GEMINI_API_KEY")

    def complete(self, system, messages):
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in messages],
            "generationConfig": {"temperature": 0.1},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        # The key goes in a header, never in the URL, so it cannot leak into logs or tracebacks.
        headers = {"x-goog-api-key": self.api_key}
        for attempt in range(self.retries + 1):
            try:
                r = self.session.post(url, headers=headers, json=body, timeout=180)
            except requests.exceptions.RequestException:
                if attempt == self.retries:
                    raise
                time.sleep(5 * 2 ** attempt)
                continue
            if r.status_code in self.RETRY_CODES and attempt < self.retries:
                time.sleep(5 * 2 ** attempt)
                continue
            if r.status_code != 200:
                raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            try:
                return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            except (KeyError, IndexError):
                raise RuntimeError(f"Unexpected Gemini response: {str(data)[:300]}")
