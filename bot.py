import sqlite3
import os
import time
import threading
import logging
import telebot
from telebot import types

# ------------------------
# Setup logging for debugging
# ------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------
# Database setup
# ------------------------
database_path = "database1.db"

def get_db_connection():
    # Use check_same_thread=False so that each thread can create its own connection.
    return sqlite3.connect(database_path, check_same_thread=False)

def create_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Create or update users table schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL UNIQUE,
            gender TEXT,
            age INTEGER,
            education TEXT,
            total_recorded INTEGER DEFAULT 0,
            stage TEXT,
            current_task_id INTEGER,
            utterances_recorded INTEGER DEFAULT 0,
            last_message_id INTEGER
        );
        """)
        # Ensure last_message_id column exists (for older DBs)
        cursor.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cursor.fetchall()]
        if "last_message_id" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_message_id INTEGER")

        # Tasks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            record_count INTEGER DEFAULT 0,
            last_record TEXT
        );
        """)
        # Recorded table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recorded (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id INTEGER NOT NULL,
            created_at TEXT,
            noise TEXT
        );
        """)
        conn.commit()
        logger.info("Tables created or verified successfully.")

def load_user_states_from_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT telegram_id, gender, age, education, stage,
                   current_task_id, utterances_recorded, last_message_id
            FROM users
        """)
        rows = cursor.fetchall()
        for tg_id, gender, age, edu, stage, task_id, utterances, last_msg in rows:
            # fetch task text if any
            current_task = None
            if task_id:
                cursor.execute("SELECT text FROM tasks WHERE id = ?", (task_id,))
                r = cursor.fetchone()
                if r:
                    current_task = (task_id, r[0])
            USER_STATE[tg_id] = {
                'stage': stage,
                'gender': gender,
                'age': age,
                'education': edu,
                'current_task': current_task,
                'utterances_recorded': utterances or 0,
                'last_message_id': last_msg,
                'prompt_time': None
            }

# In-memory cache of user state
USER_STATE = {}

create_tables()
load_user_states_from_db()

# ------------------------
# Bot setup and constants
# ------------------------
BOT_TOKEN = "6759949264:AAGZU-NAkP72r8U6VfI8IoMDlrk3I6O8Uo8"
bot = telebot.TeleBot(BOT_TOKEN)
RECORDING_EXPIRY_TIME = 120  # seconds
NUMBER_OF_UTTERANCES = 10

# ------------------------
# Helper: safe edit-or-send
# ------------------------
def send_or_edit(user_id, chat_id, text, **bot_kwargs):
    """
    Try to edit the last message for this user; if that fails,
    send a brand-new message and persist its message_id.
    """
    last_id = USER_STATE[user_id].get('last_message_id')
    if last_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=last_id, **bot_kwargs)
            return
        except Exception:
            pass

    sent = bot.send_message(chat_id, text, **bot_kwargs)
    USER_STATE[user_id]['last_message_id'] = sent.message_id
    update_user_state_in_db(user_id, last_message_id=sent.message_id)

