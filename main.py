import sys
import os
import json
import requests
from datetime import datetime, timedelta

# Fix Windows PowerShell console encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def load_config():
    """
    Loads configuration settings from config.json.
    Falls back to config.example.json if config.json is not found.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    example_path = os.path.join(base_dir, "config.example.json")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif os.path.exists(example_path):
        print("⚠️ config.json not found. Using template values from config.example.json...")
        with open(example_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise FileNotFoundError("Neither config.json nor config.example.json was found!")

CONFIG = load_config()

LOCATION_ID = CONFIG.get("location_id", "7408")
# Standard public Cineplex Azure API Management subscription key
SUBSCRIPTION_KEY = CONFIG.get("subscription_key", "dcdac5601d864addbc2675a2e96cb1f8")
MOVIE_NAME = CONFIG.get("movie_name", "The Odyssey")
REQUIRED_FORMATS = CONFIG.get("required_formats", ["70mm", "IMAX"])
TARGET_ROWS = [row.upper() for row in CONFIG.get("target_rows", ["E", "F", "G", "H", "I", "J", "K", "L", "M"])]
EXCLUDE_ACCESSIBILITY = CONFIG.get("exclude_accessibility_seats", True)
EXCLUDED_SEATS = set(CONFIG.get("excluded_seat_labels", ["EC1", "EW1", "EW2", "EC4", "EC21", "EW3", "EW4", "EC24"]))
WEBHOOK_URL = CONFIG.get("webhook_url", "")
WEEKDAY_START_HOUR = CONFIG.get("weekday_start_hour", 16) # Default 4:00 PM (16)
WEEKDAY_END_HOUR = CONFIG.get("weekday_end_hour", 20)     # Default 8:00 PM (20)
MIN_CONSECUTIVE_SEATS = CONFIG.get("min_consecutive_seats", 2)
SHOW_SEAT_MAP = CONFIG.get("show_seat_map", True)
SEND_NO_SHOWTIMES_ALERT = CONFIG.get("send_no_showtimes_alert", True)
ONLY_NOTIFY_ON_SEAT_CHANGE = CONFIG.get("only_notify_on_seat_change", True)

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seat_cache.json")

def load_seat_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            safe_print(f"⚠️ Error reading seat_cache.json: {e}")
    return {}

def save_seat_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        safe_print(f"⚠️ Error saving seat_cache.json: {e}")

# Parse Start Date
start_date_val = CONFIG.get("start_date", "today")
if not start_date_val or str(start_date_val).lower() == "today":
    START_DATE = datetime.now()
else:
    try:
        START_DATE = datetime.strptime(str(start_date_val), "%Y-%m-%d")
    except ValueError:
        START_DATE = datetime.now()

# Parse End Date
end_date_val = CONFIG.get("end_date", "2026-08-30")
try:
    END_DATE = datetime.strptime(str(end_date_val), "%Y-%m-%d")
except ValueError:
    END_DATE = datetime(datetime.now().year, 8, 30)


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))

def send_alert(message):
    safe_print(f"ALERT:\n{message}")
    if "discord.com/api/webhooks" in WEBHOOK_URL:
        try:
            res = requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
            if res.status_code == 204:
                safe_print("Successfully delivered alert to Discord webhook!")
            else:
                safe_print(f"Webhook response status: {res.status_code}")
        except Exception as err:
            safe_print(f"Failed to send webhook alert: {err}")

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY
    }

def build_visual_seat_map(layout_data, avail_data):
    """
    Renders a visual graphic seat map for Discord display.
    """
    standard_seats = layout_data.get("standardSeats", {})
    rows = standard_seats.get("rows", [])

    map_lines = ["                          `  ` ═════════════ 🎬 **SCREEN** 🎬 ═════════════ `  `\n"]
    prev_row_label = None

    for row in rows:
        raw_label = row.get("label")
        if not raw_label:
            continue

        row_label = str(raw_label).upper()
        if row_label not in TARGET_ROWS:
            continue

        if prev_row_label == 'E' and row_label == 'F':
            map_lines.append("")

        prev_row_label = row_label
        seats = row.get("seats", [])
        row_emojis = []

        for seat in seats:
            seat_id = seat.get("id")
            seat_label = seat.get("label", "")
            seat_type = seat.get("type", "")

            is_accessible = seat_type.lower() in ["wheelchair", "companion"] or str(seat_label).upper().startswith(("EC", "EW"))
            status = str(avail_data.get(seat_id, "Occupied")).lower()

            if is_accessible:
                row_emojis.append("♿")
            elif status == "available":
                row_emojis.append("🟦")
            else:
                row_emojis.append("⬛")

        row_str = "".join(row_emojis)

        if row_label == 'E':
            map_lines.append(f"`E`              {row_str}                   `E`")
        else:
            map_lines.append(f"`{row_label}` {row_str} `{row_label}`")

    return "\n".join(map_lines)

def check_seats_for_session(showtime_id, date_str, time_str, exp_name, seat_cache):
    layout_url = f"https://apis.cineplex.com/prod/ticketing/api/v1/theatre/{LOCATION_ID}/showtime/{showtime_id}/seat-layout"
    avail_url = f"https://apis.cineplex.com/prod/ticketing/api/v1/theatre/{LOCATION_ID}/showtime/{showtime_id}/seat-availability"
    headers = get_headers()
    sid_str = str(showtime_id)

    try:
        r_layout = requests.get(layout_url, headers=headers, timeout=10)
        r_avail = requests.get(avail_url, headers=headers, timeout=10)

        if r_layout.status_code == 200 and r_avail.status_code == 200:
            layout_data = r_layout.json()
            avail_data = r_avail.json().get("seatAvailabilities", {})

            seat_map_str = ""
            if SHOW_SEAT_MAP:
                seat_map_str = build_visual_seat_map(layout_data, avail_data) + "\n\n"

            standard_seats = layout_data.get("standardSeats", {})
            rows = standard_seats.get("rows", [])
            row_summary = []

            for row in rows:
                raw_label = row.get("label")
                if not raw_label:
                    continue
                row_label = str(raw_label).upper()
                if row_label not in TARGET_ROWS:
                    continue

                consecutive_avail = []
                current_group = []

                for seat in row.get("seats", []):
                    seat_id = seat.get("id")
                    seat_label = seat.get("label", "")
                    seat_type = seat.get("type", "")

                    is_accessible = seat_type.lower() in ["wheelchair", "companion"] or str(seat_label).upper().startswith(("EC", "EW"))

                    if EXCLUDE_ACCESSIBILITY and is_accessible:
                        if len(current_group) >= MIN_CONSECUTIVE_SEATS:
                            consecutive_avail.extend(current_group)
                        current_group = []
                        continue

                    if seat_label in EXCLUDED_SEATS:
                        if len(current_group) >= MIN_CONSECUTIVE_SEATS:
                            consecutive_avail.extend(current_group)
                        current_group = []
                        continue

                    status = str(avail_data.get(seat_id, "Occupied")).lower()
                    if status == "available":
                        current_group.append(seat_label)
                    else:
                        if len(current_group) >= MIN_CONSECUTIVE_SEATS:
                            consecutive_avail.extend(current_group)
                        current_group = []

                if len(current_group) >= MIN_CONSECUTIVE_SEATS:
                    consecutive_avail.extend(current_group)

                if consecutive_avail:
                    row_summary.append(f"💺 Row {row_label}: {', '.join(consecutive_avail)}")

            if row_summary:
                seats_text = "\n".join(row_summary)
                alert_msg = (
                    f"🚨 **Seats Found for {MOVIE_NAME} ({exp_name})!**\n"
                    f"📅 **Date:** {date_str} | ⏰ **Time:** {time_str}\n"
                    f"🎟️ **Session ID:** {showtime_id}\n\n"
                    f"{seat_map_str}"
                    f"**Available Rows:**\n{seats_text}"
                )

                cached_seats = seat_cache.get(sid_str)
                if ONLY_NOTIFY_ON_SEAT_CHANGE and cached_seats == row_summary:
                    safe_print(f"ℹ️ Seats for session {showtime_id} ({date_str} {time_str}) haven't changed. Skipping Discord alert.")
                else:
                    send_alert(alert_msg)
                    seat_cache[sid_str] = row_summary
                    save_seat_cache(seat_cache)
                return True
            else:
                if sid_str in seat_cache:
                    del seat_cache[sid_str]
                    save_seat_cache(seat_cache)

        else:
            cached_seats = seat_cache.get(sid_str)
            if ONLY_NOTIFY_ON_SEAT_CHANGE and cached_seats == "SHOWTIME_EXISTS":
                safe_print(f"ℹ️ Showtime alert already sent for session {showtime_id}. Skipping duplicate alert.")
            else:
                safe_print(f"Showtime exists for {date_str} at {time_str} ({exp_name})! Session ID: {showtime_id}")
                send_alert(f"🎟️ Showtime Available for {MOVIE_NAME} ({exp_name})!\nDate: {date_str} | Time: {time_str} | Session ID: {showtime_id}")
                seat_cache[sid_str] = "SHOWTIME_EXISTS"
                save_seat_cache(seat_cache)
            return True

    except Exception as e:
        safe_print(f"Error checking seats for session {showtime_id}: {e}")
    return False

def run_tracker():
    seat_cache = load_seat_cache()
    safe_print(f"Starting Ticket Scraper for '{MOVIE_NAME}'...")
    safe_print(f"Checking Location ID {LOCATION_ID}...")
    safe_print(f"Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    safe_print(f"Only Notify On Seat Change: {ONLY_NOTIFY_ON_SEAT_CHANGE}")
    
    if WEEKDAY_START_HOUR is not None and WEEKDAY_END_HOUR is not None:
        start_fmt = f"{WEEKDAY_START_HOUR % 12 or 12}:00 {'PM' if WEEKDAY_START_HOUR >= 12 else 'AM'}"
        end_fmt = f"{WEEKDAY_END_HOUR % 12 or 12}:00 {'PM' if WEEKDAY_END_HOUR >= 12 else 'AM'}"
        safe_print(f"Time Filters: Weekdays between {start_fmt} and {end_fmt} | Weekends all day\n")
    elif WEEKDAY_START_HOUR is not None:
        start_fmt = f"{WEEKDAY_START_HOUR % 12 or 12}:00 {'PM' if WEEKDAY_START_HOUR >= 12 else 'AM'}"
        safe_print(f"Time Filters: Weekdays after {start_fmt} | Weekends all day\n")
    else:
        safe_print("Time Filters: All times enabled\n")

    current_dt = START_DATE
    found_any = False
    headers = get_headers()

    while current_dt <= END_DATE:
        is_weekend = current_dt.weekday() in [5, 6]
        date_api_fmt = f"{current_dt.month}/{current_dt.day}/{current_dt.year}"
        date_display_fmt = current_dt.strftime("%Y-%m-%d")

        api_url = f"https://apis.cineplex.com/prod/cpx/theatrical/api/v1/showtimes?language=en&locationId={LOCATION_ID}&date={date_api_fmt}"

        try:
            r = requests.get(api_url, headers=headers, timeout=10)
            if r.status_code == 200:
                items = r.json()
                for theatre_data in items:
                    for d in theatre_data.get("dates", []):
                        for movie in d.get("movies", []):
                            movie_name = movie.get("name", "")
                            if MOVIE_NAME.lower() in movie_name.lower():
                                for exp in movie.get("experiences", []):
                                    exp_types = [t.lower() for t in exp.get("experienceTypes", [])]
                                    exp_display = ", ".join(exp.get("experienceTypes", []))

                                    matches_formats = True
                                    if REQUIRED_FORMATS:
                                        for req_fmt in REQUIRED_FORMATS:
                                            fmt_lower = req_fmt.lower()
                                            if not (fmt_lower in exp_types or fmt_lower in movie_name.lower() or fmt_lower in exp_display.lower()):
                                                matches_formats = False
                                                break

                                    if not matches_formats:
                                        continue

                                    for session in exp.get("sessions", []):
                                        st_time = session.get("showStartDateTime", "")
                                        sid = session.get("vistaSessionId")

                                        try:
                                            parsed_dt = datetime.strptime(st_time, "%Y-%m-%dT%H:%M:%S")
                                            parsed_time = parsed_dt.strftime("%I:%M %p")
                                            show_hour = parsed_dt.hour
                                        except Exception:
                                            parsed_time = st_time
                                            show_hour = 12

                                        # Apply weekday hour window filtering
                                        if not is_weekend:
                                            if WEEKDAY_START_HOUR is not None and show_hour < WEEKDAY_START_HOUR:
                                                continue
                                            if WEEKDAY_END_HOUR is not None and show_hour > WEEKDAY_END_HOUR:
                                                continue

                                        safe_print(f"Found Showtime! Date: {date_display_fmt} | Time: {parsed_time} | Format: {exp_display} | Session: {sid}")
                                        found_any = True
                                        check_seats_for_session(sid, date_display_fmt, parsed_time, exp_display, seat_cache)

        except Exception as err:
            safe_print(f"Error querying showtimes for {date_display_fmt}: {err}")

        current_dt += timedelta(days=1)

    if not found_any and SEND_NO_SHOWTIMES_ALERT:
        msg = f"ℹ️ Test Webhook: No showtimes for '{MOVIE_NAME}' found matching criteria between {START_DATE.strftime('%Y-%m-%d')} and {END_DATE.strftime('%Y-%m-%d')}."
        safe_print(msg)
        send_alert(msg)

if __name__ == "__main__":
    run_tracker()