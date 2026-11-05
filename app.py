"""
app.py
------
The Streamlit screen of the Public Holiday & Cultural Awareness Planner.
Run it with:   streamlit run app.py

This file only deals with what the user sees. The real work is done by
the classes in the other files:
    HolidayAPIClient      (api_client.py)    gets holidays from Nager.Date
    CultureGuideGenerator (culture_guide.py) asks Gemini to explain them
    HolidayComparator     (comparison.py)    compares two countries
    LocalStorage          (storage.py)       saves things to JSON files
"""

import calendar
from datetime import date

import streamlit as st
from dotenv import load_dotenv

from api_client import HolidayAPIClient, HolidayAPIError
from comparison import HolidayComparator
from culture_guide import CultureGuideGenerator, GuideError
from models import Country
from storage import LocalStorage, StorageError, comparison_to_text, guide_to_text
from validators import InvalidInputError, validate_country_code, validate_year

# Reads the .env file so GEMINI_API_KEY is available
load_dotenv()

st.set_page_config(page_title="Holiday & Culture Planner", layout="wide")


# ----------------------------------------------------------------------
# Shared objects. cache_resource means Streamlit creates them once and
# reuses them, instead of rebuilding them every time the page reruns.
# ----------------------------------------------------------------------
@st.cache_resource
def get_client():
    return HolidayAPIClient()


@st.cache_resource
def get_generator():
    return CultureGuideGenerator()


@st.cache_resource
def get_storage():
    return LocalStorage()


# cache_data remembers the RESULT of a function for a while, so we don't
# hit the API again for the same country and year.
@st.cache_data(ttl=3600, show_spinner=False)
def load_holidays(code, year):
    return get_client().get_holidays(code, year)


@st.cache_data(ttl=86400, show_spinner=False)
def load_country_names():
    """Dictionary like {"NG": "Nigeria"}. Returns {} if the list can't be loaded."""
    try:
        return {c.code: c.name for c in get_client().get_available_countries()}
    except HolidayAPIError:
        return {}


# ----------------------------------------------------------------------
# Small helper functions for the screen
# ----------------------------------------------------------------------
def holiday_rows(holidays):
    """Turn Holiday objects into plain rows for st.dataframe."""
    return [
        {
            "Date": h.date.strftime("%a, %d %b %Y"),
            "Holiday": h.name,
            "Local name": h.local_name,
            "Type": h.type_label,
            "Applies to": h.scope_label,
        }
        for h in holidays
    ]


def month_calendar(year, month, holidays):
    """
    Draw one month as a markdown table. Days that have a holiday are
    shown in red and bold. Returns (table_text, list_of_holidays_in_month).
    """
    in_month = [h for h in holidays if h.date.month == month]
    holiday_days = {h.date.day for h in in_month}

    lines = [
        "| Mon | Tue | Wed | Thu | Fri | Sat | Sun |",
        "|---|---|---|---|---|---|---|",
    ]
    # monthdayscalendar gives weeks as lists of day numbers (0 = not in this month)
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        cells = []
        for day in week:
            if day == 0:
                cells.append(" ")
            elif day in holiday_days:
                cells.append(f":red[**{day}**]")
            else:
                cells.append(str(day))
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines), in_month


def next_holiday(holidays):
    """The first holiday that is today or later (None if the year is over)."""
    today = date.today()
    for h in holidays:
        if h.date >= today:
            return h
    return None


def show_guide(guide):
    """Display the dictionary returned by CultureGuideGenerator.explain_holiday."""
    st.markdown("**What it means**")
    st.write(guide["meaning"] or "No information returned.")
    st.markdown("**Background**")
    st.write(guide["history"] or "No information returned.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Greetings**")
        for item in guide["greetings"]:
            st.markdown(f"- {item}")
    with col2:
        st.markdown("**Customs**")
        for item in guide["customs"]:
            st.markdown(f"- {item}")


# ----------------------------------------------------------------------
# Page layout
# ----------------------------------------------------------------------
st.title("Public Holiday & Cultural Awareness Planner")
st.caption("Look up public holidays, learn what they mean, and compare countries.")

storage = get_storage()

# The sidebar lets the user paste their Gemini key straight into the app,
# so they don't have to edit any file. It only lives in memory while the
# app is open and is never written to disk.
with st.sidebar:
    st.header("Gemini API key")
    typed_key = st.text_input("Paste your key here", type="password",
                              help="Free key from aistudio.google.com")
    st.caption("Needed only for the AI explanations. It is not saved anywhere.")

if typed_key.strip():
    generator = CultureGuideGenerator(api_key=typed_key.strip())
else:
    # No key typed, so fall back to the one in the .env file (if there is one)
    generator = get_generator()

if not generator.has_key():
    st.warning(
        "No Gemini API key yet, so the AI explanations are switched off. "
        "Paste your key in the sidebar on the left (or put it in the .env file)."
    )

