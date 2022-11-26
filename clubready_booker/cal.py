"""Functions for Google calendar integration.

Cannot name it calendar.py or ese imports break
"""
import datetime
import logging
from typing import Optional, Set, List
from collections import Counter

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from clubready_booker.util import get_config_location, default_config_vals

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

logger = logging.getLogger(__name__)

CREDENTIALS_FILENAME = "calendar_credentials.json"
TOKEN_FILENAME = "token.json"


def get_service() -> Resource:
    """Get GCal API service"""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    try:
        conf_location = get_config_location()
        token_path = conf_location.joinpath(TOKEN_FILENAME)
        credentials_path = conf_location.joinpath(CREDENTIALS_FILENAME)
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
            "Encountered and error building the Google Calendar service"
        )
        raise exc
    return service


def get_event_start_datetime(event: dict) -> datetime.datetime:
    """Convert GCal event start to datetime.datetime."""
    event_start = event['start']
    return datetime.datetime.fromisoformat(event_start['dateTime'])


def get_next_events(
        service: Resource,
        summary_set: Optional[Set[str]] = None,
        bookable_range: int = default_config_vals['bookable_range'],
        max_results: int = default_config_vals['max_results']
) -> List[dict]:
    """Get events between now and bookable_range, up to `max_results`

    Args:
        service: GCal API Resource
        summary_set: Optional set of summaries to filter on; if provided, only
            events with summaries (i.e. event names) in the summary set will be
            returned. Summaries are lowered to compare
        bookable_range: Max time in days in to fetch events up to; Some
            ClubReady pages configure it so that you can only book classes
            e.g. two days in advance.
        max_results: Maximum number of results to return from calendar API call

    Returns:
        List of dicts, each dict a valid event from the calendar according to
        the specified kwargs.
    """
    logger.info("Getting events from Google Calendar")
    kawrgs = {'bookable_range': bookable_range, 'max_results': max_results}
    logger.debug(f"Using kwargs: {kawrgs}")
    # normalize class names
    if summary_set is not None:
        summary_set = {summary.lower() for summary in summary_set}
        logger.debug(f"Using summary set: {summary_set}")
    else:
        logger.debug(f"No summary set provided, allowing all summaries.")

    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        now_str = now.isoformat()

        events_result = service.events().list(
            calendarId='primary', timeMin=now_str, singleEvents=True,
            maxResults=max_results, orderBy="startTime"
        ).execute()
        events = events_result.get('items', [])

        if not events:
            logger.warning("Did not find any events in default Google Calendar")
            return []

        # Prints the start and name of the next 10 events
        max_start_time = now + datetime.timedelta(days=bookable_range)
        valid_events = []
        invalid_reasons = []
        for event in events:
            status = event.get('status', 'cancelled')
            if status == 'cancelled':
                invalid_reasons.append(status)
                continue
            summary = event.get("summary", "").lower()
            if summary_set and summary not in summary_set:
                invalid_reasons.append('summary not in summary_set')
                continue
            start_time = get_event_start_datetime(event)
            if start_time > max_start_time:
                invalid_reasons.append(f"beyond bookable range")
                continue
            valid_events.append(event)
        if not valid_events:
            logger.debug(
                f"Found {len(events)} events in calendar, but none of them are "
                f"valid"
            )
        logger.info(f"Found {len(valid_events)} valid events in calendar")
        logger.info(f"Filtered {len(invalid_reasons)} events out as invalid")
        logger.debug(f"Invalid reasons: {dict(Counter(invalid_reasons))}")
        return valid_events

    except HttpError as exc:
        logger.exception("Encountered an error during calendar read")
        raise exc


if __name__ == '__main__':
    service = get_service()
    cal_events = get_next_events(service, bookable_range=2)
    for cal_event in cal_events:
        start = cal_event['start'].get('dateTime', cal_event['start'].get('date'))
        print(f"{cal_event['summary']} @ {start}")
