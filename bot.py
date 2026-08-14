import os
import sqlite3
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# =========================
# TASKS
# =========================

TASKS = [
    {"id": 1, "title": "Task 1", "url": "PASTE_TASK_LINK_1", "reward": 3},
    {"id": 2, "title": "Task 2", "url": "PASTE_TASK_LINK_2", "reward": 3},
    {"id": 3, "title": "Task 3", "url": "PASTE_TASK_LINK_3", "reward": 3},
    {"id": 4, "title": "Task 4", "url": "PASTE_TASK_LINK_4", "reward": 3},
    {"id": 5, "title": "Task 5", "url": "PASTE_TASK_LINK_5", "reward": 3},
    {"id": 6, "title": "Task 6", "url": "PASTE_TASK_LINK_6", "reward": 3},
    {"id": 7, "title": "Task 7", "url": "PASTE_TASK_LINK_7", "reward": 3},
    {"id": 8, "title": "Task 8", "url": "PASTE_TASK_LINK_8", "reward": 3},
    {"id": 9, "title": "Task 9", "url": "PASTE_TASK_LINK_9", "reward": 3},
    {"id": 10, "title": "Task 10", "url": "PASTE_TASK_LINK_10", "reward": 3},
]

# =========================
# DATABASE
# =========================

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    email TEXT DEFAULT '',
    balance REAL DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    task_id INTEGER,
    email TEXT,
    username TEXT,
    proof_file_id TEXT,
    status TEXT DEFAULT 'Pending',
    reward REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()

# =========================
# FLASK FOR RENDER
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Task Reward BD Bot is running!"

@app.route("/health")
def health():
    return "OK"


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    cur.execute("""
    INSERT OR IGNORE INTO users
    (telegram_id, username, first_name)
    VALUES (?, ?, ?)
    """, (
        user.id,
        user.username or "",
        user.first_name or ""
    ))

    db.commit()

    keyboard = [
        [InlineKeyboardButton("🎯 Get Task", callback_data="get_task")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("📊 My Tasks", callback_data="my_tasks")],
    ]

    await update.message.reply_text(
        "👋 Welcome to Task Reward BD!\n\n"
        "🎯 Complete tasks and earn rewards.\n\n"
        "📌 Task → Complete → Submit proof → Verification → Reward\n\n"
        "💰 Your approved earnings will be added to your balance.\n"
        "⚠️ Each task can only be completed once per Telegram account.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# BALANCE
# =========================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    cur.execute(
        "SELECT balance FROM users WHERE telegram_id=?",
        (query.from_user.id,)
    )

    row = cur.fetchone()
    balance = row[0] if row else 0

    await query.message.reply_text(
        f"💰 Your Balance: {balance:.2f} TK\n\n"
        "📌 Approved tasks are automatically added here.\n"
        "💵 Weekly payout will be processed by admin."
    )


# =========================
# GET TASK
# =========================

