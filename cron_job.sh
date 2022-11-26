#!/bin/bash

# set this srcipt to executable
# $ chmod +x cron_job.sh

# add this cron to crontab:
# $ crontab -e
# and enter this to run the script every night at 00:01
# 1 0 * * 1-7 cron_job.sh

# When you run this script, you will probably want it to run from the top level
# clubready_booker dir, so CD there and make sure the virtual env is set up
# cd path_to/clubready_booker
# source path_to/clubready_booker/venv/bin/activate
python clubready_booker/booker.py
# deactivate