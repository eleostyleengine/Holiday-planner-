"""
storage.py
----------
LocalStorage saves the user's favourite countries, holiday guides and
comparison results in JSON files inside the "data" folder, so they are
still there the next time the app is opened.
"""

import json
import os
from datetime import datetime


class StorageError(Exception):
    """Reading or writing a save file failed."""


class LocalStorage:
    def __init__(self, folder="data"):
        # Put the data folder next to this file, whatever directory the app is started from
        base = os.path.dirname(os.path.abspath(__file__))
        self.folder = os.path.join(base, folder)
        os.makedirs(self.folder, exist_ok=True)

        self.favourites_file = os.path.join(self.folder, "favourites.json")
        self.guides_file = os.path.join(self.folder, "guides.json")
        self.comparisons_file = os.path.join(self.folder, "comparisons.json")

    # ------------------------------------------------------------------
    # Low-level read / write
    # ------------------------------------------------------------------
    def _read(self, path):
        """Return the list stored in a file (an empty list if there is none yet)."""
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            # The file got damaged. Keep a copy of it and start fresh
            # instead of crashing the whole app.
            os.replace(path, path + ".bak")
            return []
        except OSError as error:
            raise StorageError(f"Could not read {os.path.basename(path)}: {error}")

        return data if isinstance(data, list) else []

    def _write(self, path, items):
        """Write the list to disk. Writes to a temp file first so a crash can't half-save."""
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(items, file, indent=2, ensure_ascii=False)
            os.replace(temp_path, path)
        except OSError as error:
            raise StorageError(f"Could not save {os.path.basename(path)}: {error}")

    # ------------------------------------------------------------------
    # Favourite countries
    # ------------------------------------------------------------------
    def get_favourites(self):
        return self._read(self.favourites_file)

    def add_favourite(self, code, name):
        """Returns True if added, False if it was already a favourite."""
        favourites = self.get_favourites()
        if any(item["code"] == code for item in favourites):
            return False
        favourites.append({"code": code, "name": name})
        self._write(self.favourites_file, favourites)
        return True

    def remove_favourite(self, code):
        favourites = [item for item in self.get_favourites() if item["code"] != code]
        self._write(self.favourites_file, favourites)

    # ------------------------------------------------------------------
    # Holiday guides
    # ------------------------------------------------------------------
    def get_guides(self):
        return self._read(self.guides_file)

    def save_guide(self, country_name, year, holiday, guide):
        """holiday is a Holiday object, guide is the dictionary from Gemini."""
        guides = self.get_guides()
        guides.append({
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "country": country_name,
            "year": year,
            "holiday": holiday.to_dict(),
            "guide": guide,
        })
        self._write(self.guides_file, guides)

    def delete_guide(self, index):
        guides = self.get_guides()
        if 0 <= index < len(guides):
            guides.pop(index)
            self._write(self.guides_file, guides)

    # ------------------------------------------------------------------
    # Comparison results
    # ------------------------------------------------------------------
    def get_comparisons(self):
        return self._read(self.comparisons_file)

    def save_comparison(self, year, comparison, ai_summary=""):
        comparisons = self.get_comparisons()
        comparisons.append({
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "year": year,
            "comparison": comparison,
            "ai_summary": ai_summary,
        })
        self._write(self.comparisons_file, comparisons)

    def delete_comparison(self, index):
        comparisons = self.get_comparisons()
        if 0 <= index < len(comparisons):
            comparisons.pop(index)
            self._write(self.comparisons_file, comparisons)


# ----------------------------------------------------------------------
# Plain-text versions, used for the "Download" buttons
# ----------------------------------------------------------------------
def guide_to_text(country_name, year, holiday_name, holiday_date, guide):
    lines = [
        f"{holiday_name} - {country_name} {year}",
        f"Date: {holiday_date}",
        "",
        "What it means",
        guide.get("meaning", ""),
        "",
        "Background",
        guide.get("history", ""),
        "",
        "Greetings",
    ]
    lines += [f"- {item}" for item in guide.get("greetings", [])]
    lines += ["", "Customs"]
    lines += [f"- {item}" for item in guide.get("customs", [])]
    return "\n".join(lines)


def comparison_to_text(year, comparison, ai_summary=""):
    a, b = comparison["country_a"], comparison["country_b"]
    lines = [
        f"Holiday comparison: {a['name']} vs {b['name']} ({year})",
        f"{a['name']}: {a['total']} holidays | {b['name']}: {b['total']} holidays",
        "",
        "Shared holidays",
    ]
    lines += [f"- {i['name']} ({i['date_a']} / {i['date_b']})" for i in comparison["shared"]] or ["- none"]
    lines += ["", "Different holidays on the same date"]
    lines += [f"- {i['date']}: {i['holiday_a']} / {i['holiday_b']}" for i in comparison["overlapping"]] or ["- none"]
    lines += ["", f"Only in {a['name']}"] + [f"- {n}" for n in comparison["only_a"]]
    lines += ["", f"Only in {b['name']}"] + [f"- {n}" for n in comparison["only_b"]]
    if ai_summary:
        lines += ["", "Cultural notes", ai_summary]
    return "\n".join(lines)
