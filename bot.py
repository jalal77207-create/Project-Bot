import telebot
import json
import os

# 1. إعداد المتغيرات الأساسية
BOT_TOKEN = "8756404288:AAEAwoywtjI_m3QiI8X3p-PaV7FMDttYRSs"
bot = telebot.TeleBot(BOT_TOKEN)

# معرف المالك الأساسي (قم بوضع الـ ID الخاص بك هنا)
OWNER_ID = 1084564343 

# ملف بسيط لحفظ معرفات المشرفين حتى لا تُفقد عند إعادة تشغيل الـ Server
ADMINS_FILE = "admins.json"

def load_admins():
    """تحميل قائمة المشرفين من الملف، وإذا لم يوجد، يتم تعيين المالك كأول مشرف."""
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r") as file:
            return json.load(file)
    return [OWNER_ID]

def save_admins(admins_list):
    """حفظ قائمة المشرفين في الملف."""
    with open(ADMINS_FILE, "w") as file:
        json.dump(admins_list, file)

# تحميل المشرفين عند بدء تشغيل الكود
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
