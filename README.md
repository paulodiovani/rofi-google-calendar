# Rofi Google Calendar

A [rofi] script to show events from Google Calendar and open details or events.

![screenshot](media/screenshot.png)

Loosely based on https://www.reddit.com/r/unixporn/comments/oin3qg/oc_timetablecalendar_setup_with_rofi/.

## Preliminary setup

1. Follow Instructions from the [Python quickstart page]
    - Enable the API (select or create a project)
    - Configure the OAuth consent screen
    - Authorize credentials for a desktop application
2. Save the client secret file to `./data/credentials.json`

## Setup and install

To install on your home folder, set `PREFIX` to `"$HOME/.local"`.

```bash
make
make install PREFIX="$HOME/.local"
```

## Configuration

```bash
# Copy and fill settings file
cp settings.yml.sample ~/.config/rofi-calendar/settings.yml
```

## Usage

```bash
rofi -show cal -modes "cal:rofi-calendar"
```

## Development

### Setup and usage

```bash
# Create and activate virtual env
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the script with rofi
rofi -show cal -modes "cal:bin/rofi-calendar"
```

## Features

Existing and planned features.

- [x] Package and Install as a Rofi plugin
- [ ] Show "loading..." while fetching calendars
- [x] Read events from Google Calendar
- [x] Open Meet conferences on default browser
- [ ] Open Zoom conferences on default browser or Zoom app
- [ ] Support multiple Google/Calendar Accounts

[Python quickstart page]: https://developers.google.com/calendar/api/quickstart/python
[rofi]: https://github.com/davatorium/rofi
