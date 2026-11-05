"""
validators.py
-------------
All the input checking lives here, so the rest of the app can trust that
whatever reaches it is already clean. This is where the regular
expressions (regex) part of the project is used.
"""

import re


class InvalidInputError(Exception):
    """Raised when the user types something we can't accept."""


# A country code is exactly two letters, e.g. NG, US, GB.
# ^ and $ mean the WHOLE text must match, not just a part of it.
COUNTRY_CODE_PATTERN = re.compile(r"^[A-Za-z]{2}$")

# A year is exactly four digits, e.g. 2026.
YEAR_PATTERN = re.compile(r"^\d{4}$")

# The Nager.Date API only has data for a limited range of years,
# so we stop people from asking for something it can't answer.
MIN_YEAR = 1975
MAX_YEAR = 2075


def validate_country_code(raw_code):
    """Check the country code and return it in capital letters (ng -> NG)."""
    code = str(raw_code).strip()

    if not code:
        raise InvalidInputError("Please enter a country code, for example NG, US or GB.")

    if not COUNTRY_CODE_PATTERN.match(code):
        raise InvalidInputError(
            f"'{code}' is not a valid country code. Use exactly two letters, like NG, US or GB."
        )

    return code.upper()


def validate_year(raw_year):
    """Check the year is four digits and inside the range the API supports."""
    text = str(raw_year).strip()

    if not text:
        raise InvalidInputError("Please enter a year, for example 2026.")

    if not YEAR_PATTERN.match(text):
        raise InvalidInputError(f"'{text}' is not a valid year. Use four digits, like 2026.")

    year = int(text)
    if year < MIN_YEAR or year > MAX_YEAR:
        raise InvalidInputError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}.")

    return year
