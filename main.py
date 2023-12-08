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


bot.infinity_polling()
