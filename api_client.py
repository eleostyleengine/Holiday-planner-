"""
api_client.py
-------------
HolidayAPIClient talks to the Nager.Date API (free, no key needed).
Docs: https://date.nager.at

Everything that can go wrong with a web request (no internet, slow
server, unknown country, bad response) is turned into one of our own
errors with a friendly message, so the app never crashes with a
scary traceback.
"""

import requests

from models import Country, Holiday


class HolidayAPIError(Exception):
    """Something went wrong while talking to the holiday API."""


class UnsupportedCountryError(HolidayAPIError):
    """The API doesn't have holiday data for that country code."""


class HolidayAPIClient:
    BASE_URL = "https://date.nager.at/api/v3"

    def __init__(self, timeout=10):
        self.timeout = timeout            # seconds to wait before giving up
        self.session = requests.Session()  # reuses the connection between calls

    def _get(self, path):
        """
        Private helper: send a GET request and return the JSON.
        Both public methods below use it, so the error handling is
        written only once.
        """
        url = f"{self.BASE_URL}{path}"

        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise HolidayAPIError("The holiday service took too long to respond. Please try again.")
        except requests.exceptions.ConnectionError:
            raise HolidayAPIError("Could not connect to the holiday service. Check your internet connection.")
        except requests.exceptions.RequestException as error:
            raise HolidayAPIError(f"The request failed: {error}")

        # 404 = the API doesn't know this country code
        if response.status_code == 404:
            raise UnsupportedCountryError("That country is not supported by the holiday service.")

        # 204 = the request worked but there is nothing to return
        if response.status_code == 204:
            return []

        # 400 = the API didn't like the request (bad code or year)
        if response.status_code == 400:
            raise HolidayAPIError("The holiday service rejected the request. Check the country code and year.")

        if not response.ok:
            raise HolidayAPIError(f"The holiday service returned an error (status {response.status_code}).")

        try:
            return response.json()
        except ValueError:
            raise HolidayAPIError("The holiday service sent back data we couldn't read.")

    def get_available_countries(self):
        """Return a list of Country objects for every supported country."""
        data = self._get("/AvailableCountries")

        countries = []
        for item in data:
            # Skip any entry that is missing a field instead of crashing
            if "countryCode" in item and "name" in item:
                countries.append(Country(item["countryCode"], item["name"]))

        return sorted(countries, key=lambda c: c.name)

    def get_holidays(self, country_code, year):
        """Return a list of Holiday objects for the country and year, sorted by date."""
        data = self._get(f"/PublicHolidays/{year}/{country_code}")

        if not data:
            raise HolidayAPIError(f"No holidays were found for {country_code} in {year}.")

        holidays = []
        for item in data:
            try:
                holidays.append(Holiday.from_api(item))
            except (KeyError, ValueError):
                # One bad record shouldn't ruin the whole list, so skip it
                continue

        if not holidays:
            raise HolidayAPIError("The holiday data came back in an unexpected format.")

        return sorted(holidays, key=lambda h: h.date)
