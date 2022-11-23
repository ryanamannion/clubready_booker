#!/bin/bash

# set this srcipt to executable
# $ chmod +x cron_job.sh

# add this cron to crontab:
# $ crontab -e
# and enter this to run the script every night at 00:01
# 1 0 * * 1-7 cron_job.sh
python clubready_booker/booker.py
