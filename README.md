# clubready_booker

## Overview

Book yourself into classes automatically with gyms that use ClubReady to manage
their class schedule.

This is a bit against the spirit of the system, so in order to be as minimal of 
a nuisance as possible, but still get a spot in all the classes you want, there 
is Google Calendar integration. If there is an event on your default Google 
Calendar with the same name and start time as a class, `clubready_booker` will 
book you into that class. 

## Set up

1. git clone repo to your machine

2. Set up virtual env and install requirements
    ```commandline
    $ cd clubready_booker
    $ python -m virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt 
    $ pip install .
    ```

3. Set up config for ClubReady account
    ```commandline
    $ cd ~/.config
    $ mkdir clubready_booker
    $ cd clubready_booker
    $ cp path_to/clubready_booker/config_template.yml ./config.yml
    ```
4. [Config Google Calendar API](https://developers.google.com/calendar/api/quickstart/python), 
    place the OAuth client IDs in the `.config/clubready_booker` dir

5. [Make sure the Google Chrome executable is installed](https://support.google.com/chrome/a/answer/9025903?hl=en&ref_topic=9025817) and in PATH

6. Run the script (make sure venv is activated)
    ```commandline
    $ cd path_to/clubready_booker/clubready_booker
    $ python booker.py
   ```

## Automation

1. With cron job
    
    * Edit `cron_job.sh` to include the full path to `clubready_booker`
    * Copy the Crontab syntax from `cron_job.sh`
    * Edit the crontab with `$ crontab -e` and enter the command as `source full_path_to/clubready_booker/cron_job.sh`

2. Docker
   
    * Coming soon
