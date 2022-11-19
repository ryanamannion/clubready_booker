"""Functions for interfacing with the specific ClubReady website."""
from datetime import date, datetime
import time
import re
from copy import deepcopy
import logging

from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from bs4 import BeautifulSoup
from bs4.element import Tag

from clubready_booker.secrets import get_secrets

logger = logging.getLogger(__name__)

APP_BASE_URL = "https://app.clubready.com/clients"
WS = re.compile(r"^\s+$")
DURATION = re.compile(r"(\d+)\s+(hour(s)?|min(s)?)", re.IGNORECASE)


def get_driver(url: str) -> WebDriver:
    exc_path = GeckoDriverManager().install()
    service = FirefoxService(exc_path)
    driver = webdriver.Firefox(service=service)
    try:
        driver.get(url)
    except Exception as exc:
        logger.exception("Encountered an error trying to get page URL")
        raise exc
    return driver


def login(driver: WebDriver, username: str, password: str) -> None:
    """Log in to ClubReady account"""
    logger.info("Logging in")
    uid_form = driver.find_element(by=By.ID, value="uid")
    pw_form = driver.find_element(by=By.ID, value="pw")
    submit = driver.find_element(by=By.CLASS_NAME, value="loginbutt")
    uid_form.send_keys(username)
    pw_form.send_keys(password)
    submit.click()


def build_class_table(driver: WebDriver):
    """Navigate through the site and build a class index"""
    # do this part with bs4 since it is probably faster to just parse it, no
    # interaction just yet
    logger.info("Building class table")
    class_table = []
    driver.get(APP_BASE_URL + "/classes.asp")
    time.sleep(2)       # stuff needs to load
    src = driver.page_source
    # source will be the classes for this week, along with all informaiton you
    # need to register
    page = BeautifulSoup(src, features="lxml")
    week_range = page.find(attrs={"id": "weekrange"})
    date_span = []
    for date_str in week_range.text.split(" - "):
        month, day, year = map(int, date_str.strip().split("/"))
        date_span.append(date(year, month, day))

    all_dates = [date_span[0]]
    last_date = date_span[0]
    assert date_span[0] < date_span[1], f"Date span invalid: {date_span}"
    while True:
        try:
            new_date = date(last_date.year, last_date.month, last_date.day+1)
        except ValueError:
            if last_date.month != 12:
                new_date = date(last_date.year, last_date.month + 1, 1)
            else:
                new_date = date(last_date.year + 1, 1, 1)
        if new_date == date_span[1]:
            break
        all_dates.append(new_date)
        last_date = new_date
    all_dates.append(date_span[1])
    schedule = page.find(id="scheduleRow")
    col_elems = [child for child in schedule.children if isinstance(child, Tag)]
    assert len(all_dates) == len(col_elems), "Dates and Cols not the same len"
    columns = {
        col_date: {'column': col}
        for col_date, col in zip(all_dates, col_elems)
    }
    for column_date, column in columns.items():
        col_elem = column['column']
        class_elems = col_elem.find('td').findChildren("div", recursive=False)
        column['classes'] = classes = []
        for class_idx, class_elem in enumerate(class_elems):
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
                        class_start = datetime(
                            column_date.year, column_date.month, column_date.day,
                            class_start.tm_hour, class_start.tm_min
                        )
                        continue
                    if matches := list(DURATION.finditer(text)):
                        duration = text
                        class_end = deepcopy(class_start)
                        for match in matches:
                            try:
                                duration_num = int(match.group(1))
                                time_args = [
                                    class_end.year, class_end.month,
                                    class_end.day, class_end.hour,
                                    class_end.minute
                                ]
                                if match.group(2).lower().startswith("hour"):
                                    time_args[3] += duration_num    # bump hour
                                    class_end = datetime(*time_args)
                                elif match.group(2).lower().startswith("min"):
                                    total_mins = class_end.minute + duration_num
                                    hour_incr, new_mins = divmod(total_mins, 60)
                                    time_args[3] += hour_incr
                                    time_args[4] = new_mins
                                    class_end = datetime(*time_args)
                                else:
                                    logger.warning(
                                        f"Unknown match group 2 for duration "
                                        f"text.  Text: {text}; "
                                        f"Group 2: {match.group(2)}"
                                    )
                            except ValueError:
                                logger.exception(
                                    "Error while trying to find class end"
                                )
                        continue
                    if not duration:
                        # class names can be multiple lines
                        class_name_strs.append(text)
                    elif duration is not None and class_name is None:
                        class_name = " ".join(class_name_strs)
                    if "spaces occupied" in text:
                        booked_proportion = re.search(r'(\d+) / (\d+)', text)
                        registered = int(booked_proportion.group(1))
                        class_size = int(booked_proportion.group(2))
                if class_name_strs and not class_name:
                    class_name = " ".join(class_name_strs)
                for desc in class_elem.descendants:
                    if "showbio" in getattr(desc, "attrs", {}).get('href', ""):
                        instructor = desc.text
                        break
                button_title = 'Book A Place In This Class'
                if button := class_elem.find(attrs={'title': button_title}):
                    booking_id = button.attrs.get('onclick', None)
                ended = class_end < datetime.now() if class_end else True
                started = class_start < datetime.now() if class_start else True
                _class = {
                    "texts": texts,
                    "class_start": class_start,
                    "started": started,
                    "class_end": class_end,
                    "ended": ended,
                    "class_name": class_name,
                    "duration": duration,
                    "instructor": instructor,
                    "registered": registered,
                    "class_size": class_size,
                    "booking_id": booking_id,
                }
                class_table.append(_class)
            except Exception:
                logger.exception("Encountered an error during class parsing")

    logger.info(
        f"Found {len(class_table)} classes for date range {date_span}"
    )

    return class_table


def main():
    user_secrets = get_secrets("secrets.yaml")
    driver = get_driver(user_secrets['url'])
    login(driver, user_secrets['username'], user_secrets['password'])
    class_table = build_class_table(driver)


if __name__ == "__main__":
    main()
