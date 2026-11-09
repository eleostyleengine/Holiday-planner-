# Public Holiday & Cultural Awareness Planner

Python Advanced Cohort 39, Group 6.
LIVE APP:
https://holidayplannerg6.streamlit.app/


A Streamlit app where you pick a country and a year, see its public
holidays in a calendar, and use Gemini AI to learn what each holiday
means and how to greet people. You can also compare two countries and
save guides and comparisons to local files.

## How to run

1. Install Python 3.10 or newer (python.org). Tick "Add Python to PATH".
2. Open this folder in VS Code.
3. Start the app, either way:
   - Windows: double-click `start_windows.bat`
   - Or in the VS Code terminal:
     ```
     pip install -r requirements.txt
     streamlit run app.py
     ```
4. Get a free Gemini key at https://aistudio.google.com and paste it into the
   sidebar box in the app. (Or copy `.env.example` to `.env` and put it there.)

The holiday data works without a key. Only the AI explanations need it.
If Streamlit asks for an email the first time, just press Enter.

## Files and classes

| File | Class | Job |
|---|---|---|
| `models.py` | `Country`, `Holiday` | Hold the data |
| `api_client.py` | `HolidayAPIClient` | Get holidays from the Nager.Date API |
| `culture_guide.py` | `CultureGuideGenerator` | Ask Gemini to explain a holiday or compare two countries |
| `comparison.py` | `HolidayComparator` | Find shared holidays, overlapping dates and differences |
| `storage.py` | `LocalStorage` | Save favourites, guides and comparisons as JSON |
| `validators.py` | (functions) | Regex checks for country codes and years |
| `app.py` | (Streamlit UI) | The screen the user sees |

## Where each project requirement is covered

- **File handling:** `storage.py` saves to `data/*.json`; the app can also download text files.
- **Exception handling:** custom errors (`InvalidInputError`, `HolidayAPIError`, `UnsupportedCountryError`, `GuideError`, `StorageError`) cover bad codes, invalid years, unsupported countries, network failures and a damaged save file.
- **Regular expressions:** `validators.py` checks codes (`NG`, `US`, `GB`) and years (`2026`); `culture_guide.py` cleans the AI's JSON; `comparison.py` normalises holiday names before matching.
- **OOP:** the classes in the table above.

## APIs

- Nager.Date: https://date.nager.at (free, no key)
- Gemini API: https://ai.google.dev
