import telebot
import json
import os
from flask import Flask
from threading import Thread
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# المكتبة الخاصة بالاتصال بـ PostgreSQL
import psycopg2
from psycopg2.extras import DictCursor

# --- إعداد خادم الويب للعمل مجاناً على Render ---
app = Flask('')

@app.route('/')
def home():
    return "سيرفر اللجنة العلمية الذكي يعمل بنجاح!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()
# ---------------------------------------------

# إعداد البوت والجدولة
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL") # جلب رابط قاعدة البيانات من بيئة التشغيل

bot = telebot.TeleBot(BOT_TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()

OWNER_ID = 1084564343

# متغيرات النظام (تُحفظ في الذاكرة المؤقتة أثناء التشغيل)
MAINTENANCE_MODE = False
USER_STATE = {}

# قوالب هيكلية المواد الثابتة
COURSES_STRUCTURE = {
    "المستوى الأول 📕": {
        "الفصل الدراسي الأول 📘": ["أساسيات برمجة 📘 Programming basics", "تفاضل وتكامل 1 📘 Calculus 1", "الجبر الخطي 📘 Linear algebra", "فيزياء عامة 📘 General Physics", "لغة عربية (1) 📘 Arabic Language (1)", "لغة إنجليزية (1) 📘 English Language (1)", "مهارات حاسوب 📘 Computer skills"],
        "الفصل الدراسي الثاني 📗": ["تفاضل وتكامل 2 📗 Calculus 2", "لغة عربية (2) 📗 Arabic Language (2)", "لغة انجليزية (2) 📗 English Language (2)", "مقدمة في علم البيانات 📗 Intro DS", "برمجة الحاسوب 📗 Computer", "رياضيات متقطعة 📗 Discrete Mathematics", "ثقافة إسلامية 📗 Islamic Culture"]
    },
    "المستوى الثاني 📗": {
        "الفصل الدراسي الأول 📘": ["هياكل بيانات 📘 Data Structures", "تصميم منطقي 📘 Logic Design", "احتمالات وإحصاء 📘 Probability"],
        "الفصل الدراسي الثاني 📗": ["برمجة كائنية 📗 OOP", "قواعد بيانات 📗 Databases"]
    }
}

# دالة مساعدة لإنشاء الاتصال بالقاعدة والتعامل مع الإغلاق التلقائي
def get_db_connection():
    # يتصل برابط PostgreSQL المأخوذ من الـ Environment Variables
    return psycopg2.connect(DATABASE_URL)

# --- إعداد وإنشاء جداول PostgreSQL ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # في PostgreSQL نستخدم SERIAL بدلاً من AUTOINCREMENT
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id BIGINT PRIMARY KEY,
            role TEXT DEFAULT 'admin'
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            level TEXT,
            semester TEXT,
            course TEXT,
            section TEXT,
            file_name TEXT,
            file_id TEXT,
            downloads_count INTEGER DEFAULT 0
        )
    """)
    
    # في PostgreSQL نستخدم ON CONFLICT بدلاً من INSERT OR IGNORE
    cursor.execute("""
        INSERT INTO admins (user_id, role) 
        VALUES (%s, 'super_admin') 
        ON CONFLICT (user_id) DO NOTHING
    """, (OWNER_ID,))
    
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# --- دالات فحص الصلاحيات والبيانات ---
def is_admin(user_id):
    if user_id == OWNER_ID: 
        return True
    conn = get_db_connection()
    cursor = conn.cursor()
    # نستخدم %s كعلامة حجز للمتغيرات في PostgreSQL بدلاً من ?
    cursor.execute("SELECT 1 FROM admins WHERE user_id = %s", (user_id,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return res is not None

def check_status(message):
    user_id = message.from_user.id
    if MAINTENANCE_MODE and not is_admin(user_id):
        bot.reply_to(message, "⚠️ **البوت قيد الصيانة الحالية** لتحديث الكود وتطوير الخدمات.. سوف يعمل فور الانتهاء مباشرة. شكراً لصبركم!")
        return False
    return True

def register_student(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

# --- لوحات المفاتيح ---
def main_menu(user_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("المستوى الأول 📕", "المستوى الثاني 📗")
    
    if is_admin(user_id):
        markup.add("لوحة تحكم الإدارة ⚙️", "التواصل مع المطور 👨‍💻")
    else:
        markup.add("التواصل مع المطور 👨‍💻")
        
    return markup

# --- 1. قسم معالجة طلبات وتصفح الطلاب ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not check_status(message): 
        return
    uid = message.from_user.id
    register_student(uid)
    if uid in USER_STATE:
        USER_STATE[uid] = {}
        
    bot.send_message(message.chat.id, f"أهلاً بك {message.from_user.first_name} 🎉 في بوت اللجنة العلمية لقسم الذكاء الاصطناعي وعلوم البيانات (AIDS)!\nتصفح المواد بسلاسة من الأزرار بالأسفل👇", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text in ["المستوى الأول 📕", "المستوى الثاني 📗", "رجوع للبداية 🏠"])
def handle_levels(message):
    if not check_status(message): 
        return
    uid = message.from_user.id
    if message.text == "رجوع للبداية 🏠":
        bot.send_message(message.chat.id, "تم العودة للقائمة الرئيسية", reply_markup=main_menu(uid))
        return
    
    level = message.text
    USER_STATE[uid] = {"level": level}
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("الفصل الدراسي الأول 📘", "الفصل الدراسي الثاني 📗")
    markup.add("رجوع للبداية 🏠")
    bot.send_message(message.chat.id, f"📂 {level} - اختر الفصل الدراسي:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["الفصل الدراسي الأول 📘", "الفصل الدراسي الثاني 📗"])
def handle_semesters(message):
    if not check_status(message): 
        return
    uid = message.from_user.id
    if uid not in USER_STATE: 
        return
    
    semester = message.text
    USER_STATE[uid]["semester"] = semester
    level = USER_STATE[uid]["level"]
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for course in COURSES_STRUCTURE[level][semester]:
        markup.add(course)
    markup.add("رجوع للبداية 🏠")
    
    bot.send_message(message.chat.id, f"📚 مقررات {semester}:", reply_markup=markup)

@bot.message_handler(func=lambda m: any(m.text in COURSES_STRUCTURE[lvl][sem] for lvl in COURSES_STRUCTURE for sem in COURSES_STRUCTURE[lvl]))
def handle_courses(message):
    if not check_status(message): 
        return
    uid = message.from_user.id
    if uid not in USER_STATE: 
        return
    
    USER_STATE[uid]["course"] = message.text
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("قسم المحاضرات 🟢", "قسم التمارين 🧪")
    markup.add("قسم النماذج 📝", "رجوع للبداية 🏠")
    
    bot.send_message(message.chat.id, f"📖 مقرر: {message.text}\nاختر القسم الدراسي لعرض الملفات:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["قسم المحاضرات 🟢", "قسم التمارين 🧪", "قسم النماذج 📝"])
def handle_sections(message):
    if not check_status(message): 
        return
    uid = message.from_user.id
    if uid not in USER_STATE or "course" not in USER_STATE[uid]: 
        return
    
    section = message.text
    state = USER_STATE[uid]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, file_id, file_name FROM files 
        WHERE level=%s AND semester=%s AND course=%s AND section=%s
    """, (state["level"], state["semester"], state["course"], section))
    files = cursor.fetchall()
    
    if not files:
        cursor.close()
        conn.close()
        bot.send_message(message.chat.id, "📭 هذا القسم فارغ حالياً، لم يتم رفع أي ملفات هنا بعد.")
        return
        
    bot.send_message(message.chat.id, f"📥 جاري إرسال ملفات {section}، يرجى الانتظار...")
    
    for file_db_id, file_id, fname in files:
        try:
            bot.send_document(message.chat.id, file_id, caption=f"📄 {fname}\nاللجنة العلمية - قنوات الكلية")
            cursor.execute("UPDATE files SET downloads_count = downloads_count + 1 WHERE id=%s", (file_db_id,))
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ حدثت مشكلة أثناء إرسال الملف: {fname}")
            
    conn.commit()
    cursor.close()
    conn.close()

