import os
import time
import telebot
from telebot import types
import threading
BOT_TOKEN = "6759949264:AAGZU-NAkP72r8U6VfI8IoMDlrk3I6O8Uo8"

bot = telebot.TeleBot(BOT_TOKEN)

def send_expiry_message(user_id):
    time.sleep(RECORDING_EXPIRY_TIME)  # Wait for 120 seconds
    user_data = USER_STATE.get(user_id, {})
    if user_data.get("stage") == "recording" and (time.time() - user_data.get("prompt_time", 0)) >= RECORDING_EXPIRY_TIME:
        markup = types.InlineKeyboardMarkup()
        continue_button = types.InlineKeyboardButton("Continue", callback_data="continue_recording")
        markup.add(continue_button)
        bot.send_message(user_id, "Time to record has expired. Press continue to try again.", reply_markup=markup)


USER_STATE = {}
number_of_utterances=10
RECORDING_EXPIRY_TIME = 120 

def send_gender_keyboard(chat_id):
    markup = types.InlineKeyboardMarkup()
    male_button = types.InlineKeyboardButton("Male", callback_data="gender_male")
    female_button = types.InlineKeyboardButton("Female", callback_data="gender_female")
    markup.add(male_button, female_button)
    bot.send_message(chat_id, "Please select your gender:", reply_markup=markup)

def send_education_keyboard(chat_id):
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("Diploma and Below", callback_data="education_diploma_below"),
        types.InlineKeyboardButton("Bachelor's Degree", callback_data="education_bachelors"),
        types.InlineKeyboardButton("Master's Degree", callback_data="education_masters"),
        types.InlineKeyboardButton("PhD", callback_data="education_phd")
    ]
    for button in buttons:
        markup.add(button)
    bot.send_message(chat_id, "Please select your education level:", reply_markup=markup)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    welcome_msg = ("سلام! به ربات ضبط گفتار فارسی خوش آمدید. این ربات برای جمع‌آوری و ضبط گفتارهای فارسی در مجموعه داده‌های بزرگ آمازون طراحی شده است. "
                   "اطلاعات جمع‌آوری شده برای تحقیقات درک زبان گفتاری استفاده خواهد شد. لطفا برای شروع و ثبت گفتار خود، بر روی دکمه 'شروع ضبط' کلیک کنید.")

    markup = types.InlineKeyboardMarkup()
    start_button = types.InlineKeyboardButton(text="شروع", callback_data="start_recording")
    markup.add(start_button)

    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id

    if call.data == "start_recording":
        send_gender_keyboard(call.message.chat.id)
        USER_STATE[user_id] = {"stage": "awaiting_gender"}

    elif call.data.startswith("gender_"):
        USER_STATE[user_id]["gender"] = call.data.split("_")[1]
        bot.send_message(call.message.chat.id, "Please enter your age in 'YY' format:")
        USER_STATE[user_id]["stage"] = "awaiting_age"

    elif call.data.startswith("education_"):
        USER_STATE[user_id] = {
            "education": call.data.split("_")[1],
            "utterances_recorded": 0,
            "stage": "recording",
            "prompt_time": time.time()
        }
        bot.send_message(call.message.chat.id, f"Please record and send {number_of_utterances} utterances.")
        timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,))
        timer.start()

    user_data = USER_STATE.get(user_id, {})

    if call.data == "submit_voice" and "current_voice" in user_data:
        # Save the voice message
        file_info = bot.get_file(user_data["current_voice"])
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f"user_{user_id}_utterance_{user_data['utterances_recorded']}.ogg", 'wb') as new_file:
            new_file.write(downloaded_file)

        USER_STATE[user_id]["utterances_recorded"] += 1
        del USER_STATE[user_id]["current_voice"]  # Clear the current voice reference

        # Check if all utterances are recorded
        if user_data["utterances_recorded"] >= number_of_utterances:
            bot.send_message(call.message.chat.id, "Thank you for recording all the utterances.")
            USER_STATE[user_id]["stage"] = "completed"
        else:
            remaining = number_of_utterances - user_data["utterances_recorded"]
            bot.send_message(call.message.chat.id, f"Please record and send {number_of_utterances} utterances.")
            timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,))
            timer.start()

    elif call.data == "re_record_voice":
        # Clear the current voice reference and prompt for re-recording
        if "current_voice" in user_data:
            del USER_STATE[user_id]["current_voice"]
        bot.send_message(call.message.chat.id, "Please re-record your utterance.")
    if call.data == "continue_recording":
        USER_STATE[user_id]["prompt_time"] = time.time()  # Reset the prompt time
        bot.send_message(call.message.chat.id, "Please record your utterance again.")

    # elif call.data.startswith("education_"):
    #     USER_STATE[user_id]["education"] = call.data.split("_")[1]
    #     USER_STATE[user_id]["stage"] = "completed"
    #     bot.send_message(call.message.chat.id, "Thank you for providing your information.")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    user_data = USER_STATE.get(user_id, {})
    if user_data.get("stage") == "recording":
        current_time = time.time()
        prompt_time = user_data.get("prompt_time")

        if prompt_time and (current_time - prompt_time) <= RECORDING_EXPIRY_TIME:
            # Temporarily store the file_id of the voice message
            USER_STATE[user_id]["current_voice"] = message.voice.file_id
    
            # Create markup for submit and re-record buttons
            markup = types.InlineKeyboardMarkup()
            submit_button = types.InlineKeyboardButton("Submit", callback_data="submit_voice")
            re_record_button = types.InlineKeyboardButton("Re-record", callback_data="re_record_voice")
            markup.add(submit_button, re_record_button)
    
            bot.send_message(message.chat.id, "Would you like to submit this recording or re-record it?", reply_markup=markup)
        else:
            # Time expired, prompt to continue
            markup = types.InlineKeyboardMarkup()
            continue_button = types.InlineKeyboardButton("Continue", callback_data="continue_recording")
            markup.add(continue_button)
            bot.send_message(message.chat.id, "This post expired. Press continue to record again.", reply_markup=markup)
            


