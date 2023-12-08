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
        # Here you can send a message to the user to open a form for gender, age, etc.
        bot.send_message(call.message.chat.id, "لطفا جنسیت، سن و گویش/استان خود را وارد کنید:")
        # You might want to implement a state machine or a way to keep track of user's responses.

USER_STATE = {}

def get_user_profile(message):
    user_id = message.from_user.id
    if user_id not in USER_STATE:
        USER_STATE[user_id] = {"stage": "gender", "data": {}}
    user_data = USER_STATE[user_id]

    if user_data["stage"] == "gender":
        user_data["data"]["gender"] = message.text
        user_data["stage"] = "age"
        bot.reply_to(message, "لطفا سن خود را وارد کنید:")
    elif user_data["stage"] == "age":
        user_data["data"]["age"] = message.text
        user_data["stage"] = "state_dialect"
        bot.reply_to(message, "لطفا گویش/استان خود را وارد کنید:")
    elif user_data["stage"] == "state_dialect":
        user_data["data"]["state_dialect"] = message.text
        user_data["stage"] = "completed"
        bot.reply_to(message, "اطلاعات شما ثبت شد. متشکرم!")
        # Here you can process the collected data or store it

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    if message.text:
        get_user_profile(message)
    else:
        bot.reply_to(message, message.text)


bot.infinity_polling()
