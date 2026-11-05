"""
comparison.py
-------------
HolidayComparator takes the holiday lists of two countries (for the same
year) and works out what they have in common and what is different.
"""

import re


class HolidayComparator:
    def __init__(self, country_a, holidays_a, country_b, holidays_b):
        self.country_a = country_a      # Country objects
        self.country_b = country_b
        self.holidays_a = holidays_a    # lists of Holiday objects
        self.holidays_b = holidays_b

    @staticmethod
    def _normalise(name):
        """
        Make names easier to match: lowercase and drop everything that
        isn't a letter or number. "New Year's Day" and "New Years Day"
        both become "newyearsday".
        """
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def find_shared(self):
        """Holidays with the same name in both countries."""
        lookup_b = {self._normalise(h.name): h for h in self.holidays_b}

        shared = []
        for holiday in self.holidays_a:
            match = lookup_b.get(self._normalise(holiday.name))
            if match:
                shared.append({
                    "name": holiday.name,
                    "date_a": holiday.date.isoformat(),
                    "date_b": match.date.isoformat(),
                    "same_date": holiday.date == match.date,
                })
        return shared

    def find_overlapping_dates(self):
        """
        Different holidays that fall on the same day of the year.
        Holidays with the same name are left out because they already
        show up in find_shared().
        """
        by_day_b = {}
        for holiday in self.holidays_b:
            by_day_b.setdefault((holiday.date.month, holiday.date.day), []).append(holiday)

        overlaps = []
        for holiday in self.holidays_a:
            matches = by_day_b.get((holiday.date.month, holiday.date.day), [])
            for other in matches:
                if self._normalise(holiday.name) != self._normalise(other.name):
                    overlaps.append({
                        "date": holiday.date.strftime("%d %b"),
                        "holiday_a": holiday.name,
                        "holiday_b": other.name,
                    })
        return overlaps

    def find_unique(self):
        """Names that appear in only one of the two countries."""
        names_a = {self._normalise(h.name) for h in self.holidays_a}
        names_b = {self._normalise(h.name) for h in self.holidays_b}

        only_a = [h.name for h in self.holidays_a if self._normalise(h.name) not in names_b]
        only_b = [h.name for h in self.holidays_b if self._normalise(h.name) not in names_a]
        return only_a, only_b

    def compare(self):
        """Run everything and return one dictionary (easy to show and to save as JSON)."""
        only_a, only_b = self.find_unique()
        return {
            "country_a": {"code": self.country_a.code, "name": self.country_a.name,
                          "total": len(self.holidays_a)},
            "country_b": {"code": self.country_b.code, "name": self.country_b.name,
                          "total": len(self.holidays_b)},
            "shared": self.find_shared(),
            "overlapping": self.find_overlapping_dates(),
            "only_a": only_a,
            "only_b": only_b,
        }
