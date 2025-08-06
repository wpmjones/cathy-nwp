# creds.py is the file in which you store all of your personal information
# This includes usernames, passwords, keys, and tokens.
# Example:
# bot_token = "my_token"
# Once you import creds, you will access this like this:
# creds.bot_token
import time

import creds

import asyncio, aiohttp
import json
import os
import re
import requests
import string

from datetime import datetime, date, timedelta, timezone
from fuzzywuzzy import fuzz, process
from loguru import logger
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

# Set global variables
orders = {}

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

@app.use
async def log_middleware(req, resp, next):
    logger.info("Middleware triggered")
    logger.info("Request body: %s", req.body)  # cleaner than f-strings in logs
    await next()


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

    await client.views_open(trigger_id=body["trigger_id"], view=modal_view)


@app.view("newuser_modal")
async def handle_modal_submission(ack, body, view):
    state_values = view["state"]["values"]

    # Extract values
    first_name = state_values["first_name"]["input"]["value"]
    last_name = state_values["last_name"]["input"]["value"]
    email = state_values["email"]["input"]["value"]
    phone_raw = state_values["phone"]["input"]["value"]
    available_date = state_values["available_date"]["input"]["selected_date"]
    orientation_date = state_values["orientation_date"]["input"]["selected_date"]

    # Validation
    errors = {}

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors["email"] = "Please enter a valid email address."

    # Strip all non-digit characters
    phone_digits = re.sub(r"\D", "", phone_raw)

    if len(phone_digits) != 10:
        errors["phone"] = "Phone number must have exactly 10 digits."

    if errors:
        await ack(response_action="errors", errors=errors)
        return

    # Format phone number as XXX-XXX-XXXX
    phone_formatted = f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"

    # Acknowledge the modal submission
    await ack()

    # Build payload
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "values": [
            timestamp,
            first_name,
            last_name,
            phone_formatted,
            available_date,
            orientation_date,
            email
        ]
    }

    # Send to GAS
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(creds.gas, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"GAS returned status {resp.status}")
                else:
                    logger.info("Payload sent successfully to GAS")
    except Exception as e:
        logger.exception(f"Error sending to GAS: {e}")


@app.command("/loomis")
async def loomis(ack, body, say):
    """Notifies the team that a manual deposit is prepared for Loomis."""
    await ack()
    if body['channel_id'] != creds.all_channel:
        return await say(f"Please use this command in <#{creds.all_channel}> only.")
    return await say("There is a manual deposit prepped and ready to go.  If you see Loomis, please "
              "make sure they get the deposit.  Thank you.")


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


@app.command("/breakfast")
async def handle_breakfast_command(ack, body, client):
    await ack()

    trigger_id = body["trigger_id"]
    user_id = body["user_id"]

    await client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "breakfast_modal",
            "title": {"type": "plain_text", "text": "Breakfast Order"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "order_block",
                    "label": {"type": "plain_text", "text": "What would you like?"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "order_input"
                    }
                }
            ]
        }
    )

@app.view("breakfast_modal")
async def handle_modal_submission(ack, body, view, client):
    await ack()  # immediate response to Slack

    user_id = body["user"]["id"]
    order_text = view["state"]["values"]["order_block"]["order_input"]["value"]

    orders[user_id] = order_text

    await client.chat_postEphemeral(
        channel=body["view"]["private_metadata"] or user_id,
        user=user_id,
        text=f"✅ Your order has been received: *{order_text}*"
    )

@app.command("/show_orders")
async def show_orders(ack, body, respond):
    await ack()
    if not orders:
        await respond("No orders yet.")
    else:
        summary = "\n".join([f"<@{uid}>: {item}" for uid, item in orders.items()])
        await respond(f"*Current breakfast orders:*\n{summary}")

@app.command("/clear_orders")
async def clear_orders(ack, respond):
    await ack()
    orders.clear()
    await respond("🥞 Orders have been cleared.")


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
