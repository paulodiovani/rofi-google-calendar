import os.path
import sys
import webbrowser
from datetime import datetime, time, timedelta
from functools import lru_cache
from re import search

import click
import yaml
from cachetools import cached
from cachetools.keys import hashkey
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pytz import timezone

# constants
CONFIG_PATH = f"{os.environ['HOME']}/.config/rofi-calendar"

CREDENTIALS_FILE = f"{getattr(sys, '_MEIPASS', os.getcwd())}/data/credentials.json"

SETTINGS_FILE = f"{CONFIG_PATH}/settings.yml"
TOKEN_FILE = f"{CONFIG_PATH}/token.json"

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]



@cached(cache={}, key=lambda **_: hashkey(None))
def settings(**overrides):
    """
    Read settings from settings.yml and allow init with overrides.
    Further calls are cached and will ignore the overrides argument.
    """
    with open(SETTINGS_FILE) as file:
        config = yaml.safe_load(file).get("settings", {})

    for k, v in overrides.items():
        if v is not None:
            config[k] = v

    return config


def credentials():
    """
    Get Google Credentials from the credentials.json file
    and stores a token.json for next calls.
    """
    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def fetch_events(service, calendar_id, page_token=None):
    """
    Call Google Calendar API with calendar_id.
    Recursively calls itself if there is paginated results.
    """
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start_date(),
            timeMax=end_date(),
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
        )
        .execute()
    )

    # loop through response pages
    next_page = events_result.get("nextPageToken", None)
    if next_page:
        return events_result.get("items", []) + fetch_events(
            service, calendar_id, next_page
        )

    return events_result.get("items", [])


@lru_cache(maxsize=None)
def start_date():
    """
    Start date to look for events.
    """
    config = settings()

    tz_info = timezone(config["timezone"])
    date = (
        tz_info.localize(datetime.fromisoformat(config["start_date"]))
        if config.get("start_date", None)
        else datetime.now(tz_info)
    )

    return date.isoformat()


@lru_cache(maxsize=None)
def end_date():
    """
    End date to look for events.
    """
    config = settings()

    tz_info = timezone(config["timezone"])
    date = (
        tz_info.localize(datetime.fromisoformat(config["end_date"]))
        if config.get("end_date", None)
        else datetime.now(tz_info)
    )

    return date.isoformat()


def default_start_date():
    return datetime.now().isoformat()


def default_end_date():
    end_date = datetime.now() + timedelta(days=1)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    return end_date.isoformat()


def format_event_line(event):
    config = settings()
    tz_info = timezone(config["timezone"])

    event_start = event["start"]
    event_end = event["end"]

    (event_start, event_end) = (
        # date and time events
        (
            datetime.fromisoformat(event_start["dateTime"]).astimezone(tz_info),
            datetime.fromisoformat(event_end["dateTime"]).astimezone(tz_info),
        )
        if "dateTime" in event_start and "dateTime" in event_end
        # full day events
        else (
            datetime.fromisoformat(event_start["date"]).replace(tzinfo=tz_info),
            datetime.fromisoformat(event_end["date"]).replace(tzinfo=tz_info),
        )
    )

    event_summary = event["summary"]
    # event_description = event['description'].replace("\n", " ")
    event_conference = (
        event["conferenceData"]["conferenceId"] if "conferenceData" in event else ""
    )

    now = datetime.now(tz_info).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )
    difference = now - event_start
    day = (
        "Today"
        if difference.days == 0
        else "Tomorrow"
        if difference.days == -1
        else event_start.strftime("%Y-%m-%d")
    )

    event_time = (
        "All day"
        if event_start.time() == time(0, 0) and event_end.time() == time(0, 0)
        else f"{event_start.strftime('%H:%M')} - {event_end.strftime('%H:%M')}"
    )

    return "{:<12} {:16} {}{:46.46} {:<12}".format(
        day,
        event_time,
        "📹 " if event_conference else "",
        event_summary,
        event_conference,
    )


@click.command()
@click.option(
    "-s",
    "--start",
    "--start-date",
    help="Start date to fetch events from (default to now).",
    default=default_start_date(),
)
@click.option(
    "-e",
    "--end",
    "--end-date",
    help="End date to fetch events until (default to end of tomorrow).",
    default=default_end_date(),
)
@click.argument("selection", required=False)
def main(start: str, end: str, selection: str | None = None):
    """
    Fetch calendar events and print in a format suitable for rofi.
    Used as: rofi -show cal -modes cal:rofi-calendar

    Or accepts a rofi selection to take an action.
    """
    if selection is not None and selection != "":
        matches = search(".*(\\w{3}-\\w{4}-\\w{3})$", selection)
        if matches is not None:
            conference_id = matches.group(1)
            conference_url = f"https://meet.google.com/{conference_id}"
            webbrowser.open(conference_url, new=0, autoraise=True)
        return

    # initialize config with overrides, if any
    config = settings(**{"start_date": start, "end_date": end})
    # initializer calendar service
    service = build("calendar", "v3", credentials=credentials())

    all_events = []

    for calendar_id in config["calendar_id"]:
        events = fetch_events(service, calendar_id)

        if not events:
            # no upcoming events for calendar
            continue

        for event in events:
            all_events.append(event)

    all_events.sort(
        key=lambda ev: ev["start"]["dateTime"]
        if "dateTime" in ev["start"]
        else ev["start"]["date"]
    )

    for ev in all_events:
        print(format_event_line(ev))


if __name__ == "__main__":
    main()
