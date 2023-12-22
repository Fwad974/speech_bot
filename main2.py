import os
import time
import telebot
from telebot import types
import threading
BOT_TOKEN = "6759949264:AAGZU-NAkP72r8U6VfI8IoMDlrk3I6O8Uo8"
bot = telebot.TeleBot(BOT_TOKEN)
RECORDING_EXPIRY_TIME = 120  # 120 seconds
USER_STATE = {}
number_of_utterances = 10
def send_expiry_message(user_id, remaining_utt):
    time.sleep(RECORDING_EXPIRY_TIME)
    user_data = USER_STATE.get(user_id, {})
    remaining = number_of_utterances - user_data.get("utterances_recorded", 0)
    if remaining_utt == remaining and user_data.get("stage") == "recording" and (time.time() - user_data.get("prompt_time", 0)) >= RECORDING_EXPIRY_TIME:
        markup = types.InlineKeyboardMarkup()
        continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
        markup.add(continue_button)
        if "last_message_id" in user_data:
            last_message_id = user_data["last_message_id"]
            bot.edit_message_text(chat_id=user_id, message_id=last_message_id, text="زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
        else:
            # Fallback in case last_message_id is not available
            sent_message=bot.send_message(user_id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
            USER_STATE[user_id]['last_message_id']=sent_message.message_id

# def send_expiry_message(user_id,conv_id):
#     time.sleep(RECORDING_EXPIRY_TIME)
#     user_data = USER_STATE.get(user_id, {})
#     print(user_data)
#     remaining = number_of_utterances - user_data["utterances_recorded"]
#     if conv_id == remaining and user_data.get("stage") == "recording" and (time.time() - user_data.get("prompt_time", 0)) >= RECORDING_EXPIRY_TIME:
#         markup = types.InlineKeyboardMarkup()
#         continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
#         markup.add(continue_button)
#         # bot.send_message(user_id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
#         bot.edit_message_text(chat_id=conv_id, message_id=user_data["last_message_id"], text="زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
def send_gender_keyboard(chat_id,message_id):
    markup = types.InlineKeyboardMarkup()
    male_button = types.InlineKeyboardButton("مرد", callback_data="gender_male")
    female_button = types.InlineKeyboardButton("زن", callback_data="gender_female")
    markup.add(male_button, female_button)
    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="لطفا جنسیت خود را انتخاب کنید:",reply_markup=markup)
def send_education_keyboard(chat_id, message_id):
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("دیپلم یا کمتر", callback_data="education_diploma_below"),
        types.InlineKeyboardButton("کارشناسی", callback_data="education_bachelors"),
        types.InlineKeyboardButton("کارشناسی ارشد", callback_data="education_masters"),
        types.InlineKeyboardButton("دکترا", callback_data="education_phd")
    ]
    for button in buttons:
        markup.add(button)
    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="لطفا سطح تحصیلات خود را انتخاب کنید:", reply_markup=markup)
    #bot.send_message(chat_id, "لطفا سطح تحصیلات خود را انتخاب کنید:", reply_markup=markup)
