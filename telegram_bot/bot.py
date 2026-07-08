"""
SANS PMS — Telegram Bot
Bilingual (Arabic / English) field reporting bot
"""
import asyncio
import logging
import os
import json
from datetime import date, datetime
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

import httpx
import psycopg2

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_URL = os.environ.get("API_BASE_URL", "http://backend:8000")
DB_URL = os.environ.get("DATABASE_URL", "")

# ─── Conversation States ──────────────────────────────────────

(
    LANG_SELECT,
    MAIN_MENU,
    # Daily Report
    DR_SELECT_PROJECT,
    DR_WEATHER,
    DR_TEMP,
    DR_WORK_DONE,
    DR_DELAYS,
    DR_MANPOWER_COUNT,
    DR_PHOTOS,
    DR_CONFIRM,
    # Attendance
    ATT_ACTION,
    ATT_CONFIRM,
    # AI Chat
    AI_QUESTION,
    # Leave
    LEAVE_TYPE,
    LEAVE_START,
    LEAVE_END,
    LEAVE_REASON,
) = range(17)

# ─── Translations ─────────────────────────────────────────────

T = {
    "ar": {
        "welcome": "🏗️ *مرحباً في نظام سانس لإدارة المشاريع*\n\nاختر لغتك:",
        "main_menu": "📋 *القائمة الرئيسية*\n\nمرحباً {name}! اختر ما تريد:",
        "daily_report": "📝 تقرير يومي",
        "attendance": "✅ الحضور والانصراف",
        "my_status": "📊 حالتي",
        "ask_ai": "🤖 اسأل الذكاء الاصطناعي",
        "leave_request": "🏖️ طلب إجازة",
        "select_project": "📂 اختر المشروع:",
        "select_weather": "🌤️ حالة الطقس:",
        "enter_temp": "🌡️ أدخل درجة الحرارة (مثال: 38):",
        "enter_work": "⚒️ صِف أعمال اليوم بإيجاز:",
        "enter_delays": "⚠️ هل هناك تأخيرات أو عوائق؟ (اكتب 'لا' إذا لم يكن):",
        "enter_manpower": "👷 عدد العمال اليوم:",
        "send_photos": "📸 أرسل صور الموقع (أو اكتب 'تخطي'):",
        "confirm_report": "✅ تأكيد إرسال التقرير؟",
        "report_sent": "✅ تم إرسال التقرير بنجاح!",
        "check_in": "📍 تسجيل الحضور",
        "check_out": "🚪 تسجيل الانصراف",
        "checked_in": "✅ تم تسجيل حضورك في {time}",
        "checked_out": "✅ تم تسجيل انصرافك في {time}\nساعات العمل: {hours}",
        "ask_question": "🤖 اكتب سؤالك وسأجيبك:",
        "thinking": "⏳ جاري التحليل...",
        "error": "❌ حدث خطأ. حاول مرة أخرى.",
        "not_registered": "⚠️ حسابك غير مرتبط بالنظام.\nتواصل مع المدير لربط Telegram ID.",
        "weather_options": ["☀️ مشمس", "⛅ غائم جزئياً", "☁️ غائم", "🌧️ ممطر", "🌪️ عاصف", "😶‍🌫️ ضبابي", "💨 عاصف رملي"],
        "sunny": "sunny", "cloudy": "cloudy", "partly_cloudy": "partly_cloudy",
        "rainy": "rainy", "stormy": "stormy", "foggy": "foggy", "dusty": "dusty",
        "yes": "نعم ✅", "no": "لا ❌", "back": "🔙 رجوع", "cancel": "❌ إلغاء",
        "skip": "تخطي",
    },
    "en": {
        "welcome": "🏗️ *Welcome to SANS Project Management System*\n\nSelect your language:",
        "main_menu": "📋 *Main Menu*\n\nHello {name}! What would you like to do?",
        "daily_report": "📝 Daily Report",
        "attendance": "✅ Check In / Out",
        "my_status": "📊 My Status",
        "ask_ai": "🤖 Ask AI Assistant",
        "leave_request": "🏖️ Leave Request",
        "select_project": "📂 Select Project:",
        "select_weather": "🌤️ Weather Condition:",
        "enter_temp": "🌡️ Enter temperature in °C (e.g., 38):",
        "enter_work": "⚒️ Briefly describe today's work:",
        "enter_delays": "⚠️ Any delays or constraints? (type 'none' if no):",
        "enter_manpower": "👷 Number of workers today:",
        "send_photos": "📸 Send site photos (or type 'skip'):",
        "confirm_report": "✅ Confirm submitting the report?",
        "report_sent": "✅ Report submitted successfully!",
        "check_in": "📍 Check In",
        "check_out": "🚪 Check Out",
        "checked_in": "✅ Checked in at {time}",
        "checked_out": "✅ Checked out at {time}\nHours worked: {hours}",
        "ask_question": "🤖 Type your question:",
        "thinking": "⏳ Analyzing...",
        "error": "❌ An error occurred. Please try again.",
        "not_registered": "⚠️ Your account is not linked.\nContact your admin to link your Telegram ID.",
        "weather_options": ["☀️ Sunny", "⛅ Partly Cloudy", "☁️ Cloudy", "🌧️ Rainy", "🌪️ Stormy", "😶‍🌫️ Foggy", "💨 Dusty"],
        "sunny": "sunny", "cloudy": "cloudy", "partly_cloudy": "partly_cloudy",
        "rainy": "rainy", "stormy": "stormy", "foggy": "foggy", "dusty": "dusty",
        "yes": "Yes ✅", "no": "No ❌", "back": "🔙 Back", "cancel": "❌ Cancel",
        "skip": "skip",
    }
}


