"""
culture_guide.py
----------------
CultureGuideGenerator uses the Gemini API to explain what a holiday
means and how to greet people on it.

We call Gemini through plain HTTP using the requests library (same as
the holiday client), so there is nothing extra to install.
Get a free key at https://aistudio.google.com and put it in a .env file.
"""

import json
import os
import re
import time

import requests


class GuideError(Exception):
    """Something went wrong while getting the AI explanation."""


class CultureGuideGenerator:
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key=None, model=None, timeout=30):
        # Key comes from the .env file (or whatever is passed in)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        # Model name is kept in .env too, so it can be changed if Google renames it
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout = timeout

    def has_key(self):
        return bool(self.api_key.strip())

    # ------------------------------------------------------------------
    # Talking to Gemini
    # ------------------------------------------------------------------
    def _post(self, model, body):
        """Send one request to one model. Network problems become GuideErrors."""
        url = self.API_URL.format(model=model)
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        try:
            return requests.post(url, headers=headers, json=body, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise GuideError("Gemini took too long to answer. Please try again.")
        except requests.exceptions.ConnectionError:
            raise GuideError("Could not reach Gemini. Check your internet connection.")
        except requests.exceptions.RequestException as error:
            raise GuideError(f"The request to Gemini failed: {error}")

    def _find_other_models(self):
        """
        Google retires old models and new keys can't always use them (that
        gives a 404). So ask Google which models exist and return a few
        "flash" text models to try instead, newest first.
        """
        try:
            response = requests.get(
                self.MODELS_URL,
                headers={"x-goog-api-key": self.api_key},
                params={"pageSize": 200},
                timeout=self.timeout,
            )
            items = response.json().get("models", [])
        except (requests.exceptions.RequestException, ValueError, AttributeError):
            return []

        # Names containing these words are for images, voice, etc., not text
        skip_words = ("image", "tts", "audio", "live", "embedding", "vision",
                      "robotics", "computer", "imagen", "veo", "aqa")
        names = []
        for item in items:
            name = str(item.get("name", "")).replace("models/", "")
            can_generate = "generateContent" in item.get("supportedGenerationMethods", [])
            if can_generate and "flash" in name and name != self.model \
                    and not any(word in name for word in skip_words):
                names.append(name)

        names.sort(reverse=True)  # highest version number first
        # Stable models go before preview/experimental ones (sort keeps the order inside each group)
        names.sort(key=lambda n: ("preview" in n or "exp" in n))
        return names[:4]

    @staticmethod
    def _google_message(response):
        """Pull Google's own explanation out of an error response, if there is one."""
        try:
            return str(response.json()["error"]["message"])[:200]
        except (ValueError, KeyError, TypeError):
            return ""

    def _ask_gemini(self, prompt, as_json=False):
        """Send a prompt to Gemini and return the text it answers with."""
        if not self.has_key():
            raise GuideError("No Gemini API key found. Add GEMINI_API_KEY to your .env file.")

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4},
        }
        if as_json:
            # Asks Gemini to reply with JSON only, which is easier to read in code
            body["generationConfig"]["responseMimeType"] = "application/json"

        response = self._post(self.model, body)

        # 404 means this model name isn't available for this key, so try others
        if response.status_code == 404:
            for other_model in self._find_other_models():
                response = self._post(other_model, body)
                if response.status_code != 404:
                    self.model = other_model   # remember the one that worked
                    break

        # 500, 502, 503 and 504 mean Google's servers are busy for a moment.
        # Wait a little and try again (2, then 4, then 8 seconds) before giving up.
        for seconds in (2, 4, 8):
            if response.status_code not in (500, 502, 503, 504):
                break
            time.sleep(seconds)
            response = self._post(self.model, body)

        if response.status_code in (500, 502, 503, 504):
            raise GuideError("Google's Gemini servers are busy right now. "
                             "Please wait a minute and try again.")

        if response.status_code in (400, 403):
            raise GuideError("Gemini rejected the request. Your API key may be wrong or not allowed. "
                             + self._google_message(response))
        if response.status_code == 429:
            raise GuideError("Too many requests to Gemini right now. Wait a minute and try again.")
        if response.status_code == 404:
            raise GuideError("Gemini could not find a model this key can use "
                             f"(tried {self.model}). " + self._google_message(response))
        if not response.ok:
            raise GuideError(f"Gemini returned an error (status {response.status_code}). "
                             + self._google_message(response))

        # The answer sits deep inside the JSON, so dig for it carefully.
        try:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError):
            raise GuideError("Gemini sent back an answer we couldn't read (it may have been blocked).")

        return text.strip()

    @staticmethod
    def _clean_json_text(text):
        """
        Sometimes the AI wraps its JSON in ```json ... ``` fences or adds a
        sentence before it. This uses regex to strip all that and parse it.
        """
        # Remove the ``` fences if they are there
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Last try: grab everything from the first { to the last }
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise GuideError("The AI answer was not in the format we expected. Please try again.")

    # ------------------------------------------------------------------
    # Features the app uses
    # ------------------------------------------------------------------
    def explain_holiday(self, holiday, country_name):
        """
        Return a dictionary with: meaning, history, greetings (list), customs (list).
        """
        prompt = (
            f"Explain the public holiday '{holiday.name}' as observed in {country_name} "
            f"(date this year: {holiday.date.strftime('%d %B %Y')}).\n"
            "Write for an ordinary person who knows nothing about it. Keep it short and accurate. "
            "If you are not sure about a detail, leave it out instead of guessing.\n"
            "Reply with JSON only, using exactly these keys:\n"
            '{"meaning": "2-3 sentences on what the holiday celebrates or marks",\n'
            ' "history": "2-3 sentences on its cultural or historical background",\n'
            ' "greetings": ["2-3 appropriate greetings, with the local language where it fits"],\n'
            ' "customs": ["3-4 common customs, traditions or etiquette tips"]}'
        )

        data = self._clean_json_text(self._ask_gemini(prompt, as_json=True))

        # Make sure every key exists and lists are really lists,
        # so the UI doesn't crash if the AI forgot one.
        return {
            "meaning": str(data.get("meaning", "")).strip(),
            "history": str(data.get("history", "")).strip(),
            "greetings": self._as_list(data.get("greetings")),
            "customs": self._as_list(data.get("customs")),
        }

    def compare_countries(self, name_a, name_b, year, comparison):
        """
        Short AI write-up on the cultural differences, based on the
        comparison dictionary made by HolidayComparator.
        """
        shared = ", ".join(item["name"] for item in comparison["shared"]) or "none"
        only_a = ", ".join(comparison["only_a"][:12]) or "none"
        only_b = ", ".join(comparison["only_b"][:12]) or "none"

        prompt = (
            f"Compare the public holidays of {name_a} and {name_b} in {year}.\n"
            f"Holidays both countries share: {shared}.\n"
            f"Only in {name_a}: {only_a}.\n"
            f"Only in {name_b}: {only_b}.\n"
            "Write about 150 words in plain language. Cover what the shared holidays show, "
            "what the differences say about each culture, and one practical tip for someone "
            "travelling or working between the two countries. Do not invent facts."
        )
        return self._ask_gemini(prompt)

    @staticmethod
    def _as_list(value):
        """Turn whatever the AI gave us into a clean list of strings."""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