@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    welcome_msg = ("سلام! به ربات ضبط گفتار فارسی خوش آمدید. این ربات برای جمع‌آوری و ضبط گفتارهای فارسی در مجموعه داده‌های بزرگ آمازون طراحی شده است. "
                   "اطلاعات جمع‌آوری شده برای تحقیقات درک زبان گفتاری استفاده خواهد شد. لطفا برای شروع و ثبت گفتار خود، بر روی دکمه 'شروع ضبط' کلیک کنید.")
    markup = types.InlineKeyboardMarkup()
    start_button = types.InlineKeyboardButton(text="شروع", callback_data="start_recording")
    markup.add(start_button)
    sent_message = bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)
    user_id = message.from_user.id
    USER_STATE[user_id]={'last_message_id':sent_message.message_id}
    print("##   ",USER_STATE)
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id

    if call.data == "start_recording":
        send_gender_keyboard(call.message.chat.id, USER_STATE[user_id]['last_message_id'])
        USER_STATE[user_id]["stage"] = "awaiting_gender"

    elif call.data.startswith("gender_"):
        USER_STATE[user_id]["gender"] = call.data.split("_")[1]
        send_education_keyboard(call.message.chat.id, USER_STATE[user_id]['last_message_id'])
        USER_STATE[user_id]["stage"] = "awaiting_education"

    elif call.data.startswith("education_"):
        USER_STATE[user_id]["education"] = call.data.split("_")[1]
        USER_STATE[user_id]["stage"] = "awaiting_age"
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا سن خود را به صورت 'سال تولد' وارد کنید:")

    user_data = USER_STATE.get(user_id, {})
    if call.data == "submit_voice" and "current_voice" in user_data:
        file_info = bot.get_file(user_data["current_voice"])
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f"user_{user_id}_utterance_{user_data['utterances_recorded']}.ogg", 'wb') as new_file:
            new_file.write(downloaded_file)
        USER_STATE[user_id]["utterances_recorded"] += 1
        del USER_STATE[user_id]["current_voice"]
        if user_data["utterances_recorded"] >= number_of_utterances:
            bot.send_message(call.message.chat.id, "تشکر از شما برای ضبط تمام جملات.")
            USER_STATE[user_id]["stage"] = "completed"
        else:
            remaining = number_of_utterances - user_data["utterances_recorded"]
            sent_message = bot.send_message(call.message.chat.id, f"لطفا {remaining} جمله دیگر ضبط کنید.")
            USER_STATE[user_id]['last_message_id']=sent_message.message_id
            timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
            timer.start()
    elif call.data == "re_record_voice":
        if "current_voice" in user_data:
            del USER_STATE[user_id]["current_voice"]
        bot.edit_message_text(chat_id=chat_id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا جمله خود را دوباره ضبط کنید.")
        # bot.send_message(call.message.chat.id, "لطفا جمله خود را دوباره ضبط کنید.")
        remaining = number_of_utterances - user_data["utterances_recorded"]
        timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
        timer.start()
    if call.data == "continue_recording":
        USER_STATE[user_id]["prompt_time"] = time.time()
        bot.edit_message_text(chat_id=chat_id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا جمله خود را دوباره ضبط کنید.")
        remaining = number_of_utterances - user_data["utterances_recorded"]
        timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
        timer.start()
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    user_data = USER_STATE.get(user_id, {})
    if user_data.get("stage") == "recording":
        current_time = time.time()
        prompt_time = user_data.get("prompt_time")
        if prompt_time and (current_time - prompt_time) <= RECORDING_EXPIRY_TIME:
            USER_STATE[user_id]["current_voice"] = message.voice.file_id
            markup = types.InlineKeyboardMarkup()
            submit_button = types.InlineKeyboardButton("تایید", callback_data="submit_voice")
            re_record_button = types.InlineKeyboardButton("ضبط مجدد", callback_data="re_record_voice")
            markup.add(submit_button, re_record_button)
            bot.send_message(message.chat.id, "آیا می‌خواهید این ضبط را تایید کنید یا دوباره ضبط کنید؟", reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup()
            continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
            markup.add(continue_button)
            bot.send_message(message.chat.id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id

    if USER_STATE[user_id]["stage"] == "awaiting_age":
        if message.text.isdigit() and len(message.text) == 2:
            USER_STATE[user_id]["age"] = message.text
            USER_STATE[user_id]["utterances_recorded"] = 0
            USER_STATE[user_id]["stage"] = "recording"
            USER_STATE[user_id]["prompt_time"]= time.time()
            sent_message = bot.send_message(message.chat.id, f"لطفا {number_of_utterances} جمله زیر را ضبط کنید.")
            USER_STATE[user_id]['last_message_id']=sent_message.message_id
            timer = threading.Thread(target=send_expiry_message, args=(message.chat.id,number_of_utterances))
            timer.start()
        else:
            bot.reply_to(message, "فرمت سن وارد شده نامعتبر است. لطفا سن خود را به صورت 'سال تولد' وارد کنید.")

bot.infinity_polling()
# import os
# import time
# import telebot
# from telebot import types
# import threading
# BOT_TOKEN = "6759949264:AAGZU-NAkP72r8U6VfI8IoMDlrk3I6O8Uo8"
# bot = telebot.TeleBot(BOT_TOKEN)
# RECORDING_EXPIRY_TIME = 120  # 120 seconds
# USER_STATE = {}
# number_of_utterances = 10
# def send_expiry_message(user_id,conv_id):
#     time.sleep(RECORDING_EXPIRY_TIME)
#     user_data = USER_STATE.get(user_id, {})
#     remaining = number_of_utterances - user_data["utterances_recorded"]
#     if conv_id == remaining and user_data.get("stage") == "recording" and (time.time() - user_data.get("prompt_time", 0)) >= RECORDING_EXPIRY_TIME:
#         markup = types.InlineKeyboardMarkup()
#         continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
#         markup.add(continue_button)
#         sent_message=bot.send_message(user_id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
#         user_id = message.from_user.id
#         USER_STATE[user_id]={'last_message_id':sent_message.message_id}
# def send_gender_keyboard(chat_id,message_id):
#     markup = types.InlineKeyboardMarkup()
#     male_button = types.InlineKeyboardButton("مرد", callback_data="gender_male")
#     female_button = types.InlineKeyboardButton("زن", callback_data="gender_female")
#     markup.add(male_button, female_button)
#     bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="لطفا جنسیت خود را انتخاب کنید:",reply_markup=markup)
# def send_education_keyboard(chat_id, message_id):
#     markup = types.InlineKeyboardMarkup()
#     buttons = [
#         types.InlineKeyboardButton("دیپلم یا کمتر", callback_data="education_diploma_below"),
#         types.InlineKeyboardButton("کارشناسی", callback_data="education_bachelors"),
#         types.InlineKeyboardButton("کارشناسی ارشد", callback_data="education_masters"),
#         types.InlineKeyboardButton("دکترا", callback_data="education_phd")
#     ]
#     for button in buttons:
#         markup.add(button)
#     bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="لطفا سطح تحصیلات خود را انتخاب کنید:", reply_markup=markup)
#     #bot.send_message(chat_id, "لطفا سطح تحصیلات خود را انتخاب کنید:", reply_markup=markup)
# @bot.message_handler(commands=['start', 'hello'])
# def send_welcome(message):
#     welcome_msg = ("سلام! به ربات ضبط گفتار فارسی خوش آمدید. این ربات برای جمع‌آوری و ضبط گفتارهای فارسی در مجموعه داده‌های بزرگ آمازون طراحی شده است. "
#                    "اطلاعات جمع‌آوری شده برای تحقیقات درک زبان گفتاری استفاده خواهد شد. لطفا برای شروع و ثبت گفتار خود، بر روی دکمه 'شروع ضبط' کلیک کنید.")
#     markup = types.InlineKeyboardMarkup()
#     start_button = types.InlineKeyboardButton(text="شروع", callback_data="start_recording")
#     markup.add(start_button)
#     sent_message = bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)
#     user_id = message.from_user.id
#     USER_STATE[user_id]={'last_message_id':sent_message.message_id}
#     print("##   ",USER_STATE)
# @bot.callback_query_handler(func=lambda call: True)
# def handle_query(call):
#     user_id = call.from_user.id

#     if call.data == "start_recording":
#         send_gender_keyboard(call.message.chat.id, USER_STATE[user_id]['last_message_id'])
#         USER_STATE[user_id]["stage"] = "awaiting_gender"

#     elif call.data.startswith("gender_"):
#         USER_STATE[user_id]["gender"] = call.data.split("_")[1]
#         send_education_keyboard(call.message.chat.id, USER_STATE[user_id]['last_message_id'])
#         USER_STATE[user_id]["stage"] = "awaiting_education"

#     elif call.data.startswith("education_"):
#         USER_STATE[user_id]["education"] = call.data.split("_")[1]
#         USER_STATE[user_id]["stage"] = "awaiting_age"
#         bot.edit_message_text(chat_id=call.message.chat.id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا سن خود را به صورت 'سال تولد' وارد کنید:")

#     user_data = USER_STATE.get(user_id, {})
#     if call.data == "submit_voice" and "current_voice" in user_data:
#         file_info = bot.get_file(user_data["current_voice"])
#         downloaded_file = bot.download_file(file_info.file_path)
#         with open(f"user_{user_id}_utterance_{user_data['utterances_recorded']}.ogg", 'wb') as new_file:
#             new_file.write(downloaded_file)
#         USER_STATE[user_id]["utterances_recorded"] += 1
#         del USER_STATE[user_id]["current_voice"]
#         if user_data["utterances_recorded"] >= number_of_utterances:
#             bot.send_message(call.message.chat.id, "تشکر از شما برای ضبط تمام جملات.")
#             USER_STATE[user_id]["stage"] = "completed"
#         else:
#             remaining = number_of_utterances - user_data["utterances_recorded"]
#             bot.edit_message_text(chat_id=call.message.chat.id, message_id=USER_STATE[user_id]['last_message_id'], text=f"لطفا {remaining} جمله دیگر ضبط کنید.")
#             bot.send_message(call.message.chat.id, f"لطفا {remaining} جمله دیگر ضبط کنید.")
#             timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
#             timer.start()
#     elif call.data == "re_record_voice":
#         if "current_voice" in user_data:
#             del USER_STATE[user_id]["current_voice"]
#         bot.edit_message_text(chat_id=call.message.chat.id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا جمله خود را دوباره ضبط کنید.")
#         #bot.send_message(call.message.chat.id, "لطفا جمله خود را دوباره ضبط کنید.")
#         remaining = number_of_utterances - user_data["utterances_recorded"]
#         timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
#         timer.start()
#     if call.data == "continue_recording":
#         USER_STATE[user_id]["prompt_time"] = time.time()
#         bot.send_message(call.message.chat.id, "لطفا جمله خود را دوباره ضبط کنید.")
#         remaining = number_of_utterances - user_data["utterances_recorded"]
#         timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
#         timer.start()
# @bot.message_handler(content_types=['voice'])
# def handle_voice(message):
#     user_id = message.from_user.id
#     user_data = USER_STATE.get(user_id, {})
#     if user_data.get("stage") == "recording":
#         current_time = time.time()
#         prompt_time = user_data.get("prompt_time")
#         if prompt_time and (current_time - prompt_time) <= RECORDING_EXPIRY_TIME:
#             USER_STATE[user_id]["current_voice"] = message.voice.file_id
#             markup = types.InlineKeyboardMarkup()
#             submit_button = types.InlineKeyboardButton("تایید", callback_data="submit_voice")
#             re_record_button = types.InlineKeyboardButton("ضبط مجدد", callback_data="re_record_voice")
#             markup.add(submit_button, re_record_button)
#             bot.send_message(message.chat.id, "آیا می‌خواهید این ضبط را تایید کنید یا دوباره ضبط کنید؟", reply_markup=markup)
#             user_id = message.from_user.id
#             USER_STATE[user_id]={'last_message_id':sent_message.message_id}
#         else:
#             markup = types.InlineKeyboardMarkup()
#             continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
#             markup.add(continue_button)
#             bot.send_message(message.chat.id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
# @bot.message_handler(func=lambda message: True)
# def handle_messages(message):
#     user_id = message.from_user.id

#     if USER_STATE[user_id]["stage"] == "awaiting_age":
#         if message.text.isdigit() and len(message.text) == 2:
#             USER_STATE[user_id]["age"] = message.text
#             USER_STATE[user_id]["utterances_recorded"] = 0
#             USER_STATE[user_id]["stage"] = "recording"
#             USER_STATE[user_id]["prompt_time"]= time.time()
#             sent_message = bot.send_message(message.chat.id, f"لطفا {number_of_utterances} جمله زیر را ضبط کنید.")
#             user_id = message.from_user.id
#             USER_STATE[user_id]={'last_message_id':sent_message.message_id}
#             timer = threading.Thread(target=send_expiry_message, args=(message.chat.id,number_of_utterances))
#             timer.start()
#         else:
#             bot.reply_to(message, "فرمت سن وارد شده نامعتبر است. لطفا سن خود را به صورت 'سال تولد' وارد کنید.")

# bot.infinity_polling()