# ─── DB Helpers ───────────────────────────────────────────────

def get_db_conn():
    return psycopg2.connect(DB_URL)


def get_user_by_telegram(telegram_id: int):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.full_name, u.full_name_ar, u.company_id, u.email,
                   ts.language, ts.state, ts.state_data
            FROM users u
            LEFT JOIN telegram_sessions ts ON ts.telegram_id = %s
            WHERE u.telegram_id = %s
        """, (telegram_id, telegram_id))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        logger.error(f"DB error: {e}")
        return None


def get_user_projects(company_id: str):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, code, name, name_ar FROM projects
            WHERE company_id = %s AND status = 'active'
            ORDER BY name
        """, (company_id,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"DB error: {e}")
        return []


def save_telegram_session(telegram_id: int, user_id: str, state: str, state_data: dict, language: str = "ar"):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO telegram_sessions (telegram_id, user_id, state, state_data, language, last_active)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (telegram_id) DO UPDATE SET
                state = EXCLUDED.state,
                state_data = EXCLUDED.state_data,
                language = EXCLUDED.language,
                last_active = NOW()
        """, (telegram_id, user_id, state, json.dumps(state_data), language))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Session save error: {e}")


async def call_api(endpoint: str, method: str = "GET", data: dict = None, user_id: str = None) -> dict:
    """Call the FastAPI backend."""
    headers = {"X-Internal-User-ID": user_id or ""}
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "POST":
            resp = await client.post(f"{API_URL}/api/v1/{endpoint}", json=data, headers=headers)
        else:
            resp = await client.get(f"{API_URL}/api/v1/{endpoint}", headers=headers)
        resp.raise_for_status()
        return resp.json()


# ─── Keyboard Builders ────────────────────────────────────────

def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = T[lang]
    return ReplyKeyboardMarkup([
        [t["daily_report"], t["attendance"]],
        [t["my_status"], t["ask_ai"]],
        [t["leave_request"]],
    ], resize_keyboard=True)


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ])


def yes_no_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = T[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["yes"], callback_data="yes"),
         InlineKeyboardButton(t["no"], callback_data="no")]
    ])


def weather_keyboard(lang: str) -> ReplyKeyboardMarkup:
    opts = T[lang]["weather_options"]
    rows = [[opts[i], opts[i+1]] for i in range(0, len(opts)-1, 2)]
    rows.append([opts[-1]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def projects_keyboard(projects: list) -> ReplyKeyboardMarkup:
    rows = [[f"{p[1]} — {p[3] or p[2]}"] for p in projects]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


# ─── Handlers ────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point — show language selector."""
    await update.message.reply_text(
        T["ar"]["welcome"],
        parse_mode="Markdown",
        reply_markup=lang_keyboard()
    )
    return LANG_SELECT


