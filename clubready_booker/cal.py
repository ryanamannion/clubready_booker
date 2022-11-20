"""Functions for Google calendar integration.

Cannot name it calendar.py or ese imports break
"""
import datetime
import logging
from typing import Optional, Set
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from clubready_booker.secrets import get_config_location

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

logger = logging.getLogger(__name__)


MAX_RESULTS = os.environ.get("CLUBREADYBOOKER_MAXRESULTS", 250)


def get_service() -> Resource:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    try:
        conf_location = get_config_location()
        token_path = conf_location.joinpath("token.json")
        credentials_path = conf_location.joinpath("credentials.json")
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with token_path.open("w") as token:
                token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)
    except Exception as exc:
        logger.exception(
            "Encountered and error building the google calendar service"
        )
        raise exc
    return service


def get_next_events(
        service: Resource,
        class_names: Optional[Set[str]] = None
):
    # normalize class names
    if class_names is not None:
        class_names = {cname.lower() for cname in class_names}

    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        logger.info("Getting the Next")
        events_result = service.events().list(
            calendarId='primary', timeMin=now, singleEvents=True,
            maxResults=MAX_RESULTS, orderBy="startTime"
        ).execute()
        events = events_result.get('items', [])

        if not events:
            logger.warning("Did not find any events in default Google Calendar")
            return

        # Prints the start and name of the next 10 events
        valid_events = []
        for event in events:
            status = event.get('status', 'cancelled')
            if status == 'cancelled':
                continue
            summary = event.get("summary", "").lower()
            if class_names and summary not in class_names:
                continue
            valid_events.append(event)
        if not valid_events:
            logger.warning(
                f"Found {len(events)} events in calendar, but none of them are "
                f"valid"
            )
        return valid_events

    except HttpError as exc:
        logger.exception("Encountered an error during calendar read")
        raise exc


if __name__ == '__main__':
    service = get_service()
    cal_events = get_next_events(service, {"Boxing All Levels"})
    print(f"Found {len(cal_events)} events:")
    for cal_event in cal_events:
        start = cal_event['start'].get('dateTime', cal_event['start'].get('date'))
        print(f"{cal_event['summary']} @ {start}")
