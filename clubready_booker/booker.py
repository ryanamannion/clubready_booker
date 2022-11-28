"""Bring it all together into a functioning app"""
from clubready_booker import cal, webpage
from operator import itemgetter
import logging

import ft

from clubready_booker import util


logger = logging.getLogger(__name__)


def book_classes(dry_run=False) -> None:
    """Book classes by comparing ClubReady schedule and GCal events.

    Args:
        dry_run: Whether to actually book the class; all steps are run except
        the click to book the class.

    Returns:
        None
    """
    config = util.get_config()
    tbl_cache = util.get_config_location().joinpath(webpage.TABLE_CACHE_NAME)
    driver = None
    try:
        if tbl_cache.exists():
            logger.info(f"Loading class table from cache: {str(tbl_cache)}")
            with tbl_cache.open('r') as f:
                class_table = webpage.load_serialized_class_table(f.read())
        else:
            driver = webpage.get_driver(config['url'])
            webpage.login(driver, config['username'], config['password'])
            class_table = webpage.build_class_table(driver, config['timezone'])

        class_names = set(map(itemgetter('class_name'), class_table))

        cal_service = cal.get_service()
        upcoming_events = cal.get_next_events(
            cal_service, class_names, config['bookable_range']
        )

        by_class_name = ft.indexBy("class_name", class_table)

        for event in upcoming_events:
            event_summary = event['summary']
            event_start = cal.get_event_start_datetime(event)
            classes = by_class_name.get(event_summary, [])
            if not classes:
                logger.debug(f'No classes for event "{event_summary}"')
            for matching_class in classes:
                if event_start == matching_class['start_time']:
                    if driver is None:
                        logger.warning(f"No Driver at class booking time")
                    else:
                        webpage.book_class(driver, matching_class, dry_run)
    except Exception as exc:
        logger.exception("Encountered an exception")
        raise exc
    finally:
        if driver is not None:
            driver.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        dry_run = bool(sys.argv[1])
    else:
        dry_run = int(input("Dry run? 1/0 > "))
    book_classes(dry_run=dry_run)
