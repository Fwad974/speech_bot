import os

import telebot
from telebot import types

BOT_TOKEN = "6759949264:AAGZU-NAkP72r8U6VfI8IoMDlrk3I6O8Uo8"

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    welcome_msg = (
        "سلام! به ربات ضبط گفتار فارسی خوش آمدید. این ربات برای جمع‌آوری و ضبط گفتارهای فارسی در مجموعه داده‌های بزرگ آمازون طراحی شده است. "
        "اطلاعات جمع‌آوری شده برای تحقیقات درک زبان گفتاری استفاده خواهد شد. لطفا برای شروع و ثبت گفتار خود، بر روی دکمه 'شروع ضبط' کلیک کنید.")

    markup = types.InlineKeyboardMarkup()
    start_button = types.InlineKeyboardButton(text="شروع", callback_data="start_recording")
    markup.add(start_button)

    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "start_recording":
        send_gender_keyboard(call.message.chat.id)
        USER_STATE[call.from_user.id] = {"stage": "awaiting_gender"}
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


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id

    if user_id not in USER_STATE:
        USER_STATE[user_id] = {"stage": None}

    if call.data.startswith("gender_"):
        USER_STATE[user_id]["gender"] = call.data.split("_")[1]
        bot.send_message(call.message.chat.id, "Please enter your age in 'YY' format:")
        USER_STATE[user_id]["stage"] = "awaiting_age"

    elif call.data.startswith("education_"):
        USER_STATE[user_id]["education"] = call.data.split("_")[1]
        USER_STATE[user_id]["stage"] = "completed"
        bot.send_message(call.message.chat.id, "Thank you for providing your information.")

def get_user_profile(message):
    user_id = message.from_user.id

    if USER_STATE[user_id]["stage"] == "awaiting_age":
        if message.text.isdigit() and len(message.text) == 2:
            USER_STATE[user_id]["age"] = message.text
            send_education_keyboard(message.chat.id)
        else:
            bot.reply_to(message, "Invalid age format. Please enter your age in 'YY' format.")

bot.infinity_polling()
