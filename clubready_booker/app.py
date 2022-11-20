"""Bring it all together into a functioning app"""
from clubready_booker import cal, webpage, secrets


def main():
    user_secrets = secrets.get_secrets("secrets.yaml")
    driver = webpage.get_driver(user_secrets['url'])
    webpage.login(driver, user_secrets['username'], user_secrets['password'])
    class_table = webpage.build_class_table(driver)
    class_names = set()

    cal_service = cal.get_service()
    upcoming_events = cal.get_next_events(cal_service, class_names)


if __name__ == "__main__":
    main()