tab_holidays, tab_compare, tab_saved = st.tabs(["Holidays", "Compare countries", "Saved"])


# ======================================================================
# TAB 1: holidays for one country
# ======================================================================
with tab_holidays:
    with st.form("holiday_form"):
        col1, col2 = st.columns(2)
        code_input = col1.text_input("Country code", value="NG", max_chars=2,
                                     help="Two letters, e.g. NG, US, GB")
        year_input = col2.text_input("Year", value=str(date.today().year), max_chars=4)
        submitted = st.form_submit_button("Show holidays")

    if submitted:
        try:
            code = validate_country_code(code_input)
            year = validate_year(year_input)
            holidays = load_holidays(code, year)

            # Keep the result in session_state, because Streamlit reruns this
            # whole file every time a button is pressed and would forget it.
            st.session_state["current"] = {
                "code": code,
                "name": load_country_names().get(code, code),
                "year": year,
                "holidays": holidays,
            }
            st.session_state.pop("guide", None)   # old guide belongs to the old search
        except (InvalidInputError, HolidayAPIError) as error:
            st.session_state.pop("current", None)
            st.error(str(error))

    current = st.session_state.get("current")

    if current:
        holidays = current["holidays"]
        st.subheader(f"{current['name']} - {current['year']}")

        stat1, stat2 = st.columns(2)
        stat1.metric("Public holidays", len(holidays))
        upcoming = next_holiday(holidays)
        if upcoming:
            stat2.metric("Next holiday", upcoming.name)
            stat2.caption(upcoming.date.strftime("%A, %d %B %Y"))
        else:
            stat2.metric("Next holiday", "None left this year")

        # --- calendar view ---
        st.markdown("#### Calendar")
        month = st.selectbox(
            "Month", list(range(1, 13)),
            index=(date.today().month - 1) if current["year"] == date.today().year else 0,
            format_func=lambda m: calendar.month_name[m],
        )
        table, in_month = month_calendar(current["year"], month, holidays)
        cal_col, list_col = st.columns([3, 2])
        cal_col.markdown(table)
        with list_col:
            if in_month:
                for h in in_month:
                    st.markdown(f"**{h.date.day} {calendar.month_abbr[month]}** - {h.name}")
            else:
                st.write("No holidays this month.")

        # --- full list ---
        st.markdown("#### All holidays")
        st.dataframe(holiday_rows(holidays), hide_index=True)

        # --- favourites ---
        if st.button(f"Add {current['name']} to favourites"):
            try:
                if storage.add_favourite(current["code"], current["name"]):
                    st.success("Added to favourites.")
                else:
                    st.info("It is already in your favourites.")
            except StorageError as error:
                st.error(str(error))

        # --- AI explanation for one holiday ---
        st.markdown("#### Explain a holiday")
        chosen = st.selectbox("Pick a holiday", holidays, format_func=str)

        if st.button("Explain this holiday", disabled=not generator.has_key()):
            try:
                with st.spinner("Asking Gemini..."):
                    guide = generator.explain_holiday(chosen, current["name"])
                st.session_state["guide"] = {"holiday": chosen, "guide": guide}
            except GuideError as error:
                st.error(str(error))

        saved_guide = st.session_state.get("guide")
        if saved_guide:
            st.markdown(f"##### {saved_guide['holiday'].name}")
            show_guide(saved_guide["guide"])

            save_col, download_col = st.columns(2)
            if save_col.button("Save this guide"):
                try:
                    storage.save_guide(current["name"], current["year"],
                                       saved_guide["holiday"], saved_guide["guide"])
                    st.success("Guide saved. You can find it in the Saved tab.")
                except StorageError as error:
                    st.error(str(error))

            download_col.download_button(
                "Download as text file",
                data=guide_to_text(current["name"], current["year"],
                                   saved_guide["holiday"].name,
                                   saved_guide["holiday"].date.strftime("%d %B %Y"),
                                   saved_guide["guide"]),
                file_name=f"{saved_guide['holiday'].name}.txt".replace(" ", "_"),
            )