@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id

    if user_id not in USER_STATE or USER_STATE[user_id].get("stage") is None:
        bot.reply_to(message, "Please use /start to begin the process.")
        return

    if USER_STATE[user_id]["stage"] == "awaiting_age":
        if message.text.isdigit() and len(message.text) == 2:
            USER_STATE[user_id]["age"] = message.text
            send_education_keyboard(message.chat.id)
        else:
            bot.reply_to(message, "Invalid age format. Please enter your age in 'YY' format.")

bot.infinity_polling()


# bot = telebot.TeleBot(BOT_TOKEN)

# USER_STATE = {}

# def send_gender_keyboard(chat_id):
#     markup = types.InlineKeyboardMarkup()
#     male_button = types.InlineKeyboardButton("Male", callback_data="gender_male")
#     female_button = types.InlineKeyboardButton("Female", callback_data="gender_female")
#     markup.add(male_button, female_button)
#     bot.send_message(chat_id, "Please select your gender:", reply_markup=markup)

# def send_education_keyboard(chat_id):
#     markup = types.InlineKeyboardMarkup()
#     buttons = [
#         types.InlineKeyboardButton("Diploma and Below", callback_data="education_diploma_below"),
#         types.InlineKeyboardButton("Bachelor's Degree", callback_data="education_bachelors"),
#         types.InlineKeyboardButton("Master's Degree", callback_data="education_masters"),
#         types.InlineKeyboardButton("PhD", callback_data="education_phd")
#     ]
#     for button in buttons:
#         markup.add(button)
#     bot.send_message(chat_id, "Please select your education level:", reply_markup=markup)

