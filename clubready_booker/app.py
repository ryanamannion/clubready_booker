"""Bring it all together into a functioning app"""
from clubready_booker import cal, webpage, util
from operator import itemgetter
import logging

import ft

from clubready_booker import util


logger = logging.getLogger(__name__)


def main(dry_run=False):
    tbl_cache = util.get_config_location().joinpath(webpage.TABLE_CACHE_NAME)
    if tbl_cache.exists():
        logger.info(f"Loading class table from cache: {str(tbl_cache)}")
        with tbl_cache.open('r') as f:
            class_table = webpage.load_serialized_class_table(f.read())
    else:
        config = util.get_config()
        driver = webpage.get_driver(config['url'])
        webpage.login(driver, config['username'], config['password'])
        class_table = webpage.build_class_table(driver, config['timezone'])

    class_names = set(map(itemgetter('class_name'), class_table))

    cal_service = cal.get_service()
    upcoming_events = cal.get_next_events(
        cal_service, class_names, BOOKABLE_RANGE
    )

    by_class_name = ft.indexBy("class_name", class_table)

    for event in upcoming_events:
        event_summary = event['summary']
        event_start = cal.get_event_start_datetime(event)
        classes = by_class_name.get(event_summary, [])
        if not classes:
            logger.debug(f'No classes for event "{event_summary}"')
        for matching_class in classes:
            if event_start == matching_class['class_start']:
                logger.info(
                    f"Found matching class for {event_summary} at {event_start.isoformat()}"
                )
                if not dry_run:
                    # Make booking
                    ...
                else:
                    logger.debug(
                        f"Dry Run - would click: {matching_class['booking_id']}"
                    )


if __name__ == "__main__":
    main(dry_run=True)