async def lang_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection."""
    query = update.callback_query
    await query.answer()
    lang = "ar" if query.data == "lang_ar" else "en"
    context.user_data["lang"] = lang
    telegram_id = query.from_user.id

    # Look up user
    user_row = get_user_by_telegram(telegram_id)
    if not user_row:
        await query.edit_message_text(T[lang]["not_registered"])
        return ConversationHandler.END

    user_id, name, name_ar, company_id, email, *_ = user_row
    display_name = name_ar if lang == "ar" and name_ar else name
    context.user_data.update({
        "user_id": str(user_id),
        "name": display_name,
        "company_id": str(company_id),
        "telegram_id": telegram_id,
    })
    save_telegram_session(telegram_id, str(user_id), "main_menu", {}, lang)

    await query.edit_message_text(
        T[lang]["main_menu"].format(name=display_name),
        parse_mode="Markdown"
    )
    await query.message.reply_text("↓", reply_markup=main_menu_keyboard(lang))
    return MAIN_MENU


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route from main menu."""
    lang = context.user_data.get("lang", "ar")
    text = update.message.text
    t = T[lang]

    if text == t["daily_report"]:
        return await start_daily_report(update, context)
    elif text == t["attendance"]:
        return await start_attendance(update, context)
    elif text == t["ask_ai"]:
        return await start_ai_chat(update, context)
    elif text == t["my_status"]:
        return await show_my_status(update, context)
    elif text == t["leave_request"]:
        return await start_leave_request(update, context)

    await update.message.reply_text("?", reply_markup=main_menu_keyboard(lang))
    return MAIN_MENU


# ─── Daily Report Flow ────────────────────────────────────────

async def start_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    company_id = context.user_data.get("company_id")
    projects = get_user_projects(company_id)

    if not projects:
        await update.message.reply_text("❌ لا توجد مشاريع نشطة." if lang == "ar" else "❌ No active projects.")
        return MAIN_MENU

    context.user_data["projects"] = {f"{p[1]} — {p[3] or p[2]}": str(p[0]) for p in projects}
    await update.message.reply_text(
        T[lang]["select_project"],
        reply_markup=projects_keyboard(projects)
    )
    return DR_SELECT_PROJECT


async def dr_project_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    text = update.message.text
    projects = context.user_data.get("projects", {})

    if text not in projects:
        await update.message.reply_text("❌" if lang == "ar" else "❌ Invalid project")
        return DR_SELECT_PROJECT

    context.user_data["report"] = {"project_id": projects[text], "project_name": text}
    await update.message.reply_text(T[lang]["select_weather"], reply_markup=weather_keyboard(lang))
    return DR_WEATHER


async def dr_weather_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    text = update.message.text
    weather_map = {
        "☀️": "sunny", "⛅": "partly_cloudy", "☁️": "cloudy",
        "🌧️": "rainy", "🌪️": "stormy", "😶‍🌫️": "foggy", "💨": "dusty"
    }
    weather = next((v for k, v in weather_map.items() if k in text), "sunny")
    context.user_data["report"]["weather_condition"] = weather
    await update.message.reply_text(T[lang]["enter_temp"], reply_markup=ReplyKeyboardRemove())
    return DR_TEMP


async def dr_temp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    try:
        temp = int(update.message.text.strip())
        context.user_data["report"]["weather_temp"] = temp
    except ValueError:
        pass
    await update.message.reply_text(T[lang]["enter_work"])
    return DR_WORK_DONE


async def dr_work_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    context.user_data["report"]["work_performed"] = update.message.text
    await update.message.reply_text(T[lang]["enter_delays"])
    return DR_DELAYS


async def dr_delays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    text = update.message.text
    context.user_data["report"]["delays_description"] = None if text.lower() in ["لا", "no", "none", "-"] else text
    await update.message.reply_text(T[lang]["enter_manpower"])
    return DR_MANPOWER_COUNT


