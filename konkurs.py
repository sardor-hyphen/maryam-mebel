import sqlite3
import logging
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import Forbidden

# --- SOZLAMALAR ---
BOT_TOKEN = "7867140377:AAHkDHowZRYZvOoyGgu2uGRJ1jvbCQhZTJg" 

REQUIRED_CHANNELS = {
    "@uzb_python": "https://t.me/uzb_python",
    "@prmg_uz": "https://t.me/prmg_uz"
}

DB_NAME = "konkurs_bot.db"

# --- Konkurs Ma'lumotlari (Oson o'zgartirish uchun) ---
CONTEST_INFO_TEXT = """
🏆 <b>Konkursimiz Haqida Ma'lumot</b> 🏆

<b>Konkursning maqsadi:</b>
Eng ko'p do'stingizni botimizga taklif qilish!

<b>Konkurs muddati:</b>
31-Dekabr, 23:59 gacha

<b>Sovrinlar:</b>
🥇 1-o'rin: 1,000,000 so'm
🥈 2-o'rin: 500,000 so'm
🥉 3-o'rin: 250,000 so'm

<b>Qoidalar:</b>
1. Barcha shart bo'lgan kanallarga a'zo bo'ling.
2. O'zingizning shaxsiy havolangiz orqali do'stlaringizni taklif qiling.
3. Har bir faol taklif uchun sizga 1 ball beriladi.
4. Qo'shimcha bonuslar uchun bosqichlarni bajaring!

Omad tilaymiz! ✨
"""

# --- Bosqichlar va Bonuslar ---
# Format: {takliflar_soni: bonus_ballari}
MILESTONES = {
    5: 2,
    10: 3,
    25: 7,
    50: 10,
    100: 15,
    200: 20,
}

# --- Logger sozlamalari ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Ma'lumotlar Bazasi Funksiyalari ---

def setup_database():
    """Ma'lumotlar bazasini sozlaydi va yangi ustunlarni qo'shadi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            referral_count INTEGER DEFAULT 0,
            referrer_id INTEGER
        )
    """)
    # Eski versiyadan yangilayotganlar uchun ustun qo'shish
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN milestones_achieved TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass # Ustun allaqachon mavjud bo'lsa
    
    conn.commit()
    conn.close()

# --- Bonus va Mukofotlar Funksiyasi ---

async def check_and_award_milestones(referrer_id: int, new_score: int, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining bosqichlardan o'tganligini tekshiradi va bonus beradi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT milestones_achieved FROM users WHERE user_id = ?", (referrer_id,))
    result = cursor.fetchone()
    if not result:
        return

    achieved_str = result[0]
    achieved_list = achieved_str.split(',') if achieved_str else []
    
    total_bonus_awarded = 0
    newly_achieved = []

    for milestone, bonus in sorted(MILESTONES.items()):
        if new_score >= milestone and str(milestone) not in achieved_list:
            total_bonus_awarded += bonus
            newly_achieved.append(str(milestone))
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 <b>Ajoyib! Siz {milestone} ta do'stingizni taklif qildingiz!</b>\n\n"
                         f"🎁 Sizga mukofot sifatida <b>+{bonus} bonus ball</b> taqdim etildi!",
                    parse_mode=ParseMode.HTML
                )
            except Forbidden:
                logger.warning(f"Foydalanuvchi {referrer_id} botni bloklagan.")
            except Exception as e:
                logger.error(f"Mukofot xabarini yuborishda xato: {e}")

    if total_bonus_awarded > 0:
        cursor.execute("UPDATE users SET referral_count = referral_count + ? WHERE user_id = ?", (total_bonus_awarded, referrer_id))
        
        updated_achieved_str = ",".join(achieved_list + newly_achieved)
        cursor.execute("UPDATE users SET milestones_achieved = ? WHERE user_id = ?", (updated_achieved_str, referrer_id))
        
        conn.commit()

    conn.close()