async def get_task(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    buttons = []

    for task in TASKS:

        cur.execute("""
        SELECT id FROM submissions
        WHERE telegram_id=? AND task_id=?
        """, (user_id, task["id"]))

        already = cur.fetchone()

        if not already:
            buttons.append([
                InlineKeyboardButton(
                    f"🎯 {task['title']} — {task['reward']} TK",
                    callback_data=f"task_{task['id']}"
                )
            ])

    if not buttons:
        await query.message.reply_text(
            "🎉 You have completed all available tasks!"
        )
        return

    await query.message.reply_text(
        "🎯 Available Tasks:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# =========================
# TASK DETAILS
# =========================

async def task_details(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])

    task = next(
        (x for x in TASKS if x["id"] == task_id),
        None
    )

    if not task:
        await query.message.reply_text("❌ Task not found.")
        return

    keyboard = [
        [InlineKeyboardButton(
            "🔗 Open Task",
            url=task["url"]
        )],
        [InlineKeyboardButton(
            "📤 Submit Proof",
            callback_data=f"submit_{task_id}"
        )]
    ]

    context.user_data["current_task"] = task_id

    await query.message.reply_text(
        f"🎯 {task['title']}\n\n"
        f"💰 Reward: {task['reward']} TK\n\n"
        "1️⃣ Open the task link.\n"
        "2️⃣ Complete the task.\n"
        "3️⃣ Take a screenshot.\n"
        "4️⃣ Click Submit Proof.\n\n"
        "⚠️ The same task cannot be submitted twice.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# SUBMIT PROOF
# =========================

async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split("_")[1])

    cur.execute("""
    SELECT id FROM submissions
    WHERE telegram_id=? AND task_id=?
    """, (query.from_user.id, task_id))

    if cur.fetchone():
        await query.message.reply_text(
            "⚠️ You have already submitted this task."
        )
        return

    context.user_data["submit_task"] = task_id
    context.user_data["waiting_email"] = True

    await query.message.reply_text(
        "📧 Please send the email you used for the task:"
    )


# =========================
# TEXT HANDLER
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    if context.user_data.get("waiting_email"):

        context.user_data["email"] = text
        context.user_data["waiting_email"] = False
        context.user_data["waiting_proof"] = True

        await update.message.reply_text(
            "📸 Now send your proof screenshot."
        )
        return


# =========================
# PHOTO PROOF
# =========================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_proof"):
        return

    task_id = context.user_data.get("submit_task")
    email = context.user_data.get("email", "")

    user = update.effective_user

    proof_file_id = update.message.photo[-1].file_id

    cur.execute("""
    SELECT id FROM submissions
    WHERE telegram_id=? AND task_id=?
    """, (user.id, task_id))

    if cur.fetchone():

        await update.message.reply_text(
            "⚠️ This task has already been submitted."
        )

        return

    task = next(
        (x for x in TASKS if x["id"] == task_id),
        None
    )

    cur.execute("""
    INSERT INTO submissions
    (telegram_id, task_id, email, username,
     proof_file_id, status, reward)
    VALUES (?, ?, ?, ?, ?, 'Pending', ?)
    """, (
        user.id,
        task_id,
        email,
        user.username or "",
        proof_file_id,
        task["reward"]
    ))

    db.commit()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ Proof submitted successfully!\n\n"
        "Status: ⏳ Pending\n"
        "Admin will verify your proof.\n\n"
        "If accepted, the reward will be added to your balance."
    )

    # SEND TO ADMIN

    if ADMIN_ID:

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Accept",
                    callback_data=f"accept_{cur.lastrowid}"
                ),
                InlineKeyboardButton(
                    "❌ Reject",
                    callback_data=f"reject_{cur.lastrowid}"
                )
            ]
        ]

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=proof_file_id,
            caption=(
                "📥 NEW TASK SUBMISSION\n\n"
                f"👤 Username: @{user.username or 'N/A'}\n"
                f"🆔 Telegram ID: {user.id}\n"
                f"📧 Email: {email}\n"
                f"🎯 Task ID: {task_id}\n"
                f"💰 Reward: {task['reward']} TK\n"
                "⏳ Status: Pending"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# =========================
# ADMIN ACCEPT / REJECT
# =========================

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Admin only.")
        return

    action, submission_id = query.data.split("_")
    submission_id = int(submission_id)

    cur.execute("""
    SELECT telegram_id, reward, status
    FROM submissions
    WHERE id=?
    """, (submission_id,))

    row = cur.fetchone()

    if not row:
        await query.message.reply_text("❌ Submission not found.")
        return

    user_id, reward, status = row

    if status != "Pending":
        await query.message.reply_text(
            f"⚠️ Already processed: {status}"
        )
        return

    if action == "accept":

        cur.execute("""
        UPDATE submissions
        SET status='Accepted'
        WHERE id=?
        """, (submission_id,))

        cur.execute("""
        UPDATE users
        SET balance=balance+?
        WHERE telegram_id=?
        """, (reward, user_id))

        db.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ Task Accepted!\n\n"
                f"💰 {reward} TK added to your balance."
            )
        )

        await query.message.reply_text(
            f"✅ Accepted\n💰 {reward} TK added."
        )

    else:

        cur.execute("""
        UPDATE submissions
        SET status='Rejected'
        WHERE id=?
        """, (submission_id,))

        db.commit()

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ Task Rejected.\n\n"
                "Your proof could not be verified."
            )
        )

        await query.message.reply_text(
            "❌ Submission rejected."
        )


# =========================
# MY TASKS
# =========================

async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    cur.execute("""
    SELECT task_id, status, reward
    FROM submissions
    WHERE telegram_id=?
    ORDER BY id DESC
    """, (query.from_user.id,))

    rows = cur.fetchall()

    if not rows:
        await query.message.reply_text(
            "📊 You have not submitted any tasks yet."
        )
        return

    text = "📊 Your Task History:\n\n"

    for task_id, status, reward in rows:

        text += (
            f"🎯 Task {task_id}\n"
            f"Status: {status}\n"
            f"Reward: {reward} TK\n\n"
        )

    await query.message.reply_text(text)


# =========================
# COMMANDS
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📚 Task Reward BD Help\n\n"
        "/start - Main menu\n"
        "/balance - Check balance\n"
        "/tasks - Task history\n\n"
        "🎯 Complete tasks → Submit proof → Admin verification → Earn."
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cur.execute(
        "SELECT balance FROM users WHERE telegram_id=?",
        (update.effective_user.id,)
    )

    row = cur.fetchone()

    amount = row[0] if row else 0

    await update.message.reply_text(
        f"💰 Your current balance: {amount:.2f} TK"
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🎯 Use the /start menu and select Get Task."
    )


# =========================
# BOT START
# =========================

def run_bot():

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("balance", balance_command)
    )

    application.add_handler(
        CommandHandler("tasks", tasks_command)
    )

    application.add_handler(
        CallbackQueryHandler(get_task, pattern="^get_task$")
    )

    application.add_handler(
        CallbackQueryHandler(balance, pattern="^balance$")
    )

    application.add_handler(
        CallbackQueryHandler(my_tasks, pattern="^my_tasks$")
    )

    application.add_handler(
        CallbackQueryHandler(task_details, pattern="^task_")
    )

    application.add_handler(
        CallbackQueryHandler(submit_proof, pattern="^submit_")
    )

    application.add_handler(
        CallbackQueryHandler(admin_action, pattern="^(accept|reject)_")
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    application.run_polling()


threading.Thread(
    target=run_bot,
    daemon=True
).start()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 10000))
    )