async def dr_manpower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    try:
        count = int(update.message.text.strip())
        context.user_data["report"]["manpower_count"] = count
    except ValueError:
        context.user_data["report"]["manpower_count"] = 0
    await update.message.reply_text(T[lang]["send_photos"])
    return DR_PHOTOS


async def dr_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    photos = context.user_data["report"].get("photos", [])

    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        photos.append(file.file_path)
        context.user_data["report"]["photos"] = photos
        await update.message.reply_text(
            f"✅ {'صورة محفوظة' if lang == 'ar' else 'Photo saved'}. {'أرسل المزيد أو اكتب' if lang == 'ar' else 'Send more or type'} '{T[lang]['skip']}'."
        )
        return DR_PHOTOS

    # Build confirmation summary
    r = context.user_data["report"]
    summary = (
        f"📋 *{'ملخص التقرير' if lang == 'ar' else 'Report Summary'}*\n"
        f"{'المشروع' if lang == 'ar' else 'Project'}: {r.get('project_name')}\n"
        f"{'التاريخ' if lang == 'ar' else 'Date'}: {date.today().isoformat()}\n"
        f"{'الطقس' if lang == 'ar' else 'Weather'}: {r.get('weather_condition')} {r.get('weather_temp', '')}°C\n"
        f"{'الأعمال' if lang == 'ar' else 'Work'}: {r.get('work_performed', '')[:100]}\n"
        f"{'العمال' if lang == 'ar' else 'Workers'}: {r.get('manpower_count', 0)}\n"
        f"{'الصور' if lang == 'ar' else 'Photos'}: {len(photos)}\n"
    )
    await update.message.reply_text(
        summary, parse_mode="Markdown",
        reply_markup=yes_no_keyboard(lang)
    )
    return DR_CONFIRM


async def dr_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    query = update.callback_query
    await query.answer()

    if query.data != "yes":
        await query.edit_message_text("❌ " + ("تم الإلغاء" if lang == "ar" else "Cancelled"))
        return MAIN_MENU

    r = context.user_data["report"]
    await query.edit_message_text(T[lang]["thinking"])

    try:
        # Submit to API
        payload = {
            "project_id": r["project_id"],
            "report_date": date.today().isoformat(),
            "weather_condition": r.get("weather_condition", "sunny"),
            "weather_temp": r.get("weather_temp"),
            "work_performed": r.get("work_performed"),
            "work_performed_ar": r.get("work_performed") if lang == "ar" else None,
            "delays_description": r.get("delays_description"),
            "status": "submitted",
        }
        await call_api("reports/", "POST", payload, context.user_data.get("user_id"))
        await query.message.reply_text(T[lang]["report_sent"], reply_markup=main_menu_keyboard(lang))
    except Exception as e:
        logger.error(f"Report submit error: {e}")
        await query.message.reply_text(T[lang]["error"], reply_markup=main_menu_keyboard(lang))

    context.user_data.pop("report", None)
    return MAIN_MENU


# ─── Attendance Flow ──────────────────────────────────────────

