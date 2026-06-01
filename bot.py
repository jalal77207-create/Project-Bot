import telebot
import json
import os
from flask import Flask
from threading import Thread

# --- إعداد خادم الويب للعمل مجاناً على Render ---
app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل بنجاح وبشكل مجاني!"

def run_server():
    # Render يمرر المنفذ تلقائياً عبر متغير بيئي اسمه PORT، وإذا لم يجده يستخدم 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """تشغيل خادم الويب في خلفية الكود"""
    t = Thread(target=run_server)
    t.start()
# ---------------------------------------------

# 1. إعداد المتغيرات الأساسية وقراءة التوكن بأمان من سيرفر Render
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
bot = telebot.TeleBot(BOT_TOKEN)

# معرف المالك الأساسي
OWNER_ID = 1084564343

# ملف حفظ معرفات المشرفين
ADMINS_FILE = "/opt/render/project/src/admins.json" if os.path.exists("/opt/render/project/src/") else "admins.json"

def load_admins():
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, "r") as file:
                return json.load(file)
        except:
            return [OWNER_ID]
    return [OWNER_ID]

def save_admins(admins_list):
    with open(ADMINS_FILE, "w") as file:
        json.dump(admins_list, file)

admins = load_admins()

def is_admin(user_id):
    return user_id in admins

# 2. الأوامر الأساسية
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        bot.reply_to(message, "أهلاً بك يا مشرف في لوحة تحكم بوت اللجنة العلمية!\nالخيارات المتاحة لك:\n- رفع ملخصات ومحاضرات جديدة.\n- إدارة المحتوى.")
    else:
        bot.reply_to(message, "مرحباً بك أيها الطالب في البوت الأكاديمي لقسم الذكاء الاصطناعي. يمكنك هنا تصفح المحاضرات والملخصات المتاحة.")

# 3. أوامر إدارة المشرفين
@bot.message_handler(commands=['add_admin'])
def add_admin(message):
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        try:
            new_admin_id = int(message.text.split()[1])
            if new_admin_id not in admins:
                admins.append(new_admin_id)
                save_admins(admins)
                bot.reply_to(message, f"تم إضافة المشرف ذو المعرف {new_admin_id} بنجاح إلى اللجنة.")
            else:
                bot.reply_to(message, "هذا المستخدم مسجل كمشرف بالفعل.")
        except (IndexError, ValueError):
            bot.reply_to(message, "صيغة غير صحيحة. الرجاء إرسال الأمر متبوعاً بالـ ID.\nمثال: /add_admin 987654321")
    else:
        bot.reply_to(message, "عذراً، هذا الإجراء مخصص لمالك البوت (Owner) فقط.")

@bot.message_handler(commands=['remove_admin'])
def remove_admin(message):
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        try:
            admin_to_remove = int(message.text.split()[1])
            if admin_to_remove == OWNER_ID:
                bot.reply_to(message, "لا يمكنك إزالة نفسك كمالك للبوت!")
            elif admin_to_remove in admins:
                admins.remove(admin_to_remove)
                save_admins(admins)
                bot.reply_to(message, f"تم سحب صلاحيات الإشراف من المعرف {admin_to_remove}.")
            else:
                bot.reply_to(message, "هذا المعرف غير موجود في قائمة المشرفين.")
        except (IndexError, ValueError):
            bot.reply_to(message, "صيغة غير صحيحة. الرجاء إرسال الأمر متبوعاً بالـ ID.\nمثال: /remove_admin 987654321")
    else:
        bot.reply_to(message, "عذراً، هذا الإجراء مخصص لمالك البوت (Owner) فقط.")

# 4. تشغيل البوت والسيرفر معاً
if __name__ == "__main__":
    print("جاري تشغيل خادم الويب...")
    keep_alive()  # تشغيل سيرفر الويب المدمج لخدعة Render مجاناً
    
    print("البوت الأكاديمي يعمل الآن...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
    if is_admin(user_id):
        bot.reply_to(message, "أهلاً بك يا مشرف في لوحة تحكم بوت اللجنة العلمية!\nالخيارات المتاحة لك:\n- رفع ملخصات ومحاضرات جديدة.\n- إدارة المحتوى.")
    else:
        bot.reply_to(message, "مرحباً بك أيها الطالب في البوت الأكاديمي لقسم الذكاء الاصطناعي. يمكنك هنا تصفح المحاضرات والملخصات المتاحة.")

# 3. أوامر إدارة المشرفين (مخصصة للمالك فقط)
@bot.message_handler(commands=['add_admin'])
def add_admin(message):
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        try:
            # استخراج الـ ID من الرسالة
            new_admin_id = int(message.text.split()[1])
            if new_admin_id not in admins:
                admins.append(new_admin_id)
                save_admins(admins)
                bot.reply_to(message, f"تم إضافة المشرف ذو المعرف {new_admin_id} بنجاح إلى اللجنة.")
            else:
                bot.reply_to(message, "هذا المستخدم مسجل كمشرف بالفعل.")
        except (IndexError, ValueError):
            bot.reply_to(message, "صيغة غير صحيحة. الرجاء إرسال الأمر متبوعاً بالـ ID.\nمثال: /add_admin 987654321")
    else:
        bot.reply_to(message, "عذراً، هذا الإجراء مخصص لمالك البوت (Owner) فقط.")

@bot.message_handler(commands=['remove_admin'])
def remove_admin(message):
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        try:
            admin_to_remove = int(message.text.split()[1])
            if admin_to_remove == OWNER_ID:
                bot.reply_to(message, "لا يمكنك إزالة نفسك كمالك للبوت!")
            elif admin_to_remove in admins:
                admins.remove(admin_to_remove)
                save_admins(admins)
                bot.reply_to(message, f"تم سحب صلاحيات الإشراف من المعرف {admin_to_remove}.")
            else:
                bot.reply_to(message, "هذا المعرف غير موجود في قائمة المشرفين.")
        except (IndexError, ValueError):
            bot.reply_to(message, "صيغة غير صحيحة. الرجاء إرسال الأمر متبوعاً بالـ ID.\nمثال: /remove_admin 987654321")
    else:
        bot.reply_to(message, "عذراً، هذا الإجراء مخصص لمالك البوت (Owner) فقط.")

# 4. تشغيل البوت باستمرار (Polling)
if __name__ == "__main__":
    print("البوت الأكاديمي يعمل الآن...")
    # استخدام infinity_polling لضمان استمرار البوت في العمل عند حدوث أخطاء شبكة
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
