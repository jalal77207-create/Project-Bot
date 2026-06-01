import telebot
import json
import os
import sqlite3
from flask import Flask
from threading import Thread
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

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
bot = telebot.TeleBot(BOT_TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()

OWNER_ID = 1084564343

# متغيرات النظام (تُحفظ في الذاكرة المؤقتة أثناء التشغيل)
MAINTENANCE_MODE = False
USER_STATE = {}  # لتتبع خطوات المشرفين والطلاب أثناء التنقل والرفع

# قوالب هيكلية المواد الثابتة (بناءً على طلبك وصورك)
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

# --- إعداد وإنشاء قاعدة البيانات المدمجة ---
def init_db():
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    # جدول المشرفين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'admin'
        )
    """)
    # جدول المستخدمين (الطلاب) لإرسال الإشعارات
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    # جدول الملفات (قاعدة بيانات التلجرام)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            semester TEXT,
            course TEXT,
            section TEXT,
            file_name TEXT,
            file_id TEXT,
            downloads_count INTEGER DEFAULT 0
        )
    """)
    # إضافة المالك كأول مشرف بصلاحية super_admin
    cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'super_admin')", (OWNER_ID,))
    conn.commit()
    conn.close()

init_db()

# --- دالات فحص الصلاحيات والبيانات ---
def is_admin(user_id):
    if user_id == OWNER_ID: return True
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def check_status(message):
    user_id = message.from_user.id
    if MAINTENANCE_MODE and user_id != OWNER_ID:
        bot.reply_to(message, "⚠️ **البوت قيد الصيانة الحالية** لتحديث الكود وتطوير الخدمات.. سوف يعمل فور الانتهاء مباشرة. شكراً لصبركم!")
        return False
    return True

def register_student(user_id):
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# --- لوحات المفاتيح والأزرار الشجرية ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("المستوى الأول 📕", "المستوى الثاني 📗")
    markup.add("لوحة تحكم الإدارة ⚙️", "التواصل مع اللجنة 📝")
    return markup

def back_buttons():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("رجوع 🔙", "رجوع للبداية 🏠")
    return markup

# --- 1. قسم معالجة طلبات وتصفح الطلاب ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not check_status(message): return
    register_student(message.from_user.id)
    bot.send_message(message.chat.id, f"أهلاً بك {message.from_user.first_name} 🎉 في بوت اللجنة العلمية لقسم الذكاء الاصطناعي وعلوم البيانات (AIDS)!\nتصفح المواد بسلاسة من الأزرار بالأسفل👇", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text in ["المستوى الأول 📕", "المستوى الثاني 📗", "رجوع للبداية 🏠"])
