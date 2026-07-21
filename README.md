# 🎬 Cineplex Ticket Checker

A flexible Python script that monitors [Cineplex](https://www.cineplex.com) theatrical showtimes for available seats (such as **70mm IMAX** for *The Odyssey*) and sends real-time alerts to a Discord channel via Webhook.

---

## 🌟 Features

- **Format Filtering** — Target specific experience types (e.g. `70mm`, `IMAX`) or scan all formats.
- **Custom Weekday Time Windows** — Filter weekday showtimes by a specific start & end hour window (e.g., 4:00 PM – 8:00 PM) while scanning all showtimes on weekends.
- **Row & Seat Targeting** — Configurable target rows (`E` through `M`) and minimum seat count threshold.
- **Accessibility Seat Exclusion** — Automatically filters out wheelchair and companion seats from seating rows.
- **Visual Seat Map** — Displays an interactive emoji seat layout directly in Discord alerts.
- **Discord Alerts** — Real-time notifications sent directly to your Discord webhook.

---

## 🚀 Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/cineplex_ticket_checker.git
   cd cineplex_ticket_checker
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv

   # On Windows
   .\.venv\Scripts\activate

   # On macOS/Linux
   source .venv/bin/activate

   pip install requests
   ```

3. **Set up `config.json`:**
   Rename `config.example.json` to `config.json` (or copy it):
   ```bash
   cp config.example.json config.json
   ```

---

## ⚙️ Configuration (`config.json`)

Here is an example `config.json`:

```json
{
  "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL",
  "location_id": "7408",
  "subscription_key": "dcdac5601d864addbc2675a2e96cb1f8",
  "movie_name": "The Odyssey",
  "required_formats": ["70mm", "IMAX"],
  "start_date": "today",
  "end_date": "2026-08-30",
  "target_rows": ["E", "F", "G", "H", "I", "J", "K", "L", "M"],
  "exclude_accessibility_seats": true,
  "excluded_seat_labels": ["EC1", "EW1", "EW2", "EC4", "EC21", "EW3", "EW4", "EC24"],
  "weekday_start_hour": 16,
  "weekday_end_hour": 20,
  "min_consecutive_seats": 2,
  "show_seat_map": true,
  "send_no_showtimes_alert": true
}
```

### Configuration Options:

| Setting | Description | Default |
|---|---|---|
| `webhook_url` | Your Discord Webhook URL for receiving alerts. | `""` |
| `location_id` | Cineplex theatre location ID. | `"7408"` (Vaughan) |
| `subscription_key` | Cineplex API Subscription Key header. | Public default key |
| `movie_name` | Name or substring of the movie to monitor. | `"The Odyssey"` |
| `required_formats` | Experience formats required (e.g. `["70mm", "IMAX"]`). | `["70mm", "IMAX"]` |
| `start_date` | `"today"` or specific date in `YYYY-MM-DD` format. | `"today"` |
| `end_date` | End date for scanning in `YYYY-MM-DD` format. | `"2026-08-30"` |
| `target_rows` | Array of row letters to monitor for available seats. | `["E".."M"]` |
| `exclude_accessibility_seats` | `true` to skip wheelchair/companion seats. | `true` |
| `excluded_seat_labels` | List of specific seat labels to ignore. | Wheelchair/Companion IDs |
| `weekday_start_hour` | Start hour (24h format) on weekdays (`16` = 4:00 PM). Set `null` to disable. | `16` |
| `weekday_end_hour` | End hour (24h format) on weekdays (`20` = 8:00 PM). Set `null` to disable. | `20` |
| `min_consecutive_seats` | Minimum available seats required in a row to alert. | `2` |
| `show_seat_map` | `true` to include visual emoji seat map in Discord alerts. | `true` |

---

## 🔍 How to Find your Theatre Location ID

To find the `location_id` for any Cineplex theatre:

1. Open your web browser (Chrome, Edge, Firefox) and go to [cineplex.com](https://www.cineplex.com).
2. Search for your preferred theatre (e.g., *Cineplex Cinemas Vaughan* or *Scotiabank Theatre Toronto*).
3. Open **Developer Tools** (`F12` or Right-Click anywhere -> **Inspect**).
4. Click on the **Network** tab in Developer Tools.
5. Search or filter for `showtimes` in the filter box.
6. Click on any request to `apis.cineplex.com/prod/cpx/theatrical/api/v1/showtimes?...`
7. Look at the request URL parameters for `locationId=XXXX` (e.g., `locationId=7408`).
8. Copy that number and paste it into `"location_id"` in your `config.json`.

---

## 💻 Running the Script

```bash
# On Windows
.\.venv\Scripts\python.exe main.py

# On macOS/Linux
python main.py
```

---

## ⏰ Automated Scheduling

### Windows Task Scheduler (Background / Hidden)
To run every 5 minutes silently in the background without opening a command prompt window:

```powershell
schtasks /create /tn "CineplexTicketChecker" /tr "c:\path\to\project\.venv\Scripts\pythonw.exe c:\path\to\project\main.py" /sc minute /mo 5 /f
```
*(Notice `pythonw.exe` runs Python in the background without popups).*

To delete the scheduled task later:
```powershell
schtasks /delete /tn "CineplexTicketChecker" /f
```

---

## 📄 License

MIT License. Free for public use and customization.