async def start_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    t = T[lang]
    keyboard = ReplyKeyboardMarkup(
        [[t["check_in"], t["check_out"]], [t["cancel"]]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(t["attendance"], reply_markup=keyboard)
    return ATT_ACTION


async def att_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    t = T[lang]
    text = update.message.text
    now = datetime.now().strftime("%H:%M")

    if text == t["check_in"]:
        await update.message.reply_text(
            t["checked_in"].format(time=now),
            reply_markup=main_menu_keyboard(lang)
        )
    elif text == t["check_out"]:
        await update.message.reply_text(
            t["checked_out"].format(time=now, hours="8.0"),
            reply_markup=main_menu_keyboard(lang)
        )
    return MAIN_MENU


# ─── AI Chat Flow ─────────────────────────────────────────────

async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    await update.message.reply_text(T[lang]["ask_question"], reply_markup=ReplyKeyboardRemove())
    return AI_QUESTION


async def ai_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    question = update.message.text

    thinking_msg = await update.message.reply_text(T[lang]["thinking"])

    try:
        result = await call_api(
            "ai/chat",
            "POST",
            {"question": question, "language": lang},
            context.user_data.get("user_id")
        )
        answer = result.get("answer", T[lang]["error"])
        await thinking_msg.edit_text(f"🤖 {answer[:4000]}")
    except Exception as e:
        logger.error(f"AI error: {e}")
        await thinking_msg.edit_text(T[lang]["error"])

    await update.message.reply_text("↩️", reply_markup=main_menu_keyboard(lang))
    return MAIN_MENU


# ─── My Status ────────────────────────────────────────────────

async def show_my_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    name = context.user_data.get("name", "")
    today = date.today().isoformat()

    status_text = (
        f"👤 *{'معلوماتي' if lang == 'ar' else 'My Status'}*\n\n"
        f"{'الاسم' if lang == 'ar' else 'Name'}: {name}\n"
        f"{'التاريخ' if lang == 'ar' else 'Date'}: {today}\n\n"
        f"{'للمزيد من التفاصيل، تفضل بزيارة لوحة التحكم على المتصفح.' if lang == 'ar' else 'For full details, visit the web dashboard.'}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")
    return MAIN_MENU


async def start_leave_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    leave_types = (
        [["إجازة سنوية", "إجازة مرضية"], ["إجازة طارئة", "إجازة بدون راتب"]]
        if lang == "ar"
        else [["Annual Leave", "Sick Leave"], ["Emergency Leave", "Unpaid Leave"]]
    )
    await update.message.reply_text(
        "نوع الإجازة:" if lang == "ar" else "Leave Type:",
        reply_markup=ReplyKeyboardMarkup(leave_types, resize_keyboard=True, one_time_keyboard=True)
    )
    return LEAVE_TYPE


async def leave_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    context.user_data["leave"] = {"type": update.message.text}
    await update.message.reply_text(
        "تاريخ البداية (YYYY-MM-DD):" if lang == "ar" else "Start date (YYYY-MM-DD):",
        reply_markup=ReplyKeyboardRemove()
    )
    return LEAVE_START


async def leave_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    context.user_data["leave"]["start"] = update.message.text
    await update.message.reply_text("تاريخ النهاية (YYYY-MM-DD):" if lang == "ar" else "End date (YYYY-MM-DD):")
    return LEAVE_END


async def leave_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    context.user_data["leave"]["end"] = update.message.text
    await update.message.reply_text("سبب الإجازة:" if lang == "ar" else "Reason:")
    return LEAVE_REASON


async def leave_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    context.user_data["leave"]["reason"] = update.message.text

    l = context.user_data["leave"]
    msg = (
        f"✅ {'تم تقديم طلب إجازتك' if lang == 'ar' else 'Leave request submitted'}\n"
        f"النوع: {l['type']}\n"
        f"من: {l['start']} إلى: {l['end']}\n"
        f"السبب: {l['reason']}"
    )
    await update.message.reply_text(msg, reply_markup=main_menu_keyboard(lang))
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "ar")
    await update.message.reply_text(
        "❌ " + ("تم الإلغاء" if lang == "ar" else "Cancelled"),
        reply_markup=main_menu_keyboard(lang)
    )
    return MAIN_MENU


# ─── Main ─────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG_SELECT: [CallbackQueryHandler(lang_selected, pattern="^lang_")],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            DR_SELECT_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, dr_project_selected)],
            DR_WEATHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, dr_weather_selected)],
            DR_TEMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, dr_temp)],
            DR_WORK_DONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, dr_work_done)],
            DR_DELAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, dr_delays)],
            DR_MANPOWER_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, dr_manpower)],
            DR_PHOTOS: [
                MessageHandler(filters.PHOTO, dr_photos),
                MessageHandler(filters.TEXT & ~filters.COMMAND, dr_photos),
            ],
            DR_CONFIRM: [CallbackQueryHandler(dr_confirm, pattern="^(yes|no)$")],
            ATT_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, att_action)],
            AI_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_answer)],
            LEAVE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_type_selected)],
            LEAVE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_start)],
            LEAVE_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_end)],
            LEAVE_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_reason)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    logger.info("🤖 SANS Telegram Bot started (polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