def handle_levels(message):
    if not check_status(message): return
    if message.text == "رجوع للبداية 🏠":
        bot.send_message(message.chat.id, "تم العودة للقائمة الرئيسية", reply_markup=main_menu())
        return
    
    level = message.text
    USER_STATE[message.from_user.id] = {"level": level}
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("الفصل الدراسي الأول 📘", "الفصل الدراسي الثاني 📗")
    markup.add("رجوع للبداية 🏠")
    bot.send_message(message.chat.id, f"📂 {level} - اختر الفصل الدراسي:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["الفصل الدراسي الأول 📘", "الفصل الدراسي الثاني 📗"])
def handle_semesters(message):
    if not check_status(message): return
    uid = message.from_user.id
    if uid not in USER_STATE: return
    
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
    if not check_status(message): return
    uid = message.from_user.id
    if uid not in USER_STATE: return
    
    USER_STATE[uid]["course"] = message.text
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("قسم المحاضرات 🟢", "قسم التمارين 🧪")
    markup.add("قسم النماذج 📝", "رجوع للبداية 🏠")
    
    bot.send_message(message.chat.id, f"📖 مقرر: {message.text}\nاختر القسم الدراسي لعرض الملفات:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["قسم المحاضرات 🟢", "قسم التمارين 🧪", "قسم النماذج 📝"])
def handle_sections(message):
    if not check_status(message): return
    uid = message.from_user.id
    if uid not in USER_STATE or "course" not in USER_STATE[uid]: return
    
    section = message.text
    state = USER_STATE[uid]
    
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, file_name FROM files 
        WHERE level=? AND semester=? AND course=? AND section=?
    """, (state["level"], state["semester"], state["course"], section))
    files = cursor.fetchall()
    conn.close()
    
    if not files:
        bot.send_message(message.chat.id, "📭 هذا القسم فارغ حالياً، لم يتم رفع أي ملفات هنا بعد.")
        return
        
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    for fid, fname in files:
        markup.add(telebot.types.InlineKeyboardButton(text=fname, callback_data=f"dl_{fid}"))
        
    bot.send_message(message.chat.id, f"📥 ملفات {section} المتاحة حالياً:\n(اضغط على الملف للتحميل المباشر)", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))
def download_file_callback(call):
    file_db_id = call.data.split("_")[1]
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, file_name, downloads_count FROM files WHERE id=?", (file_db_id,))
    res = cursor.fetchone()
    
    if res:
        file_id, fname, count = res
        cursor.execute("UPDATE files SET downloads_count = downloads_count + 1 WHERE id=?", (file_db_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, text=f"جاري جلب: {fname}")
        try:
            bot.send_document(call.message.chat.id, file_id, caption=f"📄 {fname}\n اللجنة العلمية - قنوات الكلية")
        except Exception as e:
            bot.send_message(call.message.chat.id, "❌ حدثت مشكلة أثناء جلب الملف من سيرفر التلجرام، يرجى إبلاغ اللجنة.")
    else:
        conn.close()
        bot.answer_callback_query(call.id, text="❌ العفو، هذا الملف غير موجود أو تم حذفه مؤخراً.")

# --- 2. لوحة تحكم الإدارة الكاملة والمطورة والآمنة ---

@bot.message_handler(func=lambda m: m.text == "لوحة تحكم الإدارة ⚙️")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "عذراً، هذا القسم مخصص لأعضاء اللجنة العلمية فقط.")
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📥 رفع وتحويل الملفات للقسم", "🗑️ حذف ملف واحد")
    markup.add("🗑️ حذف قسم بداخل مقرر", "🗑️ حذف مقرر بالكامل")
    markup.add("✏️ تعديل اسم ملف/مقرر", "🔀 نقل ملف بين المقررات")
    markup.add("👤 إضافة مشرف جديد", "👤 حذف وإلغاء مشرف")
    markup.add("📢 إرسال إشعار فوري", "⏳ جدولة إشعار للطلاب")
    markup.add("📊 إحصائيات التحميل", "🔧 تفعيل/إلغاء الصيانة")
    markup.add("رجوع للبداية 🏠")
    
    bot.send_message(message.chat.id, "⚙️ مرحباً بك في غرفة التحكم المتقدمة للجنة العلمية. اختر الإجراء المطلوب:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔧 تفعيل/إلغاء الصيانة" and is_admin(m.from_user.id))
def toggle_maintenance(message):
    global MAINTENANCE_MODE
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "عذراً، تفعيل وإلغاء وضع الصيانة متاح لمالك البوت الأساسي فقط.")
        return
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    status = "🔴 (مفعّل الآن - البوت مغلق للطلاب)" if MAINTENANCE_MODE else "🟢 (معطل الآن - البوت متاح للجميع)"
    bot.reply_to(message, f"🛠️ وضع الصيانة الحالي للبوت: {status}")

@bot.message_handler(func=lambda m: m.text == "📥 رفع وتحويل الملفات للقسم" and is_admin(m.from_user.id))
def start_upload_flow(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("المستوى الأول 📕", "المستوى الثاني 📗", "لوحة تحكم الإدارة ⚙️")
    msg = bot.send_message(message.chat.id, "اختر المستوى الذي تود الرفع والتحويل إليه أولاً:", reply_markup=markup)
    bot.register_next_step_handler(msg, upload_step_semester)

def upload_step_semester(message):
    if message.text == "لوحة تحكم الإدارة ⚙️": return admin_panel(message)
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
    msg = bot.send_message(message.chat.id, "اختر القسم الدقيق للرفع وحفظ التوجيه:", reply_markup=markup)
    bot.register_next_step_handler(msg, upload_step_get_file, level, semester, course)

def upload_step_get_file(message, level, semester, course):
    section = message.text
    msg = bot.send_message(message.chat.id, "📥 حسناً! الآن قم بعمل **تحويل (Forward)** لأي ملف أو محاضرة من القناة إلى هنا مباشرة، أو قم برفع الملف هنا وسأقوم بحفظه تلقائياً في التبويب المناسب:")
    bot.register_next_step_handler(msg, upload_process_final, level, semester, course, section)

def upload_process_final(message, level, semester, course, section):
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        
        conn = sqlite3.connect("committee.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO files (level, semester, course, section, file_name, file_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (level, semester, course, section, file_name, file_id))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ تم حفظ وحفظ المعرف الخاص بالملف بنجاح!\n📋 الاسم المعتمد: {file_name}\n📂 القسم الدراسي: {section}", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "❌ خطأ، لم تقم بإرسال أو تحويل ملف مستند (Document)، يرجى إعادة الإجراء بشكل صحيح عبر لوحة التحكم.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "👤 إضافة مشرف جديد" and is_admin(m.from_user.id))
def add_admin_flow(message):
    msg = bot.send_message(message.chat.id, "قم بإرسال الـ ID الرقمي للمشرف الجديد المراد ضمه للجنة العلمية:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    try:
        new_id = int(message.text)
        conn = sqlite3.connect("committee.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, role) VALUES (?, 'admin')", (new_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ تم إضافة المشرف ذو الرقم {new_id} بنجاح ومنحه كافة صلاحيات الإشراف.")
    except:
        bot.reply_to(message, "❌ القيمة المدخلة غير صحيحة، يرجى كتابة الـ ID كأرقام فقط.")

@bot.message_handler(func=lambda m: m.text == "👤 حذف وإلغاء مشرف" and is_admin(m.from_user.id))
def remove_admin_flow(message):
    msg = bot.send_message(message.chat.id, "قم بإرسال الـ ID الرقمي للمشرف المراد إلغاء صلاحياته:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(message):
    try:
        target_id = int(message.text)
        if target_id == OWNER_ID:
            bot.reply_to(message, "❌ لا يمكن إلغاء المالك الأساسي للبوت.")
            return
        conn = sqlite3.connect("committee.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"🗑️ تم حذف المشرف بنجاح وسحب صلاحيات الإدارة.")
    except:
        bot.reply_to(message, "❌ لم تنجح العملية. يرجى كتابة أرقام فقط.")

@bot.message_handler(func=lambda m: m.text == "🗑️ حذف ملف واحد" and is_admin(m.from_user.id))
def start_delete_file(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب الاسم الدقيق للملف المراد مسحه تماماً من البوت:")
    bot.register_next_step_handler(msg, process_delete_file)

def process_delete_file(message):
    fname = message.text
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE file_name = ?", (fname,))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"🗑️ تم معالجة الطلب ومسح أي ملف باسم: '{fname}' من جداول العرض الشجرية بنجاح.")

@bot.message_handler(func=lambda m: m.text == "🔀 نقل ملف بين المقررات" and is_admin(m.from_user.id))
def start_move_file(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب الاسم الدقيق للملف المراد نقله:")
    bot.register_next_step_handler(msg, process_move_file_step2)

def process_move_file_step2(message):
    fname = message.text
    msg = bot.send_message(message.chat.id, f"اكتب اسم المقرر الجديد المراد نقل الملف '{fname}' إليه بدقة:")
    bot.register_next_step_handler(msg, process_move_file_final, fname)

def process_move_file_final(message, fname):
    new_course = message.text
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET course = ? WHERE file_name = ?", (new_course, fname))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"🔀 تم نقل الملف '{fname}' بنجاح إلى تبويب مقرر '{new_course}'.")

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات التحميل" and is_admin(m.from_user.id))
def show_real_stats(message):
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_name, downloads_count FROM files ORDER BY downloads_count DESC LIMIT 5")
    rows = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_students = cursor.fetchone()[0]
    conn.close()
    
    stats_text = f"📊 **إحصائيات تفاعل واستخدام الطلاب للبوت:**\n\n👥 إجمالي عدد الطلاب المشتركين: {total_students}\n\n🔝 **أكثر 5 ملفات تم تحميلها من قبل الطلاب:**\n"
    for idx, (name, count) in enumerate(rows, 1):
        stats_text += f"{idx}. 📄 {name} -> 📥 ({count} مرة)\n"
        
    bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")

def send_broadcast_to_all(text):
    conn = sqlite3.connect("committee.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    uids = cursor.fetchall()
    conn.close()
    for u in uids:
        try: bot.send_message(u[0], f"📢 **تنبيه وإشعار من اللجنة العلمية الطلابية:**\n\n{text}", parse_mode="Markdown")
        except: pass

@bot.message_handler(func=lambda m: m.text == "📢 إرسال إشعار فوري" and is_admin(m.from_user.id))
def admin_broadcast_now(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب رسالة الإشعار الترحيبية أو التعميمية ليتم بثها فوراً:")
    bot.register_next_step_handler(msg, process_broadcast_now)

def process_broadcast_now(message):
    send_broadcast_to_all(message.text)
    bot.reply_to(message, "✅ تم بث الرسالة بنجاح لجميع المشتركين.")

@bot.message_handler(func=lambda m: m.text == "⏳ جدولة إشعار للطلاب" and is_admin(m.from_user.id))
def admin_broadcast_schedule(message):
    msg = bot.send_message(message.chat.id, "✍️ اكتب رسالة الإشعار التي تريد جدولتها للتوقيت اللاحق:")
    bot.register_next_step_handler(msg, process_broadcast_schedule_time)

def process_broadcast_schedule_time(message):
    text = message.text
    msg = bot.send_message(message.chat.id, "⏰ أرسل وقت النشر بالصيغة الشاملة التالية تماماً:\n`YYYY-MM-DD HH:MM:SS`\nمثال: `2026-06-05 15:30:00`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_broadcast_schedule_final, text)

def process_broadcast_schedule_final(message, text):
    time_string = message.text
    try:
        parsed_time = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
        scheduler.add_job(send_broadcast_to_all, 'date', run_date=parsed_time, args=[text])
        bot.reply_to(message, f"⏳ تم جدولة الإشعار ليرسل تلقائياً بالتوقيت المحدد: {time_string}")
    except ValueError:
        bot.reply_to(message, "❌ صيغة الوقت خاطئة ولم يتم فهمها، يرجى مراجعة المثال الموضح.")

# تشغيل وتجهيز المشروع
if __name__ == "__main__":
    keep_alive()
    print("البوت الأكاديمي المتكامل يعمل بأعلى كفاءة الآن...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
