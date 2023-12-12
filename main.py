import os
import time
import telebot
from telebot import types
import threading
import mysql.connector


host="localhost"
user="root"
password="password"
database="DB"



mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="DB"
        )



def cursor_instance():
    global mydb 
    try:
        return mydb.cursor()
    except:
        mydb = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        return mydb.cursor()


def insert_or_update_user_data( telegram_id, gender=None, age=None, education=None, total_recorded=0):
    # Check if user already exists in the database
    cursor=cursor_instance()
    cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cursor.fetchone()

    if user:
        # Update existing user
        update_query = "UPDATE users SET "
        update_params = []
        if gender:
            update_query += "gender = %s, "
            update_params.append(gender)
        if age:
            update_query += "age = %s, "
            update_params.append(age)
        if education:
            update_query += "education = %s, "
            update_params.append(education)
        # No need to update total_recorded here, as it's managed elsewhere
        # Remove trailing comma and space
        update_query = update_query.rstrip(', ')
        update_query += " WHERE telegram_id = %s"
        update_params.append(telegram_id)
        cursor.execute(update_query, tuple(update_params))
        mydb.commit()
    else:
        # Insert new user
        insert_query = "INSERT INTO users (telegram_id, gender, age, education, total_recorded) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (telegram_id, gender, age, education, total_recorded))
        mydb.commit()

