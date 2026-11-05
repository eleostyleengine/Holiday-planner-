"""
models.py
---------
The two data classes the whole app is built around: Country and Holiday.
They only hold data and know how to describe themselves; they don't talk
to the internet or the disk.
"""

from datetime import date


class Country:
    """A country the holiday API supports."""

    def __init__(self, code, name):
        self.code = code      # two-letter code, e.g. "NG"
        self.name = name      # full name, e.g. "Nigeria"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Holiday:
    """One public holiday for one country on one date."""

    def __init__(self, name, local_name, holiday_date, country_code,
                 types=None, is_global=True):
        self.name = name                    # English name
        self.local_name = local_name        # name in the local language
        self.date = holiday_date            # a datetime.date object
        self.country_code = country_code
        self.types = types or ["Public"]    # e.g. ["Public"], ["Bank"], ["Optional"]
        self.is_global = is_global          # False means it only applies in some regions

    @classmethod
    def from_api(cls, data):
        """
        Build a Holiday from one item of the API's JSON response.
        Raises KeyError / ValueError if the item is missing the date or the
        date is badly formatted; the API client catches that and skips the item.
        """
        # The API sends dates like "2026-12-25", so fromisoformat handles it.
        holiday_date = date.fromisoformat(data["date"])

        # Newer versions of the API send "types" (a list). Older ones sent
        # "type" (a single string). Handle both so we don't break.
        types = data.get("types")
        if not types and data.get("type"):
            types = [data["type"]]

        return cls(
            name=data.get("name") or data.get("localName") or "Unnamed holiday",
            local_name=data.get("localName") or "",
            holiday_date=holiday_date,
            country_code=data.get("countryCode", ""),
            types=types,
            is_global=data.get("global", True),
        )

    @property
    def type_label(self):
        """Types as one readable string, e.g. 'Public, Bank'."""
        return ", ".join(self.types)

    @property
    def scope_label(self):
        return "Nationwide" if self.is_global else "Some regions only"

    def to_dict(self):
        """Plain dictionary version, used when saving to JSON files."""
        return {
            "name": self.name,
            "local_name": self.local_name,
            "date": self.date.isoformat(),
            "country_code": self.country_code,
            "types": self.types,
            "is_global": self.is_global,
        }

    def __str__(self):
        return f"{self.date.strftime('%d %b %Y')} - {self.name}"
