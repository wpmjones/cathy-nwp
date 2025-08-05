# creds.py is the file in which you store all of your personal information
# This includes usernames, passwords, keys, and tokens.
# Example:
# bot_token = "my_token"
# Once you import creds, you will access this like this:
# creds.bot_token
import time

import creds

import asyncio
import json
import os
import re
import requests
import string

from datetime import datetime, date, timedelta
from fuzzywuzzy import fuzz, process
from loguru import logger
from pytz import timezone
from slack_bolt.async_app import AsyncApp
from slack_sdk.web import WebClient
from slack_bolt.error import BoltError
from slack_sdk.errors import SlackApiError

# I'm a big fan of loguru and its simplicity. Obviously, any logging tool could be substituted here.
logger.add("app.log", rotation="1 week")

# Create Slack app
app = AsyncApp(token=creds.bot_token,
               signing_secret=creds.signing_secret)
client = WebClient(token=creds.bot_token)

# Constants
CHANNEL_TESTING = "C095MDZUCHJ"

# look for whitespace in string
# I'm not currently using this function. I honestly can't remember what I was using for, but if I
# remove it, I'll immediately remember why and need it again!
def contains_whitespace(s):
    return True in [c in s for c in string.whitespace]


# Helper functions
def get_next_monday():
    today = datetime.today()
    days_ahead = (7 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = today + timedelta(days=days_ahead)
    return next_monday.strftime("%Y-%m-%d")

def get_next_thursday_after(date_str):
    date = datetime.strptime(date_str, "%Y-%m-%d")
    days_ahead = (3 - date.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


# It's poor design to hard code your help command since it won't update itself when you add/change commands,
# but here it is.  I told you I wasn't a pro!  haha
@app.command("/help")
async def cathy_help(ack, say):
    """Responds with help for Cathy commands"""
    await ack()
    await say("`/symptoms` List the symptoms that require a TM to go home\n"
              "`/illness` List the illnesses that require a TM to stay home\n"
              "`/sick` Open a form to report an illness or unexcused absence\n"
              "`/find [first last]` Retrieve information on missed shifts for the specified TM\n"
              "`/tardy [first last]` Records a tardy for the specified TM\n"
              "`/goals` Responds with goals for our waste process\n"
              "`/symbol` Report on the most recent day of sales for our Symbol run\n"
              "`/add` Opens a form to add new hire to Trello"
              "`/help` List these commands")


@app.command("/newuser")
async def handle_newuser_command(ack, body, client):
    await ack()

    available_date = get_next_monday()
    orientation_date = get_next_thursday_after(available_date)

    modal_view = {
        "type": "modal",
        "callback_id": "newuser_modal",
        "title": {"type": "plain_text", "text": "New User Registration"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "first_name",
                "label": {"type": "plain_text", "text": "First Name"},
                "element": {"type": "plain_text_input", "action_id": "input"}
            },
            {
                "type": "input",
                "block_id": "last_name",
                "label": {"type": "plain_text", "text": "Last Name"},
                "element": {"type": "plain_text_input", "action_id": "input"}
            },
            {
                "type": "input",
                "block_id": "email",
                "label": {"type": "plain_text", "text": "Email Address"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "input",
                    "placeholder": {"type": "plain_text", "text": "e.g. name@example.com"}
                }
            },
            {
                "type": "input",
                "block_id": "phone",
                "label": {"type": "plain_text", "text": "Phone Number"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "input",
                    "placeholder": {"type": "plain_text", "text": "10-digit number"}
                }
            },
            {
                "type": "input",
                "block_id": "available_date",
                "label": {"type": "plain_text", "text": "Available Date"},
                "element": {
                    "type": "datepicker",
                    "action_id": "input",
                    "initial_date": available_date
                }
            },
            {
                "type": "input",
                "block_id": "orientation_date",
                "label": {"type": "plain_text", "text": "Orientation Date"},
                "element": {
                    "type": "datepicker",
                    "action_id": "input",
                    "initial_date": orientation_date
                }
            }
        ]
    }
    logger.info(modal_view)

    await client.views_open(trigger_id=body["trigger_id"], view=modal_view)            


@app.command("/loomis")
async def loomis(ack, body, say):
    """Notifies the team that a manual deposit is prepared for Loomis."""
    await ack()
    if body['channel_id'] != creds.all_channel:
        return await say(f"Please use this command in <#{creds.all_channel}> only.")
    await say("There is a manual deposit prepped and ready to go.  If you see Loomis, please make sure they get"
              " the deposit.  Thank you.")


# async def pull_cater(user_first):
#     # Look for and add catering deliveries if they exist
#     spreadsheet = gc.open_by_key(creds.cater_id)
#     cater_sheet = spreadsheet.worksheet("Sheet1")
#     now_str = datetime.today().strftime("%m/%d/%Y")
#     list_of_orders = cater_sheet.findall(now_str, in_column=1)
#     my_orders = []
#     temp_blocks = []
#     if list_of_orders:
#         list_of_rows = [x.row for x in list_of_orders]
#         for row in list_of_rows:
#             row_values = cater_sheet.row_values(row)
#             if row_values[2] == user_first:
#                 my_orders.append(
#                     {
#                         "type": "section",
#                         "text": {
#                             "type": "mrkdwn",
#                             "text": f"{row_values[1]} ⏱️ {row_values[3]} 📞 {row_values[5]}"
#                         }
#                     }
#                 )
#     if my_orders:
#         temp_blocks.append(
#             {
#                 "type": "section",
#                 "text": {
#                     "type": "mrkdwn",
#                     "text": "*Your Catering Orders for today*"
#                 }
#             }
#         )
#         for order in my_orders:
#             temp_blocks.append(order)
#         temp_blocks.append({"type": "divider"})
#     return temp_blocks


# @app.event("url_verification")
# async def verify(event):
#     """Used only to verify new IP address at
#     https://api.slack.com/apps/A01NUGS5YNB/event-subscriptions?"""
#     if "challenge" in event:
#         logger.info("New IP address for event subscription.")
#         return event['challenge']


# @app.event("app_home_opened")
# async def initiate_home_tab(client, event):
#     """Provide user specific content to the Cathy Home tab"""
#     # Establish link to Google Sheets
#     leader_sheet = staff_spreadsheet.worksheet("Leaders")
#     user_cell = leader_sheet.find(event['user'])
#     user_first = leader_sheet.cell(user_cell.row, 1).value
#     user_loc = leader_sheet.cell(user_cell.row, 5).value
#     # build blocks
#     blocks = [
#         {
#             "type": "section",
#             "text": {
#                 "type": "mrkdwn",
#                 "text": (f"Hey there {user_first} 👋 I'm Cathy - you're gateway to a number of cool features inside of "
#                          f"Slack. Use /help to see all the different commands you can use in Slack.")
#             }
#         },
#         {
#             "type": "divider"
#         }
#     ]
#     # Add catering deliveries for this user, if they exist
#     cater_blocks = await pull_cater(user_first)
#     if cater_blocks:
#         blocks = blocks + cater_blocks
#     # Add Shift Notes
#     blocks.append(
#         {
#             "type": "section",
#             "text": {
#                 "type": "mrkdwn",
#                 "text": "✍️ *Weekly Shift Notes*"
#             },
#             "accessory": {
#                 "type": "button",
#                 "text": {
#                     "type": "plain_text",
#                     "emoji": True,
#                     "text": "Swap Notes"
#                 },
#                 "action_id": "swap_notes"
#             }
#         }
#     )
#     notes_blocks = await pull_notes(user_loc)
#     blocks = blocks + notes_blocks
#     # Publish view to home tab
#     await client.views_publish(
#         user_id=event['user'],
#         view={
#             "type": "home",
#             "callback_id": "home_view",
#             "blocks": blocks
#         }
#     )


# @app.block_action("swap_notes")
# async def home_swap_notes(ack, body, client):
#     """"Update the Home tab following a button click by the user"""
#     await ack()
#     blocks = body['view']['blocks']
#     # update blocks
#     user_loc = body['view']['blocks'][-1]['elements'][0]['elements'][0]['text'][:3]
#     logger.info(user_loc)
#     if user_loc == "BOH":
#         # Swap to FOH
#         notes_blocks = await pull_notes("FOH")
#     else:
#         # Swap to BOH
#         notes_blocks = await pull_notes("BOH")
#     blocks = blocks[:-5] + notes_blocks
#     # Publish view to home tab
#     await client.views_publish(
#         user_id=body['user']['id'],
#         view={
#             "type": "home",
#             "callback_id": "home_view",
#             "blocks": blocks
#         }
#     )


# Remove all Slack messages from the channel you are in. I only use this in my test channel.
# This is a dangerous command and the "if body['user_id'] not in" line below limits the use of this
# command to top leadership only.
@app.command("/clear")
async def clear_messages(ack, body, say, client):
    """Clear the specified number of messages in the channel that called the command"""
    await ack()
    if body['user_id'] not in [creds.pj_user_id, creds.tt_user_id, creds.st_user_id]:
        return await say("I'm sorry. Only Terrells can clear messages.")
    result = await client.conversations_history(channel=body['channel_id'], limit=int(body['text']))
    channel_history = result['messages']
    counter = 0
    for message in channel_history:
        # if counter % 20 == 0:
        #     await asyncio.sleep(2)
        try:
            await client.chat_delete(channel=body['channel_id'],
                                     ts=message['ts'],
                                     token=creds.user_token)
        except BoltError as e:
            print(f"Bolt error: {e}")
        except SlackApiError as e:
            print(f"Error deleting message: {e}")
            await asyncio.sleep(2)
        counter += 1


# @app.block_action("order_form")
# async def order_view(ack, body, client):
#     """Open the order form for data entry"""
#     await ack()
#     logger.info("Start order form view process...")
#     logger.info(body)
#     blocks = [
#         {
#             "type": "input",
#             "block_id": "input_food_item",
#             "label": {"type": "plain_text", "text": "What would you like?"},
#             "element": {
#                 "type": "plain_text_input",
#                 "action_id": "food_item",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Example: Egg White Grill + Hashbrowns"
#                 }
#             }
#         },
# 		{
# 			"type": "section",
# 			"text": {
# 				"type": "mrkdwn",
# 				"text": ("If you want multiple items, put them on the same "
#                         "line.\nFor example *Spicy Biscuit + Fruit Cup*.")
# 			}
# 		}
#     ]
#     logger.info("Blocks ready. Open view.")
#     try:
#         await client.views_open(
#             trigger_id=body['trigger_id'],
#             view={
#                 "type": "modal",
#                 "callback_id": "order_view",
#                 "title": {"type": "plain_text", "text": "Order Form"},
#                 "submit": {"type": "plain_text", "text": "Order"},
#                 "blocks": blocks
#             }
#         )


@app.command("/symptoms")
async def symptoms(ack, say):
    """Respond with the symptoms that require a Team Member to go home"""
    await ack()
    await say("*Team Members must be sent home if displaying the following symptoms:*\n"
              "Vomiting\n"
              "Diarrhea\n"
              "Jaundice (yellowing of the skin)\n"
              "Fever\n"
              "Sore throat with fever or lesions containing pus\n"
              "Infected wound or burn that is opening or draining")


@app.command("/illness")
async def illness(ack, say):
    """Respond with the illnesses that require a Team Member to stay home"""
    await ack()
    await say("*Team Members must stay home if they have the following illnesses:*\n"
              "Salmonella Typhi\n"
              "Non-typhoidal Salmonella\n"
              "Shigella spp.\n"
              "Shiga toxin-producing Escherichia coli (E coli)\n"
              "Hepatitis A virus\n"
              "Norovirus (a type of stomach flu)")


# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
    # while True:
    #     asyncio.run(cem_poster())
