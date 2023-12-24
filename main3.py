import os
import time
import telebot
from telebot import types
import threading
from threading import Event
import psycopg2

BOT_TOKEN = "6886128129:AAHq98W5sws0LOMcjVcIWnSE7SlrC6kBFgM"
bot = telebot.TeleBot(BOT_TOKEN)
RECORDING_EXPIRY_TIME = 120  # 120 seconds
USER_STATE = {}
number_of_utterances = 10
THREAD_MANAGER = {}


import psycopg2
from psycopg2 import sql

class DB_Manager:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="sdb",
            user="new_username",
            password="new_password",
            host="localhost"
        )
        self.table_queries = {
            "user_states": """
                CREATE TABLE IF NOT EXISTS user_state (
                    user_id BIGINT PRIMARY KEY,
                    last_message_id BIGINT,
                    stage VARCHAR(255),
                    gender VARCHAR(255),
                    education VARCHAR(255),
                    age INT,
                    utterances_recorded INT,
                    prompt_time TIMESTAMP
                );
            """
        }
        self.ensure_table_exists("user_states")

    def ensure_table_exists(self, table_name):
        if not self.check_table(table_name):
            self.create_table(table_name)

    def create_table(self, table_name):
        query = self.table_queries.get(table_name)
        if query:
            with self.conn.cursor() as cursor:
                try:
                    cursor.execute(query)
                    self.conn.commit()
                except psycopg2.DatabaseError as e:
                    print(f"An error occurred: {e}")
                    self.conn.rollback()

    def check_table(self, table_name):
        check_table_query = sql.SQL("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """)
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(check_table_query, (table_name,))
                return cursor.fetchone()[0]
        except psycopg2.DatabaseError as e:
            print(f"An error occurred: {e}")
            self.conn.rollback()
            return False

    def upsert_user_state(self, user_id, user_data):
        with self.conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                INSERT INTO user_state (user_id, last_message_id, stage, gender, education, age, utterances_recorded, prompt_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    last_message_id = EXCLUDED.last_message_id,
                    stage = EXCLUDED.stage,
                    gender = EXCLUDED.gender,
                    education = EXCLUDED.education,
                    age = EXCLUDED.age,
                    utterances_recorded = EXCLUDED.utterances_recorded,
                    prompt_time = EXCLUDED.prompt_time;
            """), (
                user_id,
                user_data.get('last_message_id'),
                user_data.get('stage'),
                user_data.get('gender'),
                user_data.get('education'),
                user_data.get('age'),
                user_data.get('utterances_recorded'),
                user_data.get('prompt_time')
            ))
            self.conn.commit()
    def get_user_state(self, user_id):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM user_state WHERE user_id = %s;
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                columns = ['user_id', 'last_message_id', 'stage', 'gender', 'education', 'age', 'utterances_recorded', 'prompt_time']
                return dict(zip(columns, result))
            return {}   
db_manager = DB_Manager()



UTT_LIST=["این هفته ساعت پنج صبح بیدارم کن",
"مرا جمعه ساعت نه صبح بیدار کن",
"یک زنگ هشدار را برای دو ساعت دیگر تنظیم کن",
"ساکت",
"الی ساکت شو",
"توقف",
"برای ده ثانیه متوقف کن",
"برای ده ثانیه مکث کن",
"صورتی همان چیزی است که نیاز داریم",
"نور اینجا را کمی گرمتر کن",
"لطفا روشنایی را در حالت مناسب برای مطالعه تنظیم کن",
"لطفا لامپ ها را خاموش کن",
"وقت خوابیدن است",
"علی وقت خواب",
"و تاریک شده است",
"لامپ حمام را خاموش کن",
"علی روشنایی هال را کم کن",
"لامپ ها را در هال کم کن",
 "لامپ ها را در اتاق خواب خاموش کن",
 "علی چراغ‌های اتاق خواب را خاموش کن",
 "نور را روی بیست درصد تنظیم کن",
"آلی روشنایی را تا بیست درصد تنظیم کن",
"علی نور آشپزخانه را کم کن",
"نور آشپزخانه را کم کن",
"اتاق را تاریکتر بکن",
"علی همکف را تمییز کن",
 "همکف را تمیز کن",
"اینجا کثیف است سر و صدا کن",
"خانه را جارو کن",
"علی خانه را جاروبرقی بکش",
"تمیز کردن خوب است گردو غبار خیلی بد است اکنون فرش من را تمیز کن",
"راهرو را جارو بکش",
"بررسی کن کی نمایش شروع می‌شود",
 "من میخوام دوباره آهنگ ابی را گوش بدم",
"من میخوام آن موزیک را دوباره پخش کنم",
 "بررسی کن ماشین من آماده است",
 "چک کن ببین لپتاپم سالمه",
"آیا روشنایی اسکرین من دارد کم می شود",
"من نیاز به سرویس های موقعیت دارم می توانی چک کنی",
"وضعیت باتری من رو بررسی کن",
"من وضعیت روشنایی صفحه را می خواهم",
 "وضعیت را در حافظه در دسترس من به من بدهید",
 "الی من خسته نیستم والا شادم",
"چه خبر",
"الی چه خبر",
"در ایران ساعت چند است",
"تهران ساعت چنده",
"پنج ساعت جلوتر از ساعت گرینویچ چند میشه"]


def send_expiry_message(user_id, remaining_utt,stop_thread_flag=Event()):
    user_data = USER_STATE.get(user_id, {})
    if THREAD_MANAGER.get(user_id,None) is not None:
         thread_stop_thread_flag = THREAD_MANAGER[user_id]
         thread_stop_thread_flag.set()  # Signal the thread to stop
         del THREAD_MANAGER[user_id]
    THREAD_MANAGER[user_id]=stop_thread_flag
    time.sleep(RECORDING_EXPIRY_TIME)
    if not THREAD_MANAGER[user_id].is_set():
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
            if remaining==number_of_utterances:
                sent_message = bot.send_message(call.message.chat.id, text="لطفا  جمله "+UTT_LIST[remaining]+"  را ضبط کنید .")
                USER_STATE[user_id]['last_message_id']=sent_message.message_id
            else:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا  جمله "+UTT_LIST[remaining]+"  را ضبط کنید .")
            timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
            timer.start()
    elif call.data == "re_record_voice":
        if "current_voice" in user_data:
            del USER_STATE[user_id]["current_voice"]
        remaining = number_of_utterances - user_data["utterances_recorded"]
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا جمله "+UTT_LIST[remaining]+" را دوباره ضبط کنید.")
        # bot.send_message(call.message.chat.id, "لطفا جمله "+UTT_LIST[remaining]+" را دوباره ضبط کنید.")
        remaining = number_of_utterances - user_data["utterances_recorded"]
        timer = threading.Thread(target=send_expiry_message, args=(call.message.chat.id,remaining))
        timer.start()
    if call.data == "continue_recording":
        USER_STATE[user_id]["prompt_time"] = time.time()
        remaining = number_of_utterances - user_data["utterances_recorded"]
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=USER_STATE[user_id]['last_message_id'], text="لطفا جمله "+UTT_LIST[remaining]+" را دوباره ضبط کنید.")
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
            USER_STATE[user_id]['last_message_id']=sent_message.message_id
        else:
            markup = types.InlineKeyboardMarkup()
            continue_button = types.InlineKeyboardButton("ادامه", callback_data="continue_recording")
            markup.add(continue_button)
            last_message_id = user_data["last_message_id"]
            bot.edit_message_text(chat_id=user_id, message_id=last_message_id, text="زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)

            # bot.send_message(message.chat.id, "زمان ضبط پیام شما به پایان رسیده است. برای ادامه ضبط دکمه ادامه را فشار دهید.", reply_markup=markup)
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id

    if USER_STATE[user_id]["stage"] == "awaiting_age":
        if message.text.isdigit() and len(message.text) == 2:
            USER_STATE[user_id]["age"] = message.text
            USER_STATE[user_id]["utterances_recorded"] = 0
            USER_STATE[user_id]["stage"] = "recording"
            USER_STATE[user_id]["prompt_time"]= time.time()
            sent_message = bot.send_message(message.chat.id, "لطفا جمله "+UTT_LIST[number_of_utterances]+" را ضبط کنید.")
            # sent_message = bot.send_message(message.chat.id, f"لطفا {number_of_utterances} جمله زیر را ضبط کنید.")
            USER_STATE[user_id]['last_message_id']=sent_message.message_id
            timer = threading.Thread(target=send_expiry_message, args=(message.chat.id,number_of_utterances))
            timer.start()
        else:
            bot.reply_to(message, "فرمت سن وارد شده نامعتبر است. لطفا سن خود را به صورت 'سال تولد' وارد کنید.")

bot.infinity_polling()
