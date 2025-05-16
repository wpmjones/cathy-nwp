# cathy-nwp
Slack bot for Chick-fil-A

## Overview
This is written in Python and is running on a Virtual Private Server (VPS).  I use GalaxyGate because I do other development work as a hobby.  If you have a spare computer at home (or a Raspberry Pi) you could easily run this without needing to pay for a server.

## Files
**app.py** is the main bot file.  I run this as a server in Linux, but there are many ways to run bot files.  Use the Google and find the fit that is best for you.  This is the file that needs to be running at all times for your bot to work.

**cater_remind.py** is a static python file that uses an Incoming Webhook in Slack.  It connects to a Google Sheet that has a list of upcoming catering and the assigned drivers.  I use crontab (in Linux) to schedule this each morning.

**scraper.py** is a fun one that takes some work, but comes in handy.  Any emails that come into our store email address that deal with outages at the distribution center are forwarded to my gmail account. This script looks at my gmail every night at 2am and reports any outages to Slack.

**waste_remind.py** is the file that many on Facebook asked about.  Like cash_remind.py, it is a stand-alone script that is run multiple times throughout the day to remind the BOH team to record waste.  It includes two buttons.  One brings up a form in Slack to fill out the waste.  The other opens a Google Sheet where all the waste tracking happens.  This is just the reminder.  The form is part of app.py.

## Contact Me
I don't have a lot of spare time, but if you have questions, please email me and I'll help where I can.  I'm wpmjones on gmail.