# ------------------------
# DB writes
# ------------------------
def insert_or_update_user_data(telegram_id, gender=None, age=None, education=None, total_recorded=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        if cursor.fetchone():
            parts, params = [], []
            if gender    is not None: parts.append("gender = ?");    params.append(gender)
            if age       is not None: parts.append("age = ?");       params.append(age)
            if education is not None: parts.append("education = ?"); params.append(education)
            if total_recorded is not None:
                parts.append("total_recorded = ?"); params.append(total_recorded)
            if parts:
                params.append(telegram_id)
                cursor.execute(f"UPDATE users SET {','.join(parts)} WHERE telegram_id = ?", params)
        else:
            cursor.execute("""
                INSERT INTO users
                   (telegram_id, gender, age, education, total_recorded)
                VALUES (?, ?, ?, ?, ?)
            """, (telegram_id, gender, age, education, total_recorded or 0))
        conn.commit()

def update_user_state_in_db(telegram_id, stage=None, current_task_id=None,
                             utterances_recorded=None, last_message_id=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        parts, params = [], []
        if stage                is not None: parts.append("stage = ?");                params.append(stage)
        if current_task_id      is not None: parts.append("current_task_id = ?");      params.append(current_task_id)
        if utterances_recorded  is not None: parts.append("utterances_recorded = ?");  params.append(utterances_recorded)
        if last_message_id      is not None: parts.append("last_message_id = ?");      params.append(last_message_id)
        if parts:
            params.append(telegram_id)
            cursor.execute(f"UPDATE users SET {','.join(parts)} WHERE telegram_id = ?", params)
            conn.commit()

def get_next_task_for_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, text FROM tasks
             WHERE id NOT IN (
               SELECT task_id FROM recorded WHERE user_id = ?
             )
            ORDER BY record_count ASC, id ASC
            LIMIT 1
        """, (user_id,))
        return cursor.fetchone()

# ------------------------
# Expiry timer
# ------------------------
def start_expiry_timer(user_id):
    threading.Thread(target=send_expiry_message, args=(user_id,), daemon=True).start()

def send_expiry_message(user_id):
    time.sleep(RECORDING_EXPIRY_TIME)
    user = USER_STATE.get(user_id, {})
    if user.get("stage") == "recording":
        elapsed = time.time() - (user.get("prompt_time") or 0)
        if elapsed >= RECORDING_EXPIRY_TIME:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("ادامه", callback_data="continue_recording"))
            send_or_edit(user_id, user_id,
                         "⏳ زمان اختصاص یافته برای ضبط این جمله به پایان رسیده است. برای ادامه فرایند لطفاً دکمه زیر را انتخاب نمایید.",
                         reply_markup=markup)

# ------------------------
# Keyboards
# ------------------------
def send_gender_keyboard(chat_id, user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("مرد", callback_data="gender_male"),
        types.InlineKeyboardButton("زن", callback_data="gender_female")
    )
    send_or_edit(user_id, chat_id, "لطفا جنسیت خود را انتخاب کنید:", reply_markup=markup)
def send_education_keyboard(chat_id, user_id):
    # remove the old inline keyboard if any
    # remove_previous_inline_keyboard(user_id, chat_id)

    # build the new keyboard
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("دیپلم یا کمتر", callback_data="education_diploma_below"),
        types.InlineKeyboardButton("کارشناسی",     callback_data="education_bachelors"),
        types.InlineKeyboardButton("کارشناسی ارشد", callback_data="education_masters"),
        types.InlineKeyboardButton("دکترا",         callback_data="education_phd")
    ]
    for btn in buttons:
        markup.add(btn)

    # send a brand-new message every time
    sent = bot.send_message(chat_id, "لطفا سطح تحصیلات خود را انتخاب کنید:", reply_markup=markup)

    # update in-memory state
    USER_STATE[user_id]['last_message_id'] = sent.message_id

    # persist to DB so it survives restarts
    update_user_state_in_db(user_id, last_message_id=sent.message_id)

# ------------------------
# Bot handlers
# ------------------------
@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    user_id, chat_id = message.from_user.id, message.chat.id
    welcome_msg = (
        "🌺 به سامانه ثبت گفتار هوشمند فارسی خوش آمدید\n\n"
        "این پلتفرم پژوهشی با هدف توسعه فناوری‌های تشخیص گفتار فارسی طراحی شده است.\n"
        "برای مشارکت در این پژوهش، دکمه «شروع» را انتخاب نمایید."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("شروع", callback_data="start_recording"))
    sent = bot.send_message(chat_id, welcome_msg, reply_markup=markup)
    USER_STATE[user_id] = {
        "stage": "awaiting_command",
        "utterances_recorded": 0,
        "last_message_id": sent.message_id
    }
    update_user_state_in_db(user_id, stage="awaiting_command", last_message_id=sent.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id, chat_id = call.from_user.id, call.message.chat.id
    USER_STATE.setdefault(user_id, {
        'stage': None,
        'utterances_recorded': 0,
        'gender': None,
        'education': None,
        'last_message_id': None
    })
    data = call.data

    if data == "start_recording":
        USER_STATE[user_id]['stage'] = "awaiting_gender"
        insert_or_update_user_data(user_id)
        update_user_state_in_db(user_id, stage="awaiting_gender")
        send_gender_keyboard(chat_id, user_id)

    elif data.startswith("gender_"):
         gender = call.data.split("_",1)[1]
         USER_STATE[user_id]["gender"] = gender
         insert_or_update_user_data(user_id, gender=gender)
         USER_STATE[user_id]["stage"] = "awaiting_age"
         update_user_state_in_db(user_id, stage="awaiting_age")
         send_or_edit(
             user_id, chat_id,
             "لطفاً سال تولد خود را به صورت شمسی (مثلاً ۱۳۸۰) وارد نمایید:"
         )

    elif data.startswith("education_"):
        edu = data.split("_",1)[1]
        USER_STATE[user_id].update(stage="recording", education=edu, utterances_recorded=0,
                                   prompt_time=time.time())
        insert_or_update_user_data(user_id, education=edu)
        update_user_state_in_db(user_id, stage="recording", utterances_recorded=0)

        # hand out first task
        task = get_next_task_for_user(user_id)
        if task:
            tid, txt = task
            USER_STATE[user_id]['current_task'] = (tid, txt)
            update_user_state_in_db(user_id, current_task_id=tid)
            send_or_edit(user_id, chat_id,
                         f"لطفاً جمله زیر را با صدای بلند و واضح بخوانید:\n\n{txt}")
            start_expiry_timer(user_id)
        else:
            send_or_edit(user_id, chat_id, "متاسفانه جمله‌ای برای ضبط وجود ندارد.")
            USER_STATE[user_id]['stage'] = "completed"
            update_user_state_in_db(user_id, stage="completed")

    elif data == "submit_voice":
        user = USER_STATE[user_id]
        if "current_voice" not in user:
            return
        vid = user.pop("current_voice")
        task = user.get("current_task")
        if not task:
            bot.answer_callback_query(call.id, "No task assigned!")
            return
        tid, _ = task

        # download & save
        try:
            finfo = bot.get_file(vid)
            blob  = bot.download_file(finfo.file_path)
            udir = os.path.join("recordings", f"user_{user_id}")
            os.makedirs(udir, exist_ok=True)
            fname = os.path.join(udir, f"task_{tid}_{int(time.time())}.ogg")
            with open(fname, 'wb') as f: f.write(blob)

            # update DB
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO recorded (user_id, task_id, created_at) VALUES (?,?,?)",
                            (user_id, tid, now))
                cur.execute("UPDATE tasks SET record_count=record_count+1, last_record=? WHERE id=?",
                            (now, tid))
                cur.execute("UPDATE users SET total_recorded=total_recorded+1 WHERE telegram_id=?",
                            (user_id,))
                conn.commit()

            # update in-memory & DB
            user['utterances_recorded'] += 1
            update_user_state_in_db(user_id, utterances_recorded=user['utterances_recorded'])

            # next or finish
            if user['utterances_recorded'] >= NUMBER_OF_UTTERANCES:
                USER_STATE[user_id]['stage'] = "completed"
                update_user_state_in_db(user_id, stage="completed")
                send_or_edit(user_id, chat_id, "با تشکر از شما برای ضبط تمامی جملات. فرآیند ضبط به پایان رسید.")
            else:
                task = get_next_task_for_user(user_id)
                if task:
                    tid, txt = task
                    USER_STATE[user_id]['current_task'] = (tid, txt)
                    update_user_state_in_db(user_id, current_task_id=tid)
                    user['prompt_time'] = time.time()
                    send_or_edit(user_id, chat_id,
                                 f"لطفاً جمله زیر را با صدای بلند و واضح بخوانید:\n\n{txt}")
                    start_expiry_timer(user_id)
                else:
                    USER_STATE[user_id]['stage'] = "completed"
                    update_user_state_in_db(user_id, stage="completed")
                    send_or_edit(user_id, chat_id, "متاسفانه جمله‌ای برای ضبط وجود ندارد.")

        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            bot.answer_callback_query(call.id, "Error saving recording!")

    elif data == "re_record_voice":
        user = USER_STATE[user_id]
        user.pop("current_voice", None)
        task = user.get("current_task")
        if task:
            _, txt = task
            user['prompt_time'] = time.time()
            send_or_edit(user_id, chat_id,
                         f"لطفاً جمله زیر را دوباره با صدای بلند و واضح بخوانید:\n\n{txt}")
            start_expiry_timer(user_id)

    elif data == "continue_recording":
        user = USER_STATE[user_id]
        user['prompt_time'] = time.time()
        task = user.get("current_task")
        if task:
            _, txt = task
            send_or_edit(user_id, chat_id,
                         f"لطفاً جمله زیر را دوباره با صدای بلند و واضح بخوانید:\n\n{txt}")
            start_expiry_timer(user_id)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id, chat_id = message.from_user.id, message.chat.id
    user = USER_STATE.get(user_id, {})
    # print(user)
    if user.get("stage") == "recording":
        now, prompt = time.time(), user.get("prompt_time",0)
        if prompt is None:
            prompt=0
        if now - prompt <= RECORDING_EXPIRY_TIME:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("تأیید",    callback_data="submit_voice"),
                types.InlineKeyboardButton("ضبط مجدد", callback_data="re_record_voice")
            )
            user["current_voice"] = message.voice.file_id

            
            # send a brand-new message every time
            sent = bot.send_message(chat_id, "آیا می‌خواهید این ضبط را تأیید کنید یا دوباره ضبط کنید؟" ,reply_markup=markup)
        
            # update in-memory state
            USER_STATE[user_id]['last_message_id'] = sent.message_id
        
            # persist to DB so it survives restarts
            update_user_state_in_db(user_id, last_message_id=sent.message_id)

            
           
        else:
            # expired
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("ادامه", callback_data="continue_recording"))
            sent = bot.send_message(chat_id,  "⏳ زمان اختصاص یافته برای ضبط این جمله به پایان رسیده است. برای ادامه فرایند لطفاً دکمه زیر را انتخاب نمایید.",reply_markup=markup)
        
            # update in-memory state
            USER_STATE[user_id]['last_message_id'] = sent.message_id
        
            # persist to DB so it survives restarts
            update_user_state_in_db(user_id, last_message_id=sent.message_id)

            
            # send_or_edit(user_id, chat_id,
            #              "⏳ زمان اختصاص یافته برای ضبط این جمله به پایان رسیده است. برای ادامه فرایند لطفاً دکمه زیر را انتخاب نمایید.",
            #              reply_markup=markup)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    user_id, chat_id = message.from_user.id, message.chat.id
    state = USER_STATE.get(user_id, {})
    if state.get("stage") is None:
        bot.reply_to(message, "لطفاً با استفاده از دستور /start فرآیند را شروع کنید.")
        return

    if state["stage"] == "awaiting_age":
        txt = message.text.strip()
        if txt.isdigit() and len(txt) in (2,4):
            age = int(txt)
            state['age'] = age
            insert_or_update_user_data(user_id, age=age)
            USER_STATE[user_id]['stage'] = "awaiting_education"
            update_user_state_in_db(user_id, stage="awaiting_education")            
            send_education_keyboard(chat_id, user_id)
        else:
            bot.reply_to(message, "قالب سال وارد شده صحیح نیست. لطفاً سال تولد را به صورت چهار رقم (مثال: ۱۳۷۵) وارد نمایید.")

# ------------------------
# Start polling
# ------------------------
if __name__ == "__main__":
    bot.infinity_polling()
