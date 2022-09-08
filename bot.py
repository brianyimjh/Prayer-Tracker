import logging
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import pytz
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheet API Authentication
scopes = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
json_creds = os.getenv("GOOGLE_SHEETS_CREDS_JSON")

creds_dict = json.loads(json_creds)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\\\n", "\n")
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
client = gspread.authorize(creds)

# Connect to Google Sheet
spreadsheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1adQMR__N4UDx-8VRtq7Es2HzEhNViVlelAIYJTqGoms/edit#gid=0')
sheet = spreadsheet.sheet1

data = sheet.get_all_records()
total_mins_cell = sheet.cell(2, 2).value

PORT = int(os.environ.get('PORT', 8443))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = os.getenv('TELE_API_TOKEN')

MINS_IN_AN_HOUR = 60
total_time_in_mins = int(total_mins_cell)
total_hour = str(total_time_in_mins // MINS_IN_AN_HOUR)
total_mins = str(total_time_in_mins % MINS_IN_AN_HOUR)

main_group_chat_id = int(os.getenv("GROUP_CHAT_ID"))
main_group_chat_message_id = 144

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    global total_hour, total_mins, main_group_chat_id, main_group_chat_message_id

    """Send a message when the command /start is issued."""
    if update.message.chat.type != 'group':
        update.message.reply_text("Hello! Welcome to BW13 Prays bot!!\n\nTo log how long you've prayed for, simply enter a number in mins!")
    else:
        update.message.reply_text(f"BW13 Total Prayer Time: {total_hour} hour(s) {total_mins} min(s)", quote=False)

def log_prayer(update, context):
    global total_time_in_mins, total_hour, total_mins, main_group_chat_id, main_group_chat_message_id

    """Prayer log in minutes"""
    user_input = update.message.text

    if (not user_input.isnumeric() and user_input[0] != '-') or (int(user_input) == 0):
        update.message.reply_text("Please enter a number other than 0")
    else:
        if ((total_time_in_mins + int(user_input)) < 0):
            update.message.reply_text("Total prayer time cannot be less than 0")
        else:
            total_time_in_mins += int(user_input)

            # Update Google Sheet
            total_hour = str(total_time_in_mins // MINS_IN_AN_HOUR)
            total_mins = str(total_time_in_mins % MINS_IN_AN_HOUR)

            # Change from UTC to SG Timezone
            local_timezone = pytz.timezone('Singapore')
            local_datetime = update.message.date.replace(tzinfo=pytz.utc)
            local_datetime = local_datetime.astimezone(local_timezone)

            sheet.insert_row([str(local_datetime), total_time_in_mins, total_hour, total_mins], 2)

            context.bot.edit_message_text(chat_id=main_group_chat_id, message_id=main_group_chat_message_id, text=f"BW13 Total Prayer Time: {total_hour} hour(s) {total_mins} min(s)")

            if int(user_input) < 0:
                update.message.reply_text(f"Negative adjustment done!")
            else:
                update.message.reply_text(f"Awesome!! You've prayed for {user_input} mins!", quote=True)

def get_group_details(update, context):
    update.message.reply_text(f"Group message ID - {update.message.message_id-1}")
    update.message.reply_text(f"Group chat ID - {update.message.chat_id}")

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get_group_details", get_group_details))

    dp.add_handler(MessageHandler(Filters.text, log_prayer))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    # updater.start_polling()

    updater.start_webhook(listen="0.0.0.0",
                        port=int(PORT),
                        url_path=TOKEN,
                        webhook_url=f'https://bw13-prayer-bot.herokuapp.com/{TOKEN}')

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()