# --- 2. لوحة تحكم الإدارة الكاملة المدمجة ---

@bot.message_handler(func=lambda m: m.text in ["لوحة تحكم الإدارة ⚙️", "رجوع للوحة الإدارة 🔙"])
def admin_panel(message):
    uid = message.from_user.id
    if not is_admin(uid): 
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📥 رفع وتحويل الملفات للقسم", "🗑️ الحذف")
    markup.add("إدارة الملفات 📁", "إدارة المشرفين 👥")
    markup.add("الإشعارات 📢", "📊 إحصائيات التحميل")
    markup.add("🔧 تفعيل/إلغاء الصيانة", "رجوع للبداية 🏠")
    
    bot.send_message(message.chat.id, "⚙️ مرحباً بك في غرفة التحكم المتقدمة. اختر الإجراء المطلوب:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🗑️ الحذف" and is_admin(m.from_user.id))
def admin_delete_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("حذف ملف واحد", "حذف قسم بداخل مقرر", "حذف مقرر بالكامل")
    markup.add("رجوع للوحة الإدارة 🔙")
    bot.send_message(message.chat.id, "اختر ما تود حذفه:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "الإشعارات 📢" and is_admin(m.from_user.id))
def admin_notify_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("إرسال إشعار فوري", "جدولة إشعار للطلاب")
    markup.add("رجوع للوحة الإدارة 🔙")
    bot.send_message(message.chat.id, "اختر نوع الإشعار:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "إدارة المشرفين 👥" and is_admin(m.from_user.id))
def admin_supervisors_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("إضافة مشرف", "حذف مشرف")
    markup.add("إضافة صلاحية لمشرف", "سحب صلاحية من مشرف")
    markup.add("رجوع للوحة الإدارة 🔙")
    bot.send_message(message.chat.id, "قسم إدارة فريق اللجنة العلمية:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "إدارة الملفات 📁" and is_admin(m.from_user.id))
def admin_files_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("تعديل اسم ملف/مقرر", "نقل ملف بين المقررات")
    markup.add("رجوع للوحة الإدارة 🔙")
    bot.send_message(message.chat.id, "قسم تعديل وتنظيم الملفات:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔧 تفعيل/إلغاء الصيانة" and is_admin(m.from_user.id))
def toggle_maintenance(message):
    global MAINTENANCE_MODE
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "عذراً، تفعيل وإلغاء وضع الصيانة متاح لمالك البوت الأساسي فقط.")
        return
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    status = "🔴 (مفعّل الآن - البوت مغلق للطلاب)" if MAINTENANCE_MODE else "🟢 (معطل الآن - البوت متاح للجميع)"
    bot.reply_to(message, f"🛠️ وضع الصيانة الحالي للبوت: {status}")

# ========================================================
# --- آلية الرفع المتعدد الجديدة (Bulk Upload) -----------
# ========================================================

@bot.message_handler(func=lambda m: m.text == "📥 رفع وتحويل الملفات للقسم" and is_admin(m.from_user.id))
def start_upload_flow(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("المستوى الأول 📕", "المستوى الثاني 📗", "رجوع للوحة الإدارة 🔙")
    msg = bot.send_message(message.chat.id, "اختر المستوى الذي تود الرفع والتحويل إليه أولاً:", reply_markup=markup)
    bot.register_next_step_handler(msg, upload_step_semester)

def upload_step_semester(message):
    if message.text == "رجوع للوحة الإدارة 🔙": 
        return admin_panel(message)
    level = message.text
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("الفصل الدراسي الأول 📘", "الفصل الدراسي الثاني 📗")
    msg = bot.send_message(message.chat.id, "اختر الفصل الدراسي للرفع:", reply_markup=markup)
    bot.register_next_step_handler(msg, upload_step_course, level)

def upload_step_course(message, level):
    semester = message.text
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for crs in COURSES_STRUCTURE[level][semester]:
        markup.add(crs)
    msg = bot.send_message(message.chat.id, "اختر المقرر الدراسي المستهدف:", reply_markup=markup)
    bot.register_next_step_handler(msg, upload_step_section, level, semester)

def upload_step_section(message, level, semester):
    course = message.text
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("قسم المحاضرات 🟢", "قسم التمارين 🧪", "قسم النماذج 📝")
    msg = bot.send_message(message.chat.id, "اختر القسم الدقيق لحفظ الملفات فيه:", reply_markup=markup)
    bot.register_next_step_handler(msg, upload_step_open_mode, level, semester, course)

def upload_step_open_mode(message, level, semester, course):
    section = message.text
    uid = message.from_user.id
    
    USER_STATE[uid] = {
        "action": "uploading",
        "level": level,
        "semester": semester,
        "course": course,
        "section": section
    }
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("✅ إنهاء الرفع")
    
    text = f"📥 **تم فتح وضع الرفع المتعدد للقسم:**\n({section})\n\n" \
           f"قم الآن بتحديد **كل الملفات** وعمل تحويل (Forward) لها دفعة واحدة إلى هنا.\n\n" \
           f"⚠️ **عندما تنتهي اضغط على زر '✅ إنهاء الرفع' للحفظ والعودة.**"
           
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_bulk_files(message):
    uid = message.from_user.id
    if not is_admin(uid): 
        return
    
    if uid in USER_STATE and USER_STATE[uid].get("action") == "uploading":
        state = USER_STATE[uid]
        
        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or "ملف_بدون_اسم"
        elif message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or f"فيديو_{message.message_id}.mp4"
        else:
            bot.reply_to(message, "⚠️ يرجى رفع ملفات بصيغة (مستندات Documents) أو فيديو.")
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO files (level, semester, course, section, file_name, file_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (state['level'], state['semester'], state['course'], state['section'], file_name, file_id))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"✅ تم الالتقاط والحفظ: {file_name}")

@bot.message_handler(func=lambda m: m.text == "✅ إنهاء الرفع" and is_admin(m.from_user.id))
def finish_bulk_upload(message):
    uid = message.from_user.id
    if uid in USER_STATE and USER_STATE[uid].get("action") == "uploading":
        USER_STATE[uid] = {}
        bot.send_message(message.chat.id, "🎉 ممتاز! تم حفظ جميع الملفات وأُغلق وضع الرفع.", reply_markup=main_menu(uid))

# ========================================================
# دوال الإدارة والتحكم الفرعية 
# ========================================================

# -- 1. دوال المشرفين --
@bot.message_handler(func=lambda m: m.text == "إضافة مشرف" and is_admin(m.from_user.id))
def add_admin_flow(message):
    msg = bot.send_message(message.chat.id, "قم بإرسال الـ ID الرقمي للمشرف الجديد:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    try:
        new_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO admins (user_id, role) VALUES (%s, 'admin') ON CONFLICT (user_id) DO NOTHING", (new_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"✅ تم إضافة المشرف ({new_id}) بنجاح.")
    except Exception as e:
        bot.reply_to(message, "❌ القيمة المدخلة غير صحيحة.")

@bot.message_handler(func=lambda m: m.text == "حذف مشرف" and is_admin(m.from_user.id))
def remove_admin_flow(message):
    msg = bot.send_message(message.chat.id, "قم بإرسال الـ ID الرقمي للمشرف المراد حذفه:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(message):
    try:
        target_id = int(message.text)
        if target_id == OWNER_ID:
            bot.reply_to(message, "❌ لا يمكن حذف المالك الأساسي للبوت.")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = %s", (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"🗑️ تم حذف المشرف بنجاح.")
    except Exception as e:
        bot.reply_to(message, "❌ القيمة المدخلة غير صحيحة.")

@bot.message_handler(func=lambda m: m.text == "إضافة صلاحية لمشرف" and is_admin(m.from_user.id))
def add_privilege_flow(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "عذراً، هذا الإجراء للمالك الأساسي فقط.")
        return
    msg = bot.send_message(message.chat.id, "أرسل الـ ID لترقية المشرف إلى (Super Admin):")
    bot.register_next_step_handler(msg, process_add_privilege)

def process_add_privilege(message):
    try:
        target_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE admins SET role='super_admin' WHERE user_id=%s", (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"⭐ تم ترقية المشرف ({target_id}) إلى مشرف متميز.")
    except Exception as e:
        pass

@bot.message_handler(func=lambda m: m.text == "سحب صلاحية من مشرف" and is_admin(m.from_user.id))
def remove_privilege_flow(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "عذراً، هذا الإجراء للمالك الأساسي فقط.")
        return
    msg = bot.send_message(message.chat.id, "أرسل الـ ID لسحب التميز وإعادته كمشرف عادي:")
    bot.register_next_step_handler(msg, process_remove_privilege)

def process_remove_privilege(message):
    try:
        target_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE admins SET role='admin' WHERE user_id=%s", (target_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, f"📉 تم سحب الصلاحيات الإضافية من ({target_id}).")
    except Exception as e:
        pass

# -- 2. دوال الحذف والملفات --
@bot.message_handler(func=lambda m: m.text == "حذف ملف واحد" and is_admin(m.from_user.id))
def start_delete_file(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب الاسم الدقيق للملف المراد حذفه:")
    bot.register_next_step_handler(msg, process_delete_file)

def process_delete_file(message):
    fname = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE file_name = %s", (fname,))
    conn.commit()
    cursor.close()
    conn.close()
    bot.reply_to(message, f"🗑️ تم حذف أي ملف باسم '{fname}'.")

@bot.message_handler(func=lambda m: m.text == "نقل ملف بين المقررات" and is_admin(m.from_user.id))
def start_move_file(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب الاسم الدقيق للملف المراد نقله:")
    bot.register_next_step_handler(msg, process_move_file_step2)

def process_move_file_step2(message):
    fname = message.text
    msg = bot.send_message(message.chat.id, f"اكتب اسم المقرر الجديد المراد نقل الملف '{fname}' إليه بدقة:")
    bot.register_next_step_handler(msg, process_move_file_final, fname)

def process_move_file_final(message, fname):
    new_course = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET course = %s WHERE file_name = %s", (new_course, fname))
    conn.commit()
    cursor.close()
    conn.close()
    bot.reply_to(message, f"🔀 تم نقل الملف بنجاح إلى '{new_course}'.")

@bot.message_handler(func=lambda m: m.text == "تعديل اسم ملف/مقرر" and is_admin(m.from_user.id))
def start_rename_file(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب الاسم القديم للملف المراد تعديله:")
    bot.register_next_step_handler(msg, process_rename_file_step2)

def process_rename_file_step2(message):
    old_name = message.text
    msg = bot.send_message(message.chat.id, "اكتب الاسم الجديد للملف:")
    bot.register_next_step_handler(msg, process_rename_file_final, old_name)

def process_rename_file_final(message, old_name):
    new_name = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET file_name = %s WHERE file_name = %s", (new_name, old_name))
    conn.commit()
    cursor.close()
    conn.close()
    bot.reply_to(message, f"✅ تم تغيير الاسم بنجاح إلى '{new_name}'.")

# -- 3. دوال الإشعارات والإحصائيات --
def send_broadcast_to_all(text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    uids = cursor.fetchall()
    cursor.close()
    conn.close()
    for u in uids:
        try: 
            bot.send_message(u[0], f"📢 **تنبيه وإشعار من اللجنة العلمية الطلابية:**\n\n{text}", parse_mode="Markdown")
        except Exception as e: 
            pass

@bot.message_handler(func=lambda m: m.text == "إرسال إشعار فوري" and is_admin(m.from_user.id))
def admin_broadcast_now(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب الرسالة ليتم بثها فوراً:")
    bot.register_next_step_handler(msg, lambda m: [send_broadcast_to_all(m.text), bot.reply_to(m, "✅ تم البث.")])

@bot.message_handler(func=lambda m: m.text == "جدولة إشعار للطلاب" and is_admin(m.from_user.id))
def admin_broadcast_schedule(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب رسالة الإشعار:")
    bot.register_next_step_handler(msg, process_broadcast_schedule_time)

def process_broadcast_schedule_time(message):
    text = message.text
    msg = bot.send_message(message.chat.id, "⏰ أرسل وقت النشر بصيغة:\n`YYYY-MM-DD HH:MM:SS`\nمثال: `2026-06-05 15:30:00`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_broadcast_schedule_final, text)

def process_broadcast_schedule_final(message, text):
    try:
        parsed_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M:%S")
        scheduler.add_job(send_broadcast_to_all, 'date', run_date=parsed_time, args=[text])
        bot.reply_to(message, f"⏳ تم جدولة الإشعار بنجاح.")
    except ValueError:
        bot.reply_to(message, "❌ صيغة الوقت خاطئة.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات التحميل" and is_admin(m.from_user.id))
def show_real_stats(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_name, downloads_count FROM files ORDER BY downloads_count DESC LIMIT 5")
    rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_students = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    stats_text = f"📊 **الإحصائيات:**\n👥 المشتركين: {total_students}\n\n🔝 **أكثر 5 ملفات تحميلاً:**\n"
    for idx, (name, count) in enumerate(rows, 1):
        stats_text += f"{idx}. 📄 {name} -> ({count} مرة)\n"
    bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")

# تشغيل وتجهيز المشروع
if __name__ == "__main__":
    keep_alive()
    print("البوت الأكاديمي يعمل الآن بالكود الجديد المتوافق مع PostgreSQL...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
