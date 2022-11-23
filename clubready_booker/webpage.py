"""Functions for interfacing with the specific ClubReady website."""
import json
import os
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pytz
import time
import re
from copy import deepcopy
import logging
from operator import sub, attrgetter
from typing import Dict, Any, List
from string import punctuation

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from bs4.element import Tag

from clubready_booker.util import get_config, get_config_location

logger = logging.getLogger(__name__)

APP_BASE_URL = "https://app.clubready.com/clients"
WS = re.compile(r"^\s+$")
DURATION = re.compile(r"(\d+)\s+(hour(s)?|min(s)?)", re.IGNORECASE)
BUTTON_TITLE = 'Book A Place In This Class'
TABLE_CACHE_NAME = "class_table_cache.json"

os.environ['WDM_PROGRESS_BAR'] = "0"


def get_driver(url: str) -> WebDriver:
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        exc_path = ChromeDriverManager().install()
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        service = ChromeService(exc_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
    except Exception as exc:
        logger.exception("Encountered an error trying to get the page")
        raise exc
    return driver


def login(
        driver: WebDriver,
        username: str,
        password: str
) -> None:
    """Log in to ClubReady account"""
    logger.info("Logging in")
    try:
        uid_form = driver.find_element(by=By.ID, value="uid")
        pw_form = driver.find_element(by=By.ID, value="pw")
        submit = driver.find_element(by=By.CLASS_NAME, value="loginbutt")
        uid_form.send_keys(username)
        pw_form.send_keys(password)
        submit.click()
    except Exception as exc:
        logger.exception("Encountered an error while logging in")
        driver.close()
        raise exc


def parse_class_elem(
        class_elem: Tag,
        column_date: date,
        class_idx: int,
        timezone: str
) -> Dict[str, Any]:
    try:
        texts = [
            s.strip() for s in class_elem.strings if WS.match(s) is None
        ]
        class_start = None
        class_end = None
        duration = None
        class_name_strs = []
        registered = None
        class_size = None
        class_name = None
        instructor = None
        booking_id = None
        for text in texts:
            if "AM" in text or "PM" in text:
                if class_start is not None:
                    logger.warning(
                        f"Found more than one time for class with "
                        f"index {class_idx} in column with date "
                        f"{column_date}. Already have: {class_start}, "
                        f"found {text}"
                    )
                    continue
                class_start = time.strptime(text, "%I:%M %p")
                class_start = pytz.timezone(timezone).localize(datetime(
                    *attrgetter('year', 'month', 'day')(column_date),
                    *attrgetter('tm_hour', 'tm_min')(class_start),
                ))
                continue
            if matches := list(DURATION.finditer(text)):
                duration = text
                class_end = deepcopy(class_start)
                for match in matches:
                    try:
                        duration_num = int(match.group(1))
                        if match.group(2).lower().startswith("hour"):
                            incr = relativedelta(hours=duration_num)
                        elif match.group(2).lower().startswith("min"):
                            incr = relativedelta(minutes=duration_num)
                        else:
                            logger.warning(
                                f"Unknown match group 2 for duration "
                                f"text.  Text: {text}; "
                                f"Group 2: {match.group(2)}"
                            )
                            continue
                        class_end = class_end + incr
                    except ValueError:
                        logger.exception(
                            "Error while trying to find class end"
                        )
                continue
            if not duration:
                # class names can be multiple lines
                class_name_strs.append(text)
            elif duration is not None and class_name is None:
                class_name = " ".join(class_name_strs).strip(punctuation)
            if "spaces occupied" in text:
                booked_proportion = re.search(r'(\d+) / (\d+)', text)
                registered = int(booked_proportion.group(1))
                class_size = int(booked_proportion.group(2))
        if class_name_strs and not class_name:
            class_name = " ".join(class_name_strs).strip(punctuation)
        for desc in class_elem.descendants:
            if "showbio" in getattr(desc, "attrs", {}).get('href', ""):
                instructor = desc.text
                break
        if button := class_elem.find(attrs={'title': BUTTON_TITLE}):
            booking_id = button.attrs.get('onclick', None)
        now = pytz.timezone(timezone).localize(datetime.now())
        ended = class_end < now if class_end else True
        started = class_start < now if class_start else True
        if class_size is not None and registered is not None:
            spots_available = (class_size - registered) > 0
        else:
            spots_available = None
        _class = {
            "texts": texts,
            "start_time": class_start,
            "started": started,
            "end_time": class_end,
            "ended": ended,
            "class_name": class_name,
            "duration": duration,
            "instructor": instructor,
            "registered": registered,
            "class_size": class_size,
            "spots_available": spots_available,
            "booking_id": booking_id
        }
        return _class
    except Exception as exc:
        logger.exception("Encountered an error during class parsing")
        raise exc


def wait_for_elem(driver, attr, val, wait_time=15):
    try:
        condition = EC.presence_of_element_located(
            (By.XPATH, f"//*[@{attr}='{val}']")
        )
        WebDriverWait(driver, wait_time).until(condition)
    except TimeoutException as exc:
        msg = f"Browser timed out after {wait_time}s"
        logger.error(msg)
        driver.close()
        raise exc


def get_classes_page(driver: WebDriver):
    classes_url = APP_BASE_URL + "/classes.asp"
    if driver.current_url != classes_url:
        driver.get(classes_url)
        wait_for_elem(driver, 'title', BUTTON_TITLE)


def build_class_table(
        driver: WebDriver,
        timezone: str
) -> List[Dict[str, Any]]:
    """Navigate through the site and build a table of visible classes.

    Do this part with bs4 since it is just scraping html

    Args:
        driver: selenium driver, already logged in
        timezone: timezone for the class times in the class schedule, should be
            in pytz.all_timezones
    Returns:
        List of dicts, each dict being a class, with information about the class
        stored in each key: val pair
    """
    logger.info("Building class table")
    time.sleep(1)       # stuff needs to load
    class_table = []
    get_classes_page(driver)
    src = driver.page_source
    # source will be the classes for this week, along with all informaiton you
    # need to register
    page = BeautifulSoup(src, features="lxml")
    week_range = page.find(attrs={"id": "weekrange"})
    date_span = []
    for date_str in week_range.text.split(" - "):
        month, day, year = map(int, date_str.strip().split("/"))
        date_span.append(date(year, month, day))

    assert date_span[0] < date_span[1], f"Date span invalid: {date_span}"
    all_dates = [date_span[0]]
    prev_date = date_span[0]
    date_span_days_len = (sub(*reversed(date_span))).days
    for _ in range(date_span_days_len):
        new_date = prev_date + relativedelta(days=1)
        all_dates.append(new_date)
        prev_date = new_date

    schedule = page.find(id="scheduleRow")
    col_elems = [child for child in schedule.children if isinstance(child, Tag)]

    assert len(all_dates) == len(col_elems), (
        f"Dates and Cols not the same len: {len(all_dates)} != {len(col_elems)}"
    )
    for column_date, col_elem in zip(all_dates, col_elems):
        class_elems = col_elem.find('td').findChildren("div", recursive=False)
        for class_idx, class_elem in enumerate(class_elems):
            class_table.append(
                parse_class_elem(class_elem, column_date, class_idx, timezone)
            )

    date_span_str = " - ".join((d.isoformat() for d in date_span))
    logger.info(
        f"Found {len(class_table)} classes for date range {date_span_str}"
    )

    return class_table


def book_class(
        driver: WebDriver,
        class_dict: Dict[str, Any],
        dry_run: bool = False
) -> None:
    logger.info(
        f"Attempting to book {class_dict['class_name']} at "
        f"{class_dict['start_time'].isoformat()}"
    )
    try:
        booking_id = class_dict['booking_id']
        get_classes_page(driver)
        class_button = (By.XPATH, f"//*[@onclick='{booking_id}']")
        class_book_button = driver.find_element(*class_button)
        driver.execute_script("arguments[0].scrollIntoView(true);", class_book_button)
        class_book_button.click()

        # The HTML elements for booking a class and adding yourself to the wait
        # list are pretty much exactly the same, they just have different text
        if class_dict['spots_available'] == 0:
            logger.info("No spots available in class, joining the wait list")
        wait_for_elem(driver, 'id', 'bookbutton')
        button = (By.ID, "bookbutton")
        input_tag = (By.TAG_NAME, "input")
        popup_book_button = driver.find_element(*button)
        popup_book_button = popup_book_button.find_element(*input_tag)
        if not dry_run:
            popup_book_button.click()
        else:
            logger.info("Dry Run - would have booked class")

        # close the popup
        close_button = driver.find_element(By.ID, "MB_close")
        close_button.click()
        time.sleep(1.5)

    except Exception as exc:
        logger.exception(
            f"Encountered an Exception while booking {class_dict['class_name']}"
            f" at {class_dict['start_time'].isoformat()}"
        )
        raise exc


def serialize_class_table(class_table: List[dict]) -> str:
    handled = []
    for row in class_table:
        for time_key in ['start_time', 'end_time']:
            date_time: datetime = row[time_key]
            if date_time is not None:
                row[time_key] = date_time.isoformat()
        handled.append(row)
    return json.dumps(handled)


def load_serialized_class_table(class_table: str) -> List[dict]:
    class_table = json.loads(class_table)
    for row in class_table:
        row['start_time'] = datetime.fromisoformat(row['start_time'])
        row['end_time'] = datetime.fromisoformat(row['end_time'])
    return class_table


def main(save_cache=False):
    driver = None
    try:
        config = get_config()
        driver = get_driver(config['url'])
        login(driver, config['username'], config['password'])
        class_table = build_class_table(driver, config['timezone'])
        if save_cache:
            conf_dir = get_config_location()
            with conf_dir.joinpath(TABLE_CACHE_NAME).open("w") as f:
                f.write(serialize_class_table(class_table))
    except Exception:
        logger.exception("Encountered an exception")
    finally:
        if driver is not None:
            driver.close()


if __name__ == "__main__":
    # Run the webpage and save a cache of the class schedule, so you can do some
    # dev work without hitting the page a bunch
    main(save_cache=False)