# @bot.message_handler(commands=['start', 'hello'])
# def send_welcome(message):
#     welcome_msg = ("سلام! به ربات ضبط گفتار فارسی خوش آمدید. این ربات برای جمع‌آوری و ضبط گفتارهای فارسی در مجموعه داده‌های بزرگ آمازون طراحی شده است. "
#                    "اطلاعات جمع‌آوری شده برای تحقیقات درک زبان گفتاری استفاده خواهد شد. لطفا برای شروع و ثبت گفتار خود، بر روی دکمه 'شروع ضبط' کلیک کنید.")

#     markup = types.InlineKeyboardMarkup()
#     start_button = types.InlineKeyboardButton(text="شروع", callback_data="start_recording")
#     markup.add(start_button)

#     bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

# @bot.callback_query_handler(func=lambda call: True)
# def handle_query(call):
#     user_id = call.from_user.id

#     if call.data == "start_recording":
#         send_gender_keyboard(call.message.chat.id)
#         USER_STATE[user_id] = {"stage": "awaiting_gender"}

#     elif call.data.startswith("gender_"):
#         USER_STATE[user_id]["gender"] = call.data.split("_")[1]
#         bot.send_message(call.message.chat.id, "Please enter your age in 'YY' format:")
#         USER_STATE[user_id]["stage"] = "awaiting_age"

#     elif call.data.startswith("education_"):
#         USER_STATE[user_id]["education"] = call.data.split("_")[1]
#         USER_STATE[user_id]["stage"] = "completed"
#         bot.send_message(call.message.chat.id, "Thank you for providing your information.")

# @bot.message_handler(func=lambda message: True)
# def handle_messages(message):
#     user_id = message.from_user.id

#     if user_id not in USER_STATE or USER_STATE[user_id].get("stage") is None:
#         bot.reply_to(message, "Please use /start to begin the process.")
#         return

#     if USER_STATE[user_id]["stage"] == "awaiting_age":
#         if message.text.isdigit() and len(message.text) == 2:
#             USER_STATE[user_id]["age"] = message.text
#             send_education_keyboard(message.chat.id)
#         else:
#             bot.reply_to(message, "Invalid age format. Please enter your age in 'YY' format.")

# bot.infinity_polling()


# USER_STATE = {}

# def send_gender_keyboard(chat_id):
#     markup = types.InlineKeyboardMarkup()
#     male_button = types.InlineKeyboardButton("Male", callback_data="gender_male")
#     female_button = types.InlineKeyboardButton("Female", callback_data="gender_female")
#     markup.add(male_button, female_button)
#     bot.send_message(chat_id, "Please select your gender:", reply_markup=markup)

# def send_education_keyboard(chat_id):
#     markup = types.InlineKeyboardMarkup()
#     buttons = [
#         types.InlineKeyboardButton("Diploma and Below", callback_data="education_diploma_below"),
#         types.InlineKeyboardButton("Bachelor's Degree", callback_data="education_bachelors"),
#         types.InlineKeyboardButton("Master's Degree", callback_data="education_masters"),
#         types.InlineKeyboardButton("PhD", callback_data="education_phd")
#     ]
#     for button in buttons:
#         markup.add(button)
#     bot.send_message(chat_id, "Please select your education level:", reply_markup=markup)

# @bot.message_handler(commands=['start', 'hello'])
# def send_welcome(message):
#     welcome_msg = ("سلام! به ربات ضبط گفتار فارسی خوش آمدید...")
#     send_gender_keyboard(message.chat.id)

# @bot.callback_query_handler(func=lambda call: True)
# def handle_query(call):
#     user_id = call.from_user.id

#     if call.data.startswith("gender_"):
#         USER_STATE[user_id] = {"gender": call.data.split("_")[1]}
#         bot.send_message(call.message.chat.id, "Please enter your age in 'YY' format:")
#         USER_STATE[user_id]["stage"] = "awaiting_age"

#     elif call.data.startswith("education_"):
#         USER_STATE[user_id]["education"] = call.data.split("_")[1]
#         bot.send_message(call.message.chat.id, "Thank you for providing your information.")