# --- Asosiy Bot Funksiyalari (avvalgi kod bilan bir xil, lekin chaqiruvlar qo'shilgan) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    
    referrer_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    db_user = cursor.fetchone()

    if not db_user:
        cursor.execute(
            "INSERT INTO users (user_id, full_name, username, referrer_id, milestones_achieved) VALUES (?, ?, ?, ?, '')",
            (user_id, user.full_name, user.username, referrer_id)
        )
        conn.commit()
        
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
            conn.commit()
            
            cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (referrer_id,))
            new_score = cursor.fetchone()[0]

            try:
                await context.bot.send_message(
                    chat_id=referrer_id, 
                    text=f"🎉 Tabriklaymiz! Siz <b>{user.full_name}</b>ni taklif qildingiz va sizga 1 ball qo'shildi.",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.warning(f"Referrerga xabar yuborishda xato: {e}")

            # BONUSLARNI TEKSHIRISH
            await check_and_award_milestones(referrer_id, new_score, context)
    
    conn.close()
    
    unsubscribed = await check_subscription(user_id, context)
    if unsubscribed:
        await ask_for_subscription(update, context, unsubscribed)
    else:
        await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asosiy menyuni ko'rsatadi."""
    keyboard = [
        ["🏆 Liderlar", "📊 Mening natijalarim"],
        ["🔗 Mening linkim", "ℹ️ Konkurs haqida"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    message_text = "✅ Tabriklaymiz! Siz barcha shartlarni bajardingiz.\n\n" \
                   "Asosiy menyudan foydalanishingiz mumkin!"
    if update.callback_query:
        await context.bot.send_message(chat_id=update.effective_user.id, text=message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Asosiy menyudagi matnli tugmalarni boshqaradi."""
    text = update.message.text
    if text == "🔗 Mening linkim":
        await get_my_link(update, context)
    elif text == "📊 Mening natijalarim":
        await get_my_results(update, context)
    elif text == "🏆 Liderlar":
        await show_leaderboard(update, context)
    elif text == "ℹ️ Konkurs haqida":
        await show_info(update, context) # Yangi funksiya

async def get_my_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchining shaxsiy taklif havolasini yuboradi."""
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    
    share_text = f"🚀 Ajoyib konkursda qatnashing va sovrinlar yutib oling!\n\nBotga qo'shilish uchun havola:\n{link}"

    # Inline tugma yaratish
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("↗️ Do'stga ulashish", switch_inline_query=share_text)]
    ])

    await update.message.reply_text(
        f"Sizning shaxsiy taklif havolangiz:\n\n"
        f"👉 `{link}`\n\n"
        f"Ushbu havolani do'stlaringizga yuboring yoki quyidagi tugma orqali ulashing.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Konkurs haqidagi ma'lumotni ko'rsatadi."""
    await update.message.reply_text(CONTEST_INFO_TEXT, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def broadcast_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Barcha foydalanuvchilarga eslatma yuboradi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    all_users = cursor.fetchall()
    
    # Liderlar ro'yxatini olish
    cursor.execute("SELECT full_name, referral_count FROM users ORDER BY referral_count DESC LIMIT 5")
    leaders = cursor.fetchall()
    conn.close()

    if not leaders:
        return # Agar liderlar bo'lmasa, xabar yubormaymiz

    leader_text = "🏆 <b>Liderlar ro'yxati (Top 5)</b> 🏆\n\n"
    for i, leader in enumerate(leaders):
        name, count = leader
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        medal = medals.get(i, f"<b>{i+1}.</b>")
        leader_text += f"{medal} {name} - {count} ball\n"
    
    message_text = f"🔔 <b>Konkurs Eslatmasi!</b>\n\n{leader_text}\nSiz ham faol bo'ling va g'oliblar qatoridan joy oling!"

    for user in all_users:
        user_id = user[0]
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text, parse_mode=ParseMode.HTML)
        except Forbidden:
            logger.warning(f"Foydalanuvchi {user_id} botni bloklagan. Xabar yuborilmadi.")
        except Exception as e:
            logger.error(f"Xabarni {user_id} ga yuborishda xato: {e}")

# Qolgan funksiyalar (check_subscription, ask_for_subscription, va hokazo) avvalgi kod bilan bir xil,
# ularni o'zgartirish shart emas. Shuning uchun bu yerga to'liq qayta yozmadim, lekin ular ham kodda bo'lishi kerak.
# To'liq kod uchun avvalgi javobdagi funksiyalarni ham qo'shib qo'ying.
# Yaxshisi, pastdagi to'liq kod blokini ishlating.

# --- To'liq funksional kod uchun birlashtirilgan ---

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> list:
    unsubscribed_channels = []
    for channel_username in REQUIRED_CHANNELS.keys():
        try:
            member = await context.bot.get_chat_member(chat_id=channel_username, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed_channels.append(channel_username)
        except Exception as e:
            logger.error(f"Kanallar a'zoligini tekshirishda xatolik: {e} - Kanal: {channel_username}")
            unsubscribed_channels.append(channel_username) 
    return unsubscribed_channels

async def ask_for_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE, unsubscribed_channels: list):
    user = update.effective_user
    buttons = []
    is_callback = update.callback_query and "check_subscription" in update.callback_query.data
    if is_callback:
        text = f"❌ Kechirasiz, <b>{user.full_name}</b>, siz hali ham quyidagi kanallarga a'zo bo'lmadingiz:\n\n"
    else:
        text = f"Salom, <b>{user.full_name}</b>!\n\nKonkursimizda qatnashish uchun quyidagi kanallarga a'zo bo'lishingiz kerak:\n\n"
        
    for channel_username in unsubscribed_channels:
        channel_link = REQUIRED_CHANNELS.get(channel_username, "")
        buttons.append([InlineKeyboardButton(text=f"➡️ {channel_username}", url=channel_link)])
    
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("A'zolik tekshirilmoqda...")
    user_id = query.from_user.id
    unsubscribed = await check_subscription(user_id, context)
    
    if unsubscribed:
        await ask_for_subscription(update, context, unsubscribed)
    else:
        await query.message.delete()
        await show_main_menu(update, context)

async def get_my_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT referral_count FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    count = result[0] if result else 0
    await update.message.reply_text(f"📊 Sizning umumiy balingiz: <b>{count} ball</b>.", parse_mode=ParseMode.HTML)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, referral_count FROM users ORDER BY referral_count DESC LIMIT 10")
    leaders = cursor.fetchall()
    conn.close()
    if not leaders:
        await update.message.reply_text("Hozircha liderlar ro'yxati bo'sh.")
        return
    text = "🏆 <b>Liderlar ro'yxati (Top 10)</b> 🏆\n\n"
    for i, leader in enumerate(leaders):
        name, count = leader
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        medal = medals.get(i, f"<b>{i+1}.</b>")
        text += f"{medal} {name} - {count} ball\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


def main() -> None:
    """Botni ishga tushiradi."""
    setup_database()

    application = Application.builder().token(BOT_TOKEN).build()

    # Job Queue ni olish
    job_queue = application.job_queue

    # Kundalik eslatmani rejalashtirish (Toshkent vaqti bilan har kuni soat 12:00 da)
    job_queue.run_daily(
        broadcast_reminder,
        time=datetime.time(hour=12, minute=0, tzinfo=pytz.timezone('Asia/Tashkent')),
        name="daily_reminder"
    )

    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", show_info))
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    application.run_polling()

if __name__ == "__main__":
    main()