# SQL Statement to create table
create_table_user_sql = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    gender VARCHAR(10),
    age INT,
    education VARCHAR(50),
    total_recorded INT DEFAULT 0
);
"""
create_tasks_table_sql = """
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    text TEXT,
    record_count INT DEFAULT 0,
    last_record TIMESTAMP NULL DEFAULT NULL
);
"""

create_recorded_table_sql = """
CREATE TABLE IF NOT EXISTS recorded (
    user_email VARCHAR(100) DEFAULT NULL,
    user_phone VARCHAR(100) DEFAULT NULL,
    task_id INT NOT NULL,
    created_at TIMESTAMP NULL DEFAULT NULL,
    id INT NOT NULL AUTO_INCREMENT,
    noise VARCHAR(100) DEFAULT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""

# Create table
def create_table(create_table_sql):
    db_cursor = cursor_instance()
    db_cursor.execute(create_table_sql)
    mydb.commit()

    db_cursor.close()

create_table(create_table_user_sql)
create_table(create_recorded_table_sql)
create_table(create_tasks_table_sql)

BOT_TOKEN = "6759949264:AAGZU-NAkP72r8U6VfI8IoMDlrk3I6O8Uo8"
bot = telebot.TeleBot(BOT_TOKEN)
RECORDING_EXPIRY_TIME = 120  # 120 seconds
USER_STATE = {}
number_of_utterances = 10

def send_expiry_message(user_id,conv_id):
    time.sleep(RECORDING_EXPIRY_TIME)
    user_data = USER_STATE.get(user_id, {})
    remaining = number_of_utterances - user_data["utterances_recorded"]
    if conv_id == remaining and user_data.get("stage") == "recording" and (time.time() - user_data.get("prompt_time", 0)) >= RECORDING_EXPIRY_TIME:
        markup = types.InlineKeyboardMarkup()
        continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
        markup.add(continue_button)
        sent_message =bot.send_message(user_id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
        USER_STATE[user_id][last_message_id] = sent_message.message_id

def send_gender_keyboard(chat_id):
    markup = types.InlineKeyboardMarkup()
    male_button = types.InlineKeyboardButton("مرد", callback_data="gender_male")
    female_button = types.InlineKeyboardButton("زن", callback_data="gender_female")
    markup.add(male_button, female_button)
    sent_message =bot.send_message(chat_id, "لطفا جنسیت خود را انتخاب کنید:", reply_markup=markup)
    USER_STATE[user_id][last_message_id] = sent_message.message_id

def send_education_keyboard(chat_id):
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("دیپلم یا کمتر", callback_data="education_diploma_below"),
        types.InlineKeyboardButton("کارشناسی", callback_data="education_bachelors"),
        types.InlineKeyboardButton("کارشناسی ارشد", callback_data="education_masters"),
        types.InlineKeyboardButton("دکترا", callback_data="education_phd")
    ]
    for button in buttons:
        markup.add(button)
    sent_message = bot.send_message(chat_id, "لطفا سطح تحصیلات خود را انتخاب کنید:", reply_markup=markup)
    USER_STATE[user_id][last_message_id] = sent_message.message_id

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    welcome_msg = ("سلام! به ربات ضبط گفتار فارسی خوش آمدید. این ربات برای جمع‌آوری و ضبط گفتارهای فارسی در مجموعه داده‌های بزرگ آمازون طراحی شده است. "
                   "اطلاعات جمع‌آوری شده برای تحقیقات درک زبان گفتاری استفاده خواهد شد. لطفا برای شروع و ثبت گفتار خود، بر روی دکمه 'شروع ضبط' کلیک کنید.")
    markup = types.InlineKeyboardMarkup()
    start_button = types.InlineKeyboardButton(text="شروع", callback_data="start_recording")
    markup.add(start_button)
    sent_message = bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)
    # print(sent_message.message_id)
    USER_STATE[user_id][last_message_id] = sent_message.message_id

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    user_data = USER_STATE.get(user_id, {})
    # print(call.message.message_id , user_data.get("last_message_id"))
    # if call.message.message_id != user_data.get("last_message_id"):
        # return 

    if call.data == "start_recording":
        send_gender_keyboard(call.message.chat.id)
        insert_or_update_user_data(user_id)
        USER_STATE[user_id] = {"stage": "awaiting_gender"}

    elif call.data.startswith("gender_"):
        USER_STATE[user_id]["gender"] = call.data.split("_")[1]
        insert_or_update_user_data( user_id, gender=USER_STATE[user_id]["gender"])
        sent_message = bot.send_message(call.message.chat.id, "لطفا سن خود را به صورت 'سال تولد' وارد کنید:")
        USER_STATE[user_id][last_message_id] = sent_message.message_id
        USER_STATE[user_id]["stage"] = "awaiting_age"

    elif call.data.startswith("education_"):
        USER_STATE[user_id] = {
            "education": call.data.split("_")[1],
            "utterances_recorded": 0,
            "stage": "recording",
            "prompt_time": time.time()
        }
        insert_or_update_user_data( user_id, education=USER_STATE[user_id]["education"])
        sent_message = bot.send_message(call.message.chat.id, f"لطفا {number_of_utterances} جمله زیر را ضبط کنید.")
        USER_STATE[user_id][last_message_id] = sent_message.message_id
        timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,number_of_utterances))
        timer.start()

    if call.data == "submit_voice" and "current_voice" in user_data:
        file_info = bot.get_file(user_data["current_voice"])
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f"user_{user_id}_utterance_{user_data['utterances_recorded']}.ogg", 'wb') as new_file:
            new_file.write(downloaded_file)

        USER_STATE[user_id]["utterances_recorded"] += 1
        del USER_STATE[user_id]["current_voice"]

        if user_data["utterances_recorded"] >= number_of_utterances:
            sent_message = bot.send_message(call.message.chat.id, "تشکر از شما برای ضبط تمام جملات.")
            USER_STATE[user_id][last_message_id] = sent_message.message_id
            USER_STATE[user_id]["stage"] = "completed"
        else:
            remaining = number_of_utterances - user_data["utterances_recorded"]
            sent_message = bot.send_message(call.message.chat.id, f"لطفا {remaining} جمله دیگر ضبط کنید.")
            USER_STATE[user_id][last_message_id] = sent_message.message_id
            timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
            timer.start()

    elif call.data == "re_record_voice":
        if "current_voice" in user_data:
            del USER_STATE[user_id]["current_voice"]
        sent_message = bot.send_message(call.message.chat.id, "لطفا جمله خود را دوباره ضبط کنید.")
        USER_STATE[user_id][last_message_id] = sent_message.message_id
        remaining = number_of_utterances - user_data["utterances_recorded"]
        timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
        timer.start()

    if call.data == "continue_recording":
        USER_STATE[user_id]["prompt_time"] = time.time()
        sent_message = bot.send_message(call.message.chat.id, "لطفا جمله خود را دوباره ضبط کنید.")
        USER_STATE[user_id][last_message_id] = sent_message.message_id
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
            sent_message = bot.send_message(message.chat.id, "آیا می‌خواهید این ضبط را تایید کنید یا دوباره ضبط کنید؟", reply_markup=markup)
            USER_STATE[user_id][last_message_id] = sent_message.message_id
        else:
            markup = types.InlineKeyboardMarkup()
            continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
            markup.add(continue_button)
            sent_message = bot.send_message(message.chat.id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
            USER_STATE[user_id][last_message_id] = sent_message.message_id

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    if user_id not in USER_STATE or USER_STATE[user_id].get("stage") is None:
        bot.reply_to(message, "لطفا با استفاده از دستور /start فرآیند را شروع کنید.")
        return

    if USER_STATE[user_id]["stage"] == "awaiting_age":
        if message.text.isdigit() and len(message.text) == 2:
            USER_STATE[user_id]["age"] = message.text
            insert_or_update_user_data( user_id, age=USER_STATE[user_id]["age"])
            send_education_keyboard(message.chat.id)
        else:
            bot.reply_to(message, "فرمت سن وارد شده نامعتبر است. لطفا سن خود را به صورت 'سال تولد' وارد کنید.")

bot.infinity_polling()