# @bot.message_handler(func=lambda message: True)
# def handle_messages(message):
#     user_id = message.from_user.id

#     if user_id not in USER_STATE or USER_STATE[user_id].get("stage") is None:
#         bot.reply_to(message, "Please use /start to begin the process.")
#         return

#     if USER_STATE[user_id]["stage"] == "awaiting_age":
#         if message.text.isdigit() and len(message.text) == 2:
#             USER_STATE[user_id]["age"] = message.text
#             send_education_keyboard(message.chat.id)
#         else:
#             bot.reply_to(message, "Invalid age format. Please enter your age in 'YY' format.")

# bot.infinity_polling()


# @bot.message_handler(commands=['start', 'hello'])
# def send_welcome(message):
#     welcome_msg = (
#         "سلام! به ربات ضبط گفتار فارسی خوش آمدید. این ربات برای جمع‌آوری و ضبط گفتارهای فارسی در مجموعه داده‌های بزرگ آمازون طراحی شده است. "
#         "اطلاعات جمع‌آوری شده برای تحقیقات درک زبان گفتاری استفاده خواهد شد. لطفا برای شروع و ثبت گفتار خود، بر روی دکمه 'شروع ضبط' کلیک کنید.")

#     markup = types.InlineKeyboardMarkup()
#     start_button = types.InlineKeyboardButton(text="شروع", callback_data="start_recording")
#     markup.add(start_button)

#     bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

# @bot.callback_query_handler(func=lambda call: True)
# def handle_query(call):
#     if call.data == "start_recording":
#         send_gender_keyboard(call.message.chat.id)
#         USER_STATE[call.from_user.id] = {"stage": "awaiting_gender"}
# def send_gender_keyboard(chat_id):
#     markup = types.InlineKeyboardMarkup()
#     male_button = types.InlineKeyboardButton("Male", callback_data="gender_male")
#     female_button = types.InlineKeyboardButton("Female", callback_data="gender_female")
#     markup.add(male_button, female_button)
#     bot.send_message(chat_id, "Please select your gender:", reply_markup=markup)

# def send_education_keyboard(chat_id):
#     markup = types.InlineKeyboardMarkup()
#     buttons = [
#         types.InlineKeyboardButton("Diploma and Below", callback_data="education_diploma_below"),
#         types.InlineKeyboardButton("Bachelor's Degree", callback_data="education_bachelors"),
#         types.InlineKeyboardButton("Master's Degree", callback_data="education_masters"),
#         types.InlineKeyboardButton("PhD", callback_data="education_phd")
#     ]
#     for button in buttons:
#         markup.add(button)
#     bot.send_message(chat_id, "Please select your education level:", reply_markup=markup)


# @bot.callback_query_handler(func=lambda call: True)
# def handle_query(call):
#     user_id = call.from_user.id

#     if user_id not in USER_STATE:
#         USER_STATE[user_id] = {"stage": None}

#     if call.data.startswith("gender_"):
#         USER_STATE[user_id]["gender"] = call.data.split("_")[1]
#         bot.send_message(call.message.chat.id, "Please enter your age in 'YY' format:")
#         USER_STATE[user_id]["stage"] = "awaiting_age"

#     elif call.data.startswith("education_"):
#         USER_STATE[user_id]["education"] = call.data.split("_")[1]
#         USER_STATE[user_id]["stage"] = "completed"
#         bot.send_message(call.message.chat.id, "Thank you for providing your information.")

# def get_user_profile(message):
#     user_id = message.from_user.id

#     if USER_STATE[user_id]["stage"] == "awaiting_age":
#         if message.text.isdigit() and len(message.text) == 2:
#             USER_STATE[user_id]["age"] = message.text
#             send_education_keyboard(message.chat.id)
#         else:
#             bot.reply_to(message, "Invalid age format. Please enter your age in 'YY' format.")

# bot.infinity_polling()