# ======================================================================
# TAB 2: compare two countries
# ======================================================================
with tab_compare:
    with st.form("compare_form"):
        col1, col2, col3 = st.columns(3)
        code_a_input = col1.text_input("First country code", value="NG", max_chars=2)
        code_b_input = col2.text_input("Second country code", value="GB", max_chars=2)
        year_cmp_input = col3.text_input("Year", value=str(date.today().year), max_chars=4)
        compare_clicked = st.form_submit_button("Compare")

    if compare_clicked:
        try:
            code_a = validate_country_code(code_a_input)
            code_b = validate_country_code(code_b_input)
            year_cmp = validate_year(year_cmp_input)

            if code_a == code_b:
                raise InvalidInputError("Please choose two different countries.")

            names = load_country_names()
            country_a = Country(code_a, names.get(code_a, code_a))
            country_b = Country(code_b, names.get(code_b, code_b))

            comparator = HolidayComparator(
                country_a, load_holidays(code_a, year_cmp),
                country_b, load_holidays(code_b, year_cmp),
            )
            st.session_state["comparison"] = {
                "year": year_cmp,
                "data": comparator.compare(),
                "ai_summary": "",
            }
        except (InvalidInputError, HolidayAPIError) as error:
            st.session_state.pop("comparison", None)
            st.error(str(error))

    result = st.session_state.get("comparison")

    if result:
        data = result["data"]
        name_a, name_b = data["country_a"]["name"], data["country_b"]["name"]

        st.subheader(f"{name_a} vs {name_b} ({result['year']})")

        m1, m2, m3 = st.columns(3)
        m1.metric(f"{name_a} holidays", data["country_a"]["total"])
        m2.metric(f"{name_b} holidays", data["country_b"]["total"])
        m3.metric("Shared holidays", len(data["shared"]))

        st.markdown("#### Shared celebrations")
        if data["shared"]:
            st.dataframe(
                [{"Holiday": i["name"], name_a: i["date_a"], name_b: i["date_b"],
                  "Same date": "Yes" if i["same_date"] else "No"} for i in data["shared"]],
                hide_index=True,
            )
        else:
            st.write("These two countries have no holidays with the same name.")

        st.markdown("#### Different holidays on the same date")
        if data["overlapping"]:
            st.dataframe(
                [{"Date": i["date"], name_a: i["holiday_a"], name_b: i["holiday_b"]}
                 for i in data["overlapping"]],
                hide_index=True,
            )
        else:
            st.write("No overlapping dates.")

        only_col_a, only_col_b = st.columns(2)
        with only_col_a:
            st.markdown(f"#### Only in {name_a}")
            for name in data["only_a"]:
                st.markdown(f"- {name}")
        with only_col_b:
            st.markdown(f"#### Only in {name_b}")
            for name in data["only_b"]:
                st.markdown(f"- {name}")

        # --- optional AI write-up ---
        st.markdown("#### Cultural notes")
        if st.button("Generate cultural comparison", disabled=not generator.has_key()):
            try:
                with st.spinner("Asking Gemini..."):
                    result["ai_summary"] = generator.compare_countries(
                        name_a, name_b, result["year"], data)
            except GuideError as error:
                st.error(str(error))

        if result["ai_summary"]:
            st.write(result["ai_summary"])

        save_col, download_col = st.columns(2)
        if save_col.button("Save this comparison"):
            try:
                storage.save_comparison(result["year"], data, result["ai_summary"])
                st.success("Comparison saved. You can find it in the Saved tab.")
            except StorageError as error:
                st.error(str(error))

        download_col.download_button(
            "Download as text file",
            data=comparison_to_text(result["year"], data, result["ai_summary"]),
            file_name=f"{data['country_a']['code']}_vs_{data['country_b']['code']}_{result['year']}.txt",
        )


# ======================================================================
# TAB 3: everything the user has saved
# ======================================================================
with tab_saved:
    try:
        favourites = storage.get_favourites()
        guides = storage.get_guides()
        comparisons = storage.get_comparisons()
    except StorageError as error:
        st.error(str(error))
        favourites, guides, comparisons = [], [], []

    st.subheader("Favourite countries")
    if not favourites:
        st.write("Nothing here yet. Add a country from the Holidays tab.")
    for item in favourites:
        fav_col, btn_col = st.columns([4, 1])
        fav_col.write(f"{item['name']} ({item['code']})")
        if btn_col.button("Remove", key=f"remove_fav_{item['code']}"):
            storage.remove_favourite(item["code"])
            st.rerun()

    st.subheader("Saved holiday guides")
    if not guides:
        st.write("No saved guides yet.")
    for index, item in enumerate(guides):
        title = f"{item['holiday']['name']} - {item['country']} {item['year']}"
        with st.expander(title):
            st.caption(f"Saved {item['saved_at']}")
            show_guide(item["guide"])
            if st.button("Delete", key=f"delete_guide_{index}"):
                storage.delete_guide(index)
                st.rerun()

    st.subheader("Saved comparisons")
    if not comparisons:
        st.write("No saved comparisons yet.")
    for index, item in enumerate(comparisons):
        a, b = item["comparison"]["country_a"], item["comparison"]["country_b"]
        with st.expander(f"{a['name']} vs {b['name']} ({item['year']})"):
            st.caption(f"Saved {item['saved_at']}")
            st.text(comparison_to_text(item["year"], item["comparison"], item["ai_summary"]))
            if st.button("Delete", key=f"delete_comparison_{index}"):
                storage.delete_comparison(index)
                st.rerun()
