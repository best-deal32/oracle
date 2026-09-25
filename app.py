#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔮 $ORACLE Bot — بوت مجتمع عرّاف الكريبتو (Silas Kane)
- نقاط = "شظايا العين"
- مهام مجانية → Drop على pump.fun (Solana)
- دعم لغتين: عربي + إنجليزي
- v6 — نسخة Render Webhook كاملة
"""

import os
import re
import io
import csv
import json
import html
import asyncio
import random
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import RetryAfter, Forbidden, BadRequest
from dotenv import load_dotenv

from locales import t, kb_lang

load_dotenv()

# ============================================================
# ⚙️ الإعدادات
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")
PORT = int(os.environ.get("PORT", "10000"))

# نقاط
PTS_WELCOME   = 10
PTS_DAILY     = 5
PTS_LORE      = 20
PTS_CAT       = 15
PTS_CAT_LUCKY = 50
PTS_REFERRAL  = 50
PTS_STREAK_7  = 200

# Cooldowns
DAILY_COOLDOWN_H   = 24.0
WRONG_COOLDOWN_H   = 0.25
CAT_COOLDOWN_H     = 3.0
DIG_COOLDOWN_H     = 24.0

STATE_TIMEOUT_H    = 1.0
QUIZ_TIMEOUT_MIN   = 30

REFERRAL_MIN_TASKS = 1
RATE_LIMIT_SEC     = 3
TEXT_RATE_LIMIT    = 2
LANG_RATE_LIMIT    = 1

FRAUD_REF_THRESHOLD = 5
FRAUD_WINDOW_H      = 1.0

BROADCAST_MAX_LEN        = 4000
BROADCAST_DELAY          = 0.05
BROADCAST_PROGRESS_EVERY = 100
BROADCAST_MAX_RETRIES    = 3

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# أدوات عامة
# ============================================================
def esc(s):
    return html.escape(str(s) if s is not None else "")

def utcnow():
    return datetime.now(timezone.utc)

def utcnow_iso():
    return utcnow().isoformat()

def parse_iso(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None

def hours_since(iso_str):
    d = parse_iso(iso_str)
    if not d:
        return 9999
    return (utcnow() - d).total_seconds() / 3600

SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def split_message(text: str, max_len: int = BROADCAST_MAX_LEN):
    if len(text) <= max_len:
        return [text]
    chunks = []
    remaining = text
    while len(remaining) > max_len:
        split_at = remaining.rfind("\n\n", 0, max_len)
        if split_at < max_len * 0.5:
            split_at = remaining.rfind("\n", 0, max_len)
        if split_at < max_len * 0.5:
            split_at = remaining.rfind(" ", 0, max_len)
        if split_at < max_len * 0.5:
            split_at = max_len
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


# ============================================================
# قاعدة البيانات
# ============================================================
def init_db():
    c = sqlite3.connect("oracle.db", check_same_thread=False, timeout=30, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT,
        points INTEGER DEFAULT 0,
        referrer_id INTEGER DEFAULT NULL,
        referral_verified INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        best_streak INTEGER DEFAULT 0,
        last_daily_at TEXT,
        last_dig_at TEXT,
        last_cat_at TEXT,
        last_lore_at TEXT,
        wallet_address TEXT,
        wallet_saved_at TEXT,
        highest_chapter INTEGER DEFAULT 0,
        state TEXT, temp_data TEXT,
        last_action_at TEXT,
        language TEXT DEFAULT NULL,
        last_wrong_at TEXT,
        state_set_at TEXT,
        created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS lore_chapters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_num INTEGER UNIQUE,
        title_ar TEXT, title_en TEXT,
        body_ar TEXT, body_en TEXT,
        unlock_points INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1)""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_lore (
        user_id INTEGER, chapter_id INTEGER,
        read_at TEXT,
        PRIMARY KEY (user_id, chapter_id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        q_ar TEXT, q_en TEXT,
        a_ar TEXT, a_en TEXT,
        b_ar TEXT, b_en TEXT,
        c_ar TEXT, c_en TEXT,
        correct TEXT,
        expl_ar TEXT, expl_en TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS task_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, task TEXT, points INTEGER,
        meta TEXT, created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER, referred_id INTEGER UNIQUE,
        points INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0,
        created_at TEXT, verified_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS digs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, prize INTEGER, created_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, added_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS admin_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER, action TEXT, target TEXT, details TEXT, created_at TEXT)""")

    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_users_points ON users(points DESC)",
        "CREATE INDEX IF NOT EXISTS idx_tasklog_user ON task_log(user_id, task)",
        "CREATE INDEX IF NOT EXISTS idx_refs_referrer ON referrals(referrer_id, verified)",
        "CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address)",
    ]:
        try: c.execute(sql)
        except sqlite3.OperationalError: pass

    for sql in [
        "ALTER TABLE users ADD COLUMN language TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN last_wrong_at TEXT",
        "ALTER TABLE users ADD COLUMN state_set_at TEXT",
        "ALTER TABLE lore_chapters ADD COLUMN title_en TEXT",
        "ALTER TABLE lore_chapters ADD COLUMN body_en TEXT",
    ]:
        try: c.execute(sql)
        except sqlite3.OperationalError: pass

    c.execute("INSERT OR IGNORE INTO admins (user_id, added_at) VALUES (?,?)",
              (ADMIN_ID, utcnow_iso()))
    return c

conn = init_db()


@contextmanager
def tx():
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try: conn.execute("ROLLBACK")
        except Exception: pass
        raise


# ============================================================
# بيانات أولية
# ============================================================
def seed_lore():
    if conn.execute("SELECT COUNT(*) FROM lore_chapters").fetchone()[0] > 0:
        return

    chapters = [
        (1, "الفصل الأول: الأصل", "Chapter 1: The Origin",
         """الاسم الكامل: Silas Kane
اللقب: The Crypto Oracle (عرّاف الكريبتو)
العمر: يدّعي أنه 67 عامًا.

📍 الإقامة: كوخ خشبي قديم في غابة "بلاك ريدج" بولاية أوريغون. لا كهرباء. لا إنترنت.

🎬 القصة:
• 2009 — طُرد من عمله في سياتل بسبب "سلوك غريب".
• 2010 — اشترى 10,000 بيتكوين مقابل 50 دولارًا، على قرص صلب قديم.
• 2011 — بعد الانفصال عن زوجته، رمى القرص في بحيرة. قال: "لن أحتاج شيئًا لا أفهمه."
• 2013 — قرأ أن البيتكوين وصل لـ 1000 دولار. عاد للبحيرة. لم يجد شيئًا.
• 2014 — اشترى شاشة CRT مكسورة. أطلق عليها اسم "العين".
• 2015 — اعتزل العالم في الغابة.
• 2016 — أول نبوءة: "البيتكوين سيصل 20 ألف ثم ينهار." — حدث فعلًا.

⚡ المفارقة: الأولى كانت صدفة. كل نبوءاته بعدها... خاطئة.""",
         """Full Name: Silas Kane
Title: The Crypto Oracle
Age: Claims to be 67.

📍 Residence: An old wooden cabin in Black Ridge Forest, Oregon. No electricity. No internet.

🎬 The Story:
• 2009 — Fired from his job in Seattle for "strange behavior."
• 2010 — Bought 10,000 Bitcoin for $50, stored on an old hard drive.
• 2011 — After his divorce, he threw the drive into a lake. "I won't need what I don't understand."
• 2013 — Read that Bitcoin hit $1,000. Returned to the lake. Found nothing.
• 2014 — Bought a broken CRT monitor. Named it "The Eye."
• 2015 — Withdrew from the world into the forest.
• 2016 — First prophecy: "Bitcoin will hit $20K, then crash." — It happened.

⚡ The irony: The first one was a coincidence. Every prophecy after it... wrong.""",
         0),

        (2, "الفصل الثاني: الشخصيات", "Chapter 2: The Characters",
         """🔮 سيلاس كين — البطل
جملته: "The chart doesn't lie. People do."
سرّه: يعرف أن نبوءاته خاطئة، لكنه لا يستطيع التوقف.

👩 إيلين كين — الزوجة السابقة
العقل الحقيقي. سرّها: لديها 500 بيتكوين سرية.

🧑 زاك — التلميذ
21 سنة، متحمس. جملته: "Silas! I bought! Am I rich now?"
سرّه: يعرف أن النبوءات خاطئة، لكنه يخفي ذلك.

👨‍💼 ماركوس فين — الخصم
مدير صندوق تحوط. جملته: "I don't predict. I calculate."
سرّه: نبوءاته صحيحة بشكل ممل. لكن لا أحد يحبه.

🐈‍⬛ أوراكل — القطة
قطة سوداء، عين صفراء. تظهر فقط عندما يبدأ السوق في الحركة.""",
         """🔮 Silas Kane — The Protagonist
His line: "The chart doesn't lie. People do."
His secret: He knows his prophecies are wrong. He can't stop.

👩 Eileen Kane — The Ex-Wife
The real brain. Her secret: 500 Bitcoin hidden.

🧑 Zack — The Disciple
21, over-enthusiastic. His line: "Silas! I bought! Am I rich now?"
His secret: He knows the prophecies are wrong. He hides it.

👨‍💼 Marcus Finn — The Rival
Hedge fund manager. His line: "I don't predict. I calculate."
His secret: His predictions are boringly accurate. No one likes him.

🐈‍⬛ Oracle — The Cat
Black cat, one yellow eye. Appears only when the market moves.""",
         30),

        (3, "الفصل الثالث: الخط الزمني", "Chapter 3: The Timeline",
         """📅 الأحداث الكبرى:
2009 — الطرد من سياتل
2010 — شراء 10,000 بيتكوين
2011 — رمي القرص في البحيرة
2013 — البيتكوين = 1000 دولار
2014 — "العين"
2015 — الاعتزال
2016 — النبوءة الأولى (صحيحة!)
2017 — الشهرة
2018 — "عتبة الغابة"
2019 — زاك
2020 — ماركوس
2021 — إيلين تربح 500 بيتكوين سرًا
2022 — "الشتاء"
2023 — القطة أوراكل
2024 — النبوءة الكبرى: 2025 = سنة الميم
2025 — $ORACLE — الإطلاق""",
         """📅 Key Events:
2009 — Fired from Seattle
2010 — Bought 10,000 BTC
2011 — Threw the drive into the lake
2013 — BTC = $1,000
2014 — "The Eye"
2015 — Withdrew
2016 — First prophecy (correct!)
2017 — Fame
2018 — "The Threshold"
2019 — Zack arrives
2020 — Marcus appears
2021 — Eileen secretly earns 500 BTC
2022 — "The Winter"
2023 — Oracle the cat
2024 — Great Prophecy: 2025 = year of the meme
2025 — $ORACLE launch""",
         80),

        (4, "الفصل الرابع: قواعد العالم", "Chapter 4: World Rules",
         """⚖️ القوانين السبعة:

1️⃣ قانون التنبؤ المقلوب — كلما كانت النبوءة خاطئة، زاد إيمان الأتباع.
2️⃣ قانون الغابة — لا يمكن لسيلاس مغادرة الغابة.
3️⃣ قانون العين — العين تعمل فقط عندما يكون السوق هادئًا.
4️⃣ قانون التلميذ — كل تلميذ يظن أنه "خاص".
5️⃣ قانون النبوءة الكبرى — كل 100 عام، تتحقق نبوءة واحدة.
6️⃣ قانون الحكمة — من يسأل سيلاس "متى يشتري" لم يفهم شيئًا.
7️⃣ قانون القطة — القطة أوراكل تفعل ما تريد.""",
         """⚖️ The Seven Laws:

1️⃣ Law of Inverted Prophecy — The more wrong the prophecy, the stronger the faith.
2️⃣ Law of the Forest — Silas cannot leave the forest.
3️⃣ Law of The Eye — The Eye works only when the market is calm.
4️⃣ Law of the Disciple — Every disciple thinks they're "special".
5️⃣ Law of the Great Prophecy — Once every 100 years, one prophecy comes true.
6️⃣ Law of Wisdom — Whoever asks Silas "when to buy" has understood nothing.
7️⃣ Law of the Cat — Oracle the cat does whatever she wants.""",
         150),

        (5, "الفصل الخامس: النكات الداخلية", "Chapter 5: Running Gags",
         """😂 النكات الداخلية:

1. "الشارت لا يكذب" — سيلاس يقولها، ثم يهبط السعر.
2. القرص الصلب — "هل بحثت في البحيرة؟" — "البحيرة فيها أسماك. لا يهم."
3. زاك والشراء — زاك = مؤشر عكسي.
4. ماركوس والذكاء الاصطناعي — "الآلة لا تشرب القهوة."
5. إيلين والمحفظة السرية — "إيلين تحركت في المحفظة مرة أخرى."
6. القطة أوراكل — "القطة ظهرت. اشتروا."
7. "سيلاس قال" — أي تنبؤ خاطئ يُنسب إليه.""",
         """😂 Running Gags:

1. "The chart doesn't lie" — Silas says it. Price drops.
2. The hard drive — "Did you check the lake again?" — "The lake has fish. It doesn't matter."
3. Zack and buying — Zack = reverse indicator.
4. Marcus and AI — "Machines don't drink coffee."
5. Eileen and the secret wallet — "Eileen moved in the wallet again."
6. Oracle the cat — "The cat appeared. Buy."
7. "Silas said" — Every wrong prediction is attributed to him.""",
         250),

        (6, "الفصل السادس: الأقواس القصصية", "Chapter 6: Story Arcs",
         """🎭 القوس الأول: "البحيرة"
سيلاس يعود للبحيرة. لم يجد شيئًا. لكنه قال: "البحيرة أعطتني سلامًا."
📖 الدرس: لا تتمسك بالماضي.

🎭 القوس الثاني: "إيلين تزور"
إيلين تركت مظروفًا: "البيتكوين عندي. لكنك لن تعرف أبدًا."
📖 الدرس: الحقيقة غالبًا أمامنا.

🎭 القوس الثالث: "ماركوس يتحدى"
ماركوس يفوز بالأرقام. سيلاس يفوز بالقلوب.
📖 الدرس: العقل والقلب يمكن أن يتعايشا.

🎭 القوس الرابع: "النبوءة الكبرى"
النبوءة = "سأطلق عملة." — $ORACLE.
📖 الدرس: النبوءة الوحيدة الصادقة هي التي تصنعها بنفسك.""",
         """🎭 Arc 1: "The Lake"
Silas returns to the lake. Finds nothing. Says: "The lake gave me peace."
📖 Lesson: Don't cling to the past.

🎭 Arc 2: "Eileen visits"
She leaves an envelope: "I have the Bitcoin. You'll never know."
📖 Lesson: The truth is often right in front of us.

🎭 Arc 3: "Marcus challenges"
Marcus wins by numbers. Silas wins by hearts.
📖 Lesson: Mind and heart can coexist.

🎭 Arc 4: "The Great Prophecy"
The prophecy: "I will launch a coin." — $ORACLE.
📖 Lesson: The only true prophecy is the one you build yourself.""",
         400),

        (7, "الفصل السابع: القنوات والمنصات", "Chapter 7: Channels & Platforms",
         """📱 المحتوى:

1. تغريدات القصة — 3-4 أسبوعيًا.
2. ميمات بصرية — بيكسل آرت لسيلاس، زاك، القطة.
3. حكمة سيلاس — اقتباسات فلسفية.
4. تفاعل المجتمع — "اسأل سيلاس"، "نبوءتك"، "صحح سيلاس".
5. AMA الشهرية على X.
6. ألعاب البوت — القطة أوراكل، نبوءة اليوم، مبارزة الأنبياء.""",
         """📱 Content:

1. Story tweets — 3-4 per week.
2. Visual memes — pixel art of Silas, Zack, the cat.
3. Wisdom of Silas — philosophical quotes.
4. Community engagement — "Ask Silas", "Your prophecy", "Correct Silas".
5. Monthly AMA on X.
6. Bot games — Oracle cat, daily prophecy, prophets' duel.""",
         600),

        (8, "الفصل الثامن: الهوية البصرية", "Chapter 8: Visual Identity",
         """🎨 الشعار
خلفية: دائرة رمادية داكنة.
المركز: رأس سيلاس (بيكسل آرت).
الأسفل: القطة أوراكل نائمة.
النص: ORACLE / $ORACLE.

🎨 الألوان:
• رمادي داكن — #2C2C2C
• رمادي متوسط — #4A4A4A
• أزرق باهت — #7BA7BC
• أبيض عاجي — #F5F5DC
• أخضر نيون — #00FF88
• أحمر خافت — #8B0000""",
         """🎨 Logo
Background: Dark gray circle.
Center: Silas's head (pixel art).
Bottom: Oracle cat sleeping.
Text: ORACLE / $ORACLE.

🎨 Colors:
• Dark gray — #2C2C2C
• Mid gray — #4A4A4A
• Faded blue — #7BA7BC
• Ivory white — #F5F5DC
• Neon green — #00FF88
• Faded red — #8B0000""",
         900),

        (9, "الفصل التاسع: التغريدات الجاهزة", "Chapter 9: Ready Tweets",
         """📝 مجموعة من أفضل التغريدات:

🔮 "The future is not something you wait for. The future is something you build." — Silas

💰 إيلين: "هذا للطوارئ." سيلاس: "أي طوارئ؟" إيلين: "أنت."

🐈‍⬛ القطة أوراكل ظهرت اليوم. عندما تظهر، يتحرك السوق.

⚔️ ماركوس: "من يتنبأ بشكل صحيح يفوز." سيلاس: "أنا لا أتنبأ. أنا أروي القصص."

🚀 "2025 هي سنة الميم." — سيلاس. لا أحد يعرف ما يعني. لكن الجميع متحمس.""",
         """📝 Best tweets:

🔮 "The future is not something you wait for. The future is something you build." — Silas

💰 Eileen: "This is for emergencies." Silas: "What emergencies?" Eileen: "You."

🐈‍⬛ Oracle the cat appeared today. When she appears, the market moves.

⚔️ Marcus: "Whoever predicts correctly wins." Silas: "I don't predict. I tell stories."

🚀 "2025 is the year of the meme." — Silas. No one knows what it means. But everyone's excited.""",
         1300),
    ]

    with tx():
        for order_num, title_ar, title_en, body_ar, body_en, pts in chapters:
            conn.execute(
                "INSERT INTO lore_chapters (order_num, title_ar, title_en, body_ar, body_en, unlock_points) "
                "VALUES (?,?,?,?,?,?)",
                (order_num, title_ar, title_en, body_ar, body_en, pts))


def seed_quiz():
    if conn.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0] > 0:
        return

    qs = [
        ("ماذا فعل سيلاس بالقرص الصلب؟", "What did Silas do with the hard drive?",
         "باعه", "Sold it", "رماه في بحيرة", "Threw it in a lake", "أحرقه", "Burned it", "b",
         "رمى القرص في بحيرة بعد الانفصال.", "He threw it into a lake after the divorce."),

        ("ما اسم القطة؟", "What's the cat's name?",
         "Luna", "Luna", "Oracle", "Oracle", "Shadow", "Shadow", "b",
         "سُميت أوراكل لأنها تظهر عندما يتحرك السوق.", "Named Oracle because she appears when the market moves."),

        ("كم بيتكوين اشترى سيلاس؟", "How much BTC did Silas buy?",
         "1,000", "1,000", "10,000", "10,000", "100,000", "100,000", "b",
         "10,000 بيتكوين مقابل 50 دولارًا.", "10,000 BTC for $50."),

        ("ما لقب سيلاس؟", "What's Silas's title?",
         "The Trader", "The Trader", "The Crypto Oracle", "The Crypto Oracle", "The Whale", "The Whale", "b",
         "يُعرف بـ The Crypto Oracle.", "Known as The Crypto Oracle."),

        ("من هو التلميذ؟", "Who is the disciple?",
         "Marcus", "Marcus", "Zack", "Zack", "Eileen", "Eileen", "b",
         "زاك، 21 سنة، مؤشر عكسي.", "Zack, 21, a reverse indicator."),

        ("ماذا تمثل إيلين؟", "What does Eileen represent?",
         "الحب", "Love", "الواقع", "Reality", "المال", "Money", "b",
         "إيلين تمثل الواقع.", "Eileen represents reality."),

        ("ما هو سر إيلين؟", "What is Eileen's secret?",
         "كتاب", "A book", "500 بيتكوين سرية", "500 hidden BTC", "كوخ", "A cabin", "b",
         "لديها 500 بيتكوين سرية.", "She has 500 hidden Bitcoin."),

        ("متى ظهرت القطة أوراكل؟", "When did Oracle cat first appear?",
         "2020", "2020", "2023", "2023", "2025", "2025", "b",
         "ظهرت أول مرة في 2023.", "First appeared in 2023."),
    ]

    with tx():
        for row in qs:
            conn.execute(
                "INSERT INTO quiz_questions "
                "(q_ar, q_en, a_ar, a_en, b_ar, b_en, c_ar, c_en, correct, expl_ar, expl_en) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)", row)


seed_lore()
seed_quiz()


# ============================================================
# المستخدمون
# ============================================================
def get_user(uid):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()


ALLOWED_COLS = {
    "points", "referrer_id", "referral_verified", "streak",
    "best_streak", "last_daily_at", "last_dig_at", "last_cat_at",
    "last_lore_at", "wallet_address", "wallet_saved_at",
    "highest_chapter", "state", "temp_data", "last_action_at",
    "language", "first_name", "username", "last_wrong_at", "state_set_at",
}


def get_col(uid, col):
    if col not in ALLOWED_COLS:
        raise ValueError(f"Invalid column: {col}")
    r = conn.execute(f"SELECT {col} FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r else None


def ensure_user(uid, username, first_name):
    with tx():
        exists = conn.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone()
        if exists:
            return
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, points, created_at) "
            "VALUES (?,?,?,?,?)",
            (uid, username or "", first_name or "", PTS_WELCOME, utcnow_iso()))
        conn.execute(
            "INSERT INTO task_log (user_id, task, points, meta, created_at) VALUES (?,?,?,?,?)",
            (uid, "welcome_bonus", PTS_WELCOME, "", utcnow_iso()))


def add_points(uid, amount, task, meta=""):
    if amount == 0:
        return
    with tx():
        conn.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amount, uid))
        conn.execute(
            "INSERT INTO task_log (user_id, task, points, meta, created_at) VALUES (?,?,?,?,?)",
            (uid, task, amount, str(meta)[:200], utcnow_iso()))


def get_points(uid):
    r = conn.execute("SELECT points FROM users WHERE user_id=?", (uid,)).fetchone()
    return r[0] if r else 0


def get_total_points_issued():
    return conn.execute("SELECT COALESCE(SUM(points),0) FROM users").fetchone()[0] or 0


def get_total_chapters():
    r = conn.execute("SELECT COUNT(*) FROM lore_chapters WHERE is_active=1").fetchone()
    return r[0] if r else 0


# ============================================================
# اللغة
# ============================================================
def get_lang(uid, ctx=None) -> str:
    if ctx is not None:
        l = ctx.user_data.get("language")
        if l:
            return l
    l = get_col(uid, "language")
    return l or "ar"


def set_lang(uid, lang, ctx=None):
    if ctx is not None:
        ctx.user_data["language"] = lang
    conn.execute("UPDATE users SET language=? WHERE user_id=?", (lang, uid))


# ============================================================
# Rate limit
# ============================================================
def rl(uid, sec=RATE_LIMIT_SEC):
    row = conn.execute("SELECT last_action_at FROM users WHERE user_id=?", (uid,)).fetchone()
    now = utcnow()
    if row and row[0]:
        last = parse_iso(row[0])
        if last and (now - last).total_seconds() < sec:
            return True
    conn.execute("UPDATE users SET last_action_at=? WHERE user_id=?", (now.isoformat(), uid))
    return False


# ============================================================
# الحالة
# ============================================================
def set_state(uid, state, data=None, ctx=None):
    now = utcnow_iso()
    if ctx is not None:
        ctx.user_data["state"] = state
        ctx.user_data["temp"] = data
        ctx.user_data["state_set_at"] = now
    conn.execute(
        "UPDATE users SET state=?, temp_data=?, state_set_at=? WHERE user_id=?",
        (state, data, now, uid))


def get_state(uid, ctx=None):
    if ctx is not None:
        s = ctx.user_data.get("state")
        if s:
            ts = ctx.user_data.get("state_set_at")
            if ts and hours_since(ts) > STATE_TIMEOUT_H:
                clear_state(uid, ctx)
                return (None, None)
            return (s, ctx.user_data.get("temp"))
    r = conn.execute(
        "SELECT state, temp_data, state_set_at FROM users WHERE user_id=?",
        (uid,)).fetchone()
    if not r:
        return (None, None)
    s, data, ts = r
    if s and ts and hours_since(ts) > STATE_TIMEOUT_H:
        clear_state(uid, ctx)
        return (None, None)
    return (s, data)


def clear_state(uid, ctx=None):
    if ctx is not None:
        ctx.user_data.pop("state", None)
        ctx.user_data.pop("temp", None)
        ctx.user_data.pop("state_set_at", None)
    conn.execute(
        "UPDATE users SET state=NULL, temp_data=NULL, state_set_at=NULL WHERE user_id=?",
        (uid,))


# ============================================================
# مشرفون
# ============================================================
def is_admin(uid):
    return uid == ADMIN_ID or conn.execute(
        "SELECT 1 FROM admins WHERE user_id=?", (uid,)).fetchone() is not None


def get_all_admins():
    ids = {r[0] for r in conn.execute("SELECT user_id FROM admins").fetchall()}
    ids.add(ADMIN_ID)
    return list(ids)


async def send_to_admins(context, text):
    for admin_id in get_all_admins():
        try:
            await context.bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception:
            pass


def log_admin(aid, action, target="", details=""):
    try:
        conn.execute(
            "INSERT INTO admin_log (admin_id, action, target, details, created_at) VALUES (?,?,?,?,?)",
            (aid, action, str(target), str(details)[:500], utcnow_iso()))
    except Exception: pass


def detect_referral_fraud(referrer_id) -> bool:
    cutoff = (utcnow() - timedelta(hours=FRAUD_WINDOW_H)).isoformat()
    recent = conn.execute(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id=? AND verified=1 AND verified_at >= ?",
        (referrer_id, cutoff)).fetchone()[0]
    return recent >= FRAUD_REF_THRESHOLD


# ============================================================
# لوحات
# ============================================================
def main_menu(lang="ar"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "btn_lore"), callback_data="lore"),
         InlineKeyboardButton(t(lang, "btn_daily"), callback_data="daily")],
        [InlineKeyboardButton(t(lang, "btn_cat"), callback_data="cat"),
         InlineKeyboardButton(t(lang, "btn_dig"), callback_data="dig")],
        [InlineKeyboardButton(t(lang, "btn_top"), callback_data="top"),
         InlineKeyboardButton(t(lang, "btn_invite"), callback_data="invite")],
        [InlineKeyboardButton(t(lang, "btn_me"), callback_data="me"),
         InlineKeyboardButton(t(lang, "btn_wallet"), callback_data="wallet")],
    ])


def back_menu(lang="ar"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu")]])


# ============================================================
# /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ensure_user(u.id, u.username, u.first_name)

    old_state, _ = get_state(u.id, context)
    clear_state(u.id, context)

    if context.args and context.args[0].startswith("ref_"):
        try:
            ref_id = int(context.args[0][4:])
        except ValueError:
            ref_id = None
        if ref_id and ref_id != u.id and not get_col(u.id, "referrer_id") and get_user(ref_id):
            conn.execute("UPDATE users SET referrer_id=? WHERE user_id=?", (ref_id, u.id))
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO referrals (referrer_id, referred_id, created_at) VALUES (?,?,?)",
                    (ref_id, u.id, utcnow_iso()))
                ref_lang = get_lang(ref_id)
                await context.bot.send_message(
                    chat_id=ref_id,
                    text=t(ref_lang, "invite_new_join", pts=PTS_REFERRAL),
                    parse_mode="HTML")
            except Exception:
                pass

    user_lang = get_col(u.id, "language")
    if not user_lang:
        await update.message.reply_text(t("ar", "choose_lang"), reply_markup=kb_lang())
        return

    if old_state in ("waiting_wallet",):
        await update.message.reply_text(t(user_lang, "state_cancelled"))

    pts = get_points(u.id)
    total = get_total_points_issued() or 1
    share = round(pts / total * 100, 3)

    await update.message.reply_text(
        t(user_lang, "welcome", name=esc(u.first_name), pts=pts, share=share),
        parse_mode="HTML", reply_markup=main_menu(user_lang))


async def set_lang_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if rl(uid, LANG_RATE_LIMIT):
        await q.answer("⏳", show_alert=False)
        return

    lang = q.data.replace("set_lang_", "")
    if lang not in ("ar", "en"):
        await q.answer()
        return

    set_lang(uid, lang, context)
    await q.answer(t(lang, "lang_set"), show_alert=False)
    pts = get_points(uid)
    total = get_total_points_issued() or 1
    share = round(pts / total * 100, 3)
    name = get_col(uid, "first_name") or ""
    await q.edit_message_text(
        t(lang, "welcome", name=esc(name), pts=pts, share=share),
        parse_mode="HTML", reply_markup=main_menu(lang))


async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t("ar", "choose_lang"), reply_markup=kb_lang())


async def menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    clear_state(q.from_user.id, context)
    lang = get_lang(q.from_user.id, context)
    pts = get_points(q.from_user.id)
    await q.edit_message_text(
        t(lang, "main_menu_title", pts=pts),
        parse_mode="HTML", reply_markup=main_menu(lang))


# ============================================================
# 📜 الفصول
# ============================================================
async def lore_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid, context)
    pts = get_points(uid)

    chapters = conn.execute(
        "SELECT id, order_num, title_ar, title_en, unlock_points FROM lore_chapters "
        "WHERE is_active=1 ORDER BY order_num").fetchall()
    read_ids = {r[0] for r in conn.execute(
        "SELECT chapter_id FROM user_lore WHERE user_id=?", (uid,)).fetchall()}

    rows = []
    for cid, order_num, t_ar, t_en, unlock_pts in chapters:
        title = t_ar if lang == "ar" else (t_en or t_ar)
        display = title[:32]
        if cid in read_ids:
            rows.append([InlineKeyboardButton(t(lang, "lore_read", title=display), callback_data=f"ch_{cid}")])
        elif pts >= unlock_pts:
            rows.append([InlineKeyboardButton(t(lang, "lore_unlocked", title=f"{display} (+{PTS_LORE})"), callback_data=f"ch_{cid}")])
        else:
            rows.append([InlineKeyboardButton(t(lang, "lore_locked", num=order_num, pts=unlock_pts), callback_data="locked")])

    rows.append([InlineKeyboardButton(t(lang, "btn_back"), callback_data="menu")])
    await q.edit_message_text(
        t(lang, "lore_header", pts=pts, lore_pts=PTS_LORE),
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


async def chapter_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    lang = get_lang(uid, context)
    cid = int(q.data.split("_")[1])
    row = conn.execute(
        "SELECT order_num, title_ar, title_en, body_ar, body_en, unlock_points "
        "FROM lore_chapters WHERE id=?", (cid,)).fetchone()
    if not row:
        await q.answer("Not found" if lang == "en" else "غير موجود", show_alert=True); return

    order_num, t_ar, t_en, b_ar, b_en, unlock = row
    title = t_ar if lang == "ar" else (t_en or t_ar)
    body = b_ar if lang == "ar" else (b_en or b_ar)
    pts = get_points(uid)
    if pts < unlock:
        await q.answer(t(lang, "lore_not_enough", pts=unlock), show_alert=True); return

    already = conn.execute("SELECT 1 FROM user_lore WHERE user_id=? AND chapter_id=?",
                          (uid, cid)).fetchone()
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton(t(lang, "btn_back_chapters"), callback_data="lore")]])

    if already:
        await q.answer()
        await q.edit_message_text(f"<b>{esc(title)}</b>\n\n{esc(body)}",
            parse_mode="HTML", reply_markup=back_btn)
        return

    await q.answer(t(lang, "lore_earned", pts=PTS_LORE))
    with tx():
        conn.execute("INSERT OR IGNORE INTO user_lore (user_id, chapter_id, read_at) VALUES (?,?,?)",
                     (uid, cid, utcnow_iso()))
        conn.execute(
            "UPDATE users SET points = points + ?, highest_chapter = MAX(highest_chapter, ?) WHERE user_id=?",
            (PTS_LORE, order_num, uid))
        conn.execute(
            "INSERT INTO task_log (user_id, task, points, meta, created_at) VALUES (?,?,?,?,?)",
            (uid, "lore_read", PTS_LORE, f"chapter={order_num}", utcnow_iso()))

    await q.edit_message_text(
        f"<b>{esc(title)}</b>\n\n{esc(body)}\n\n{t(lang, 'lore_earned', pts=PTS_LORE)}",
        parse_mode="HTML", reply_markup=back_btn)


async def locked_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    lang = get_lang(q.from_user.id, context)
    await q.answer(t(lang, "lore_locked_alert"), show_alert=True)


# ============================================================
# 🎯 المهمة اليومية
# ============================================================
async def daily_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid, context)

    last_correct = get_col(uid, "last_daily_at")
    if hours_since(last_correct) < DAILY_COOLDOWN_H:
        remaining = DAILY_COOLDOWN_H - hours_since(last_correct)
        await q.edit_message_text(
            t(lang, "daily_cooldown", h=f"{remaining:.1f}"),
            parse_mode="HTML", reply_markup=back_menu(lang))
        return

    last_wrong = get_col(uid, "last_wrong_at")
    if hours_since(last_wrong) < WRONG_COOLDOWN_H:
        remaining_min = (WRONG_COOLDOWN_H - hours_since(last_wrong)) * 60
        await q.edit_message_text(
            t(lang, "daily_wrong_cooldown", m=f"{remaining_min:.0f}"),
            parse_mode="HTML", reply_markup=back_menu(lang))
        return

    row = conn.execute(
        "SELECT id, q_ar, q_en, a_ar, a_en, b_ar, b_en, c_ar, c_en, correct "
        "FROM quiz_questions ORDER BY RANDOM() LIMIT 1").fetchone()
    if not row:
        await q.edit_message_text(t(lang, "daily_no_questions"), reply_markup=back_menu(lang)); return

    qid, q_ar, q_en, a_ar, a_en, b_ar, b_en, c_ar, c_en, correct = row
    question = q_ar if lang == "ar" else q_en
    opt_a = a_ar if lang == "ar" else a_en
    opt_b = b_ar if lang == "ar" else b_en
    opt_c = c_ar if lang == "ar" else c_en

    set_state(uid, "quiz", json.dumps({
        "qid": qid, "correct": correct, "ts": utcnow_iso()
    }), context)

    await q.edit_message_text(
        t(lang, "daily_header", q=esc(question), pts=PTS_DAILY),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"A) {opt_a[:40]}", callback_data="ans_a")],
            [InlineKeyboardButton(f"B) {opt_b[:40]}", callback_data="ans_b")],
            [InlineKeyboardButton(f"C) {opt_c[:40]}", callback_data="ans_c")],
        ]))


async def answer_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    lang = get_lang(uid, context)
    state, temp = get_state(uid, context)

    if state != "quiz":
        await q.answer(t(lang, "daily_no_state"), show_alert=True); return

    await q.answer()

    data = json.loads(temp) if temp else {}

    started = parse_iso(data.get("ts"))
    if not started:
        clear_state(uid, context)
        await q.edit_message_text(
            "⏰ Session expired." if lang == "en" else "⏰ انتهت الصلاحية.",
            reply_markup=back_menu(lang))
        return

    elapsed_min = (utcnow() - started).total_seconds() / 60
    if elapsed_min > QUIZ_TIMEOUT_MIN:
        clear_state(uid, context)
        msg = ("⏰ <b>انتهت صلاحية السؤال.</b>\n\nاضغط على المهمة اليومية مرة أخرى."
               if lang == "ar" else
               "⏰ <b>Question expired.</b>\n\nTap Daily Task again.")
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=back_menu(lang))
        return

    correct = data.get("correct")
    qid = data.get("qid")
    choice = q.data.split("_")[1]

    if choice == correct:
        last = get_col(uid, "last_daily_at")
        h = hours_since(last)
        cur_streak = get_col(uid, "streak") or 0
        new_streak = cur_streak + 1 if h < 48 else 1
        pts_earned = PTS_DAILY
        streak_bonus = PTS_STREAK_7 if new_streak > 0 and new_streak % 7 == 0 else 0
        total_gain = pts_earned + streak_bonus

        with tx():
            conn.execute(
                "UPDATE users SET last_daily_at=?, last_wrong_at=NULL, "
                "streak=?, best_streak=MAX(best_streak, ?) WHERE user_id=?",
                (utcnow_iso(), new_streak, new_streak, uid))
            conn.execute("UPDATE users SET points = points + ? WHERE user_id=?",
                         (total_gain, uid))
            conn.execute(
                "INSERT INTO task_log (user_id, task, points, meta, created_at) VALUES (?,?,?,?,?)",
                (uid, "daily", total_gain, f"streak={new_streak}", utcnow_iso()))

        clear_state(uid, context)
        await _verify_referral(uid, context)

        msg = t(lang, "daily_correct", pts=pts_earned)
        if streak_bonus:
            msg += t(lang, "daily_streak_bonus", streak=new_streak, pts=streak_bonus)
        msg += t(lang, "daily_streak_line", streak=new_streak)
        await q.edit_message_text(msg, parse_mode="HTML", reply_markup=back_menu(lang))
        return

    with tx():
        conn.execute("UPDATE users SET last_wrong_at=? WHERE user_id=?",
                     (utcnow_iso(), uid))

    row = conn.execute(
        "SELECT expl_ar, expl_en FROM quiz_questions WHERE id=?", (qid,)).fetchone()
    expl = (row[0] if lang == "ar" else row[1]) if row else ""

    clear_state(uid, context)
    await q.edit_message_text(
        t(lang, "daily_wrong", correct=correct.upper(), expl=esc(expl or "")),
        parse_mode="HTML", reply_markup=back_menu(lang))


# ============================================================
# 🌊 البحيرة
# ============================================================
async def dig_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    lang = get_lang(uid, context)
    last = get_col(uid, "last_dig_at")
    if hours_since(last) < DIG_COOLDOWN_H:
        rem = DIG_COOLDOWN_H - hours_since(last)
        await q.answer(t(lang, "dig_cooldown", h=f"{rem:.1f}"), show_alert=True); return

    r = random.random()
    if r < 0.05:
        prize = random.randint(50, 100); label = t(lang, "dig_lucky")
    elif r < 0.30:
        prize = random.randint(15, 40); label = t(lang, "dig_medium")
    else:
        prize = random.randint(2, 10); label = t(lang, "dig_small")

    with tx():
        conn.execute("UPDATE users SET last_dig_at=?, points = points + ? WHERE user_id=?",
                     (utcnow_iso(), prize, uid))
        conn.execute("INSERT INTO digs (user_id, prize, created_at) VALUES (?,?,?)",
                     (uid, prize, utcnow_iso()))
        conn.execute(
            "INSERT INTO task_log (user_id, task, points, meta, created_at) VALUES (?,?,?,?,?)",
            (uid, "dig", prize, "", utcnow_iso()))

    await q.answer(f"+{prize}")
    await q.edit_message_text(
        t(lang, "dig_result", label=label, pts=prize),
        parse_mode="HTML", reply_markup=back_menu(lang))


# ============================================================
# 🐈‍⬛ القطة
# ============================================================
async def cat_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    lang = get_lang(uid, context)
    last = get_col(uid, "last_cat_at")
    if hours_since(last) < CAT_COOLDOWN_H:
        rem = CAT_COOLDOWN_H - hours_since(last)
        await q.answer(t(lang, "cat_cooldown", h=f"{rem:.1f}"), show_alert=True); return

    r = random.random()
    if r < 0.15:
        prize = PTS_CAT_LUCKY; msg = t(lang, "cat_lucky")
    elif r < 0.55:
        prize = PTS_CAT; msg = t(lang, "cat_normal")
    else:
        prize = 2; msg = t(lang, "cat_empty")

    with tx():
        conn.execute("UPDATE users SET last_cat_at=?, points = points + ? WHERE user_id=?",
                     (utcnow_iso(), prize, uid))
        conn.execute(
            "INSERT INTO task_log (user_id, task, points, meta, created_at) VALUES (?,?,?,?,?)",
            (uid, "cat", prize, "", utcnow_iso()))

    await q.answer(f"+{prize}")
    await q.edit_message_text(
        t(lang, "cat_result", msg=msg, pts=prize),
        parse_mode="HTML", reply_markup=back_menu(lang))


# ============================================================
# 🏆 المتصدرون
# ============================================================
async def top_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid, context)
    rows = conn.execute(
        "SELECT first_name, username, points FROM users ORDER BY points DESC LIMIT 20").fetchall()
    if not rows:
        await q.edit_message_text(t(lang, "top_empty"), reply_markup=back_menu(lang)); return

    my_rank = conn.execute(
        "SELECT COUNT(*) + 1 FROM users WHERE points > (SELECT points FROM users WHERE user_id=?)",
        (uid,)).fetchone()[0]
    my_pts = get_points(uid)

    text = t(lang, "top_header")
    medals = ["🥇", "🥈", "🥉"]
    for i, (fn, un, pts) in enumerate(rows):
        icon = medals[i] if i < 3 else f"{i+1}."
        name = esc(fn or un or "?")
        text += f"{icon} {name} — <code>{pts}</code> 💠\n"
    text += t(lang, "top_my_rank", rank=my_rank, pts=my_pts)
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=back_menu(lang))


# ============================================================
# 👥 الدعوة
# ============================================================
async def invite_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid, context)
    try:
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start=ref_{uid}"
    except Exception:
        link = "N/A"

    total = conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,)).fetchone()[0]
    verified = conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=? AND verified=1", (uid,)).fetchone()[0]
    earned = conn.execute(
        "SELECT COALESCE(SUM(points),0) FROM referrals WHERE referrer_id=?",
        (uid,)).fetchone()[0]

    await q.edit_message_text(
        t(lang, "invite_header",
          link=esc(link), total=total, verified=verified, earned=earned, ref_pts=PTS_REFERRAL),
        parse_mode="HTML", reply_markup=back_menu(lang))


async def _verify_referral(uid, context):
    row = conn.execute("SELECT referrer_id FROM users WHERE user_id=?", (uid,)).fetchone()
    if not row or not row[0]:
        return
    ref_id = row[0]
    ref_row = conn.execute("SELECT id, verified FROM referrals WHERE referred_id=?", (uid,)).fetchone()
    if not ref_row or ref_row[1]:
        return

    real_tasks = conn.execute(
        "SELECT COUNT(*) FROM task_log WHERE user_id=? "
        "AND task NOT IN ('welcome_bonus','referral')",
        (uid,)).fetchone()[0]
    if real_tasks < REFERRAL_MIN_TASKS:
        return

    with tx():
        conn.execute(
            "UPDATE referrals SET verified=1, points=?, verified_at=? WHERE referred_id=?",
            (PTS_REFERRAL, utcnow_iso(), uid))
        conn.execute("UPDATE users SET points = points + ? WHERE user_id=?",
                     (PTS_REFERRAL, ref_id))
        conn.execute(
            "INSERT INTO task_log (user_id, task, points, meta, created_at) VALUES (?,?,?,?,?)",
            (ref_id, "referral", PTS_REFERRAL, f"referred={uid}", utcnow_iso()))

    if detect_referral_fraud(ref_id):
        await send_to_admins(context, (
            f"⚠️ <b>نمط إحالة مشبوه</b>\n\n"
            f"👤 المُحيل: <code>{ref_id}</code>\n"
            f"أكمل <b>{FRAUD_REF_THRESHOLD}+</b> مدعوين في أقل من ساعة.\n"
            f"راجع: <code>/user_referrals {ref_id}</code>"))

    ref_lang = get_lang(ref_id)
    try:
        await context.bot.send_message(
            chat_id=ref_id,
            text=t(ref_lang, "invite_reward", pts=PTS_REFERRAL),
            parse_mode="HTML")
    except Exception:
        pass


# ============================================================
# 💼 حسابي
# ============================================================
async def me_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid, context)
    row = get_user(uid)
    if not row:
        await q.edit_message_text(t(lang, "me_no_account"), reply_markup=back_menu(lang)); return

    pts = row[3]
    streak = row[6] or 0
    best = row[7] or 0
    refs_total = conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,)).fetchone()[0]
    refs_verified = conn.execute(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id=? AND verified=1", (uid,)).fetchone()[0]
    chapters_read = conn.execute("SELECT COUNT(*) FROM user_lore WHERE user_id=?", (uid,)).fetchone()[0]
    total_chapters = get_total_chapters() or 1
    total = get_total_points_issued() or 1
    share = round(pts / total * 100, 4)

    wallet = row[12]
    wallet_display = (f"<code>{esc(wallet[:6] + '...' + wallet[-4:])}</code>"
                      if wallet else t(lang, "me_wallet_unset"))

    await q.edit_message_text(
        t(lang, "me_header",
          uid=uid, pts=pts, share=share, streak=streak, best=best,
          chapters=chapters_read, total_chapters=total_chapters,
          verified=refs_verified, total=refs_total,
          wallet=wallet_display),
        parse_mode="HTML", reply_markup=back_menu(lang))


# ============================================================
# 💎 تسجيل المحفظة
# ============================================================
async def wallet_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = get_lang(uid, context)
    existing = get_col(uid, "wallet_address")
    if existing:
        await q.edit_message_text(
            t(lang, "wallet_exists", wallet=esc(existing)),
            parse_mode="HTML", reply_markup=back_menu(lang))
        return

    set_state(uid, "waiting_wallet", None, context)
    await q.edit_message_text(
        t(lang, "wallet_prompt"),
        parse_mode="HTML", reply_markup=back_menu(lang))


# ============================================================
# معالج النصوص
# ============================================================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid, context)
    state, _ = get_state(uid, context)

    if rl(uid, TEXT_RATE_LIMIT):
        if state:
            try:
                await update.message.reply_text(t(lang, "rate_limited"))
            except Exception:
                pass
        return

    text = update.message.text.strip()

    if state == "waiting_wallet":
        if not SOLANA_RE.match(text):
            await update.message.reply_text(
                t(lang, "wallet_invalid"), parse_mode="HTML")
            return

        dup = conn.execute(
            "SELECT user_id FROM users WHERE wallet_address=? AND user_id!=?",
            (text, uid)).fetchone()
        if dup:
            await update.message.reply_text(
                t(lang, "wallet_dup"), parse_mode="HTML")
            return

        with tx():
            conn.execute(
                "UPDATE users SET wallet_address=?, wallet_saved_at=? WHERE user_id=?",
                (text, utcnow_iso(), uid))
        clear_state(uid, context)
        await update.message.reply_text(
            t(lang, "wallet_saved", wallet=esc(text)),
            parse_mode="HTML", reply_markup=main_menu(lang))
        return

    await update.message.reply_text(t(lang, "use_menu"), reply_markup=main_menu(lang))


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = get_lang(uid, context)
    clear_state(uid, context)
    await update.message.reply_text(t(lang, "cancelled"), reply_markup=main_menu(lang))


# ============================================================
# 🛠️ أوامر الأدمن
# ============================================================
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_pts = get_total_points_issued()
    wallets = conn.execute("SELECT COUNT(*) FROM users WHERE wallet_address IS NOT NULL").fetchone()[0]
    total_refs = conn.execute("SELECT COUNT(*) FROM referrals WHERE verified=1").fetchone()[0]
    chapters_read = conn.execute("SELECT COUNT(*) FROM user_lore").fetchone()[0]
    top5 = conn.execute("SELECT first_name, points FROM users ORDER BY points DESC LIMIT 5").fetchall()

    text = (f"📊 <b>إحصائيات $ORACLE / Stats</b>\n\n"
            f"👥 Users: <code>{total_users}</code>\n"
            f"💠 Shards: <code>{total_pts}</code>\n"
            f"💎 Wallets: <code>{wallets}</code>\n"
            f"👥 Ref: <code>{total_refs}</code>\n"
            f"📖 Chapters read: <code>{chapters_read}</code>\n\n"
            f"🏆 <b>Top 5:</b>\n")
    for i, (fn, pts) in enumerate(top5, 1):
        text += f"{i}. {esc(fn or '?')} — <code>{pts}</code>\n"
    await update.message.reply_text(text, parse_mode="HTML")


async def credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /credit USER_ID AMOUNT"); return
    try:
        uid = int(context.args[0]); amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid numbers."); return
    if not get_user(uid):
        await update.message.reply_text("❌ User not found."); return
    add_points(uid, amount, "admin_credit", f"by={update.effective_user.id}")
    log_admin(update.effective_user.id, "credit", uid, amount)
    await update.message.reply_text(f"✅ +{amount} → <code>{uid}</code>", parse_mode="HTML")


async def _send_broadcast_to_user(context, uid, chunks):
    for chunk in chunks:
        attempt = 0
        chunk_sent = False
        while attempt < BROADCAST_MAX_RETRIES:
            try:
                await context.bot.send_message(chat_id=uid, text=chunk, parse_mode="HTML")
                chunk_sent = True
                break
            except RetryAfter as e:
                wait = (e.retry_after or 1) + 1
                logger.warning(f"RetryAfter {wait}s for user {uid}")
                await asyncio.sleep(wait)
                attempt += 1
            except Forbidden:
                return "blocked"
            except BadRequest:
                try:
                    await context.bot.send_message(chat_id=uid, text=chunk)
                    chunk_sent = True
                    break
                except Exception:
                    return False
            except Exception as e:
                logger.error(f"Broadcast error to {uid}: {e}")
                return False

        if not chunk_sent:
            return False

        await asyncio.sleep(BROADCAST_DELAY)

    return True


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast TEXT (HTML supported)"); return

    msg = " ".join(context.args)
    chunks = split_message(msg)

    uids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
    total_users = len(uids)
    if total_users == 0:
        await update.message.reply_text("No users."); return

    admin_chat = update.effective_chat.id
    status_msg = await update.message.reply_text(
        f"📤 بدء البث إلى {total_users} مستخدم...\nChunks: {len(chunks)}")

    sent = 0
    failed = 0
    blocked = 0

    for idx, uid in enumerate(uids, 1):
        result = await _send_broadcast_to_user(context, uid, chunks)
        if result is True:
            sent += 1
        elif result == "blocked":
            blocked += 1
        else:
            failed += 1

        if idx % BROADCAST_PROGRESS_EVERY == 0:
            try:
                await context.bot.edit_message_text(
                    chat_id=admin_chat,
                    message_id=status_msg.message_id,
                    text=(f"📤 تقدم: {idx}/{total_users}\n"
                          f"✅ {sent} | ❌ {failed} | 🚫 {blocked}"))
            except Exception:
                pass

    log_admin(update.effective_user.id, "broadcast", "",
              f"sent={sent} fail={failed} blocked={blocked} chunks={len(chunks)}")

    try:
        await context.bot.edit_message_text(
            chat_id=admin_chat,
            message_id=status_msg.message_id,
            text=(f"✅ <b>انتهى البث</b>\n\n"
                  f"👥 إجمالي: <code>{total_users}</code>\n"
                  f"✅ نجح: <code>{sent}</code>\n"
                  f"❌ فشل: <code>{failed}</code>\n"
                  f"🚫 حظر: <code>{blocked}</code>\n"
                  f"📦 Chunks: <code>{len(chunks)}</code>"),
            parse_mode="HTML")
    except Exception:
        await update.message.reply_text(
            f"✅ Done | Sent: {sent} | Failed: {failed} | Blocked: {blocked}")


async def export_wallets_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    rows = conn.execute(
        "SELECT user_id, first_name, points, wallet_address FROM users "
        "WHERE wallet_address IS NOT NULL ORDER BY points DESC").fetchall()
    if not rows:
        await update.message.reply_text("No wallets."); return
    total_pts = sum(r[2] for r in rows) or 1

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["user_id", "first_name", "points", "share_pct", "wallet"])
    for uid, fn, pts, w in rows:
        share = round(pts / total_pts * 100, 6)
        writer.writerow([uid, fn or "", pts, share, w])

    data = buf.getvalue().encode("utf-8")
    buf.close()

    await update.message.reply_document(
        document=io.BytesIO(data),
        filename=f"oracle_wallets_{utcnow().strftime('%Y%m%d_%H%M')}.csv",
        caption=f"💎 {len(rows)} wallets | {total_pts} total shards")


async def new_chapter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    text = " ".join(context.args) if context.args else ""
    parts = text.split("|", 4)
    if len(parts) < 4:
        await update.message.reply_text(
            "Usage: /new_chapter ORDER|TITLE_AR|POINTS|BODY_AR[|BODY_EN]"); return
    try:
        order_num = int(parts[0]); pts = int(parts[2])
    except ValueError:
        await update.message.reply_text("❌ Bad numbers."); return
    title_ar = parts[1].strip()
    body_ar = parts[3].strip()
    body_en = parts[4].strip() if len(parts) > 4 else body_ar
    with tx():
        conn.execute(
            "INSERT INTO lore_chapters (order_num, title_ar, title_en, body_ar, body_en, unlock_points) "
            "VALUES (?,?,?,?,?,?)",
            (order_num, title_ar, title_ar, body_ar, body_en, pts))
    await update.message.reply_text(f"✅ Chapter {order_num} added.")


async def list_wallets_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    count = conn.execute("SELECT COUNT(*) FROM users WHERE wallet_address IS NOT NULL").fetchone()[0]
    await update.message.reply_text(f"💎 Wallets: <code>{count}</code>", parse_mode="HTML")


async def user_referrals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /user_referrals USER_ID"); return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Bad ID."); return
    rows = conn.execute(
        "SELECT referred_id, verified, points, created_at, verified_at "
        "FROM referrals WHERE referrer_id=? ORDER BY id DESC LIMIT 50",
        (target,)).fetchall()
    if not rows:
        await update.message.reply_text(f"No referrals for <code>{target}</code>.", parse_mode="HTML"); return
    text = f"👥 <b>Referrals of <code>{target}</code>:</b>\n\n"
    for ref_id, verified, pts, created, v_at in rows:
        st = "✅" if verified else "⏳"
        text += f"{st} <code>{ref_id}</code> — {pts} pts | {esc(created[:10])}\n"
    await update.message.reply_text(text[:4000], parse_mode="HTML")


async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Only the main admin can add admins."); return
    if not context.args:
        await update.message.reply_text("Usage: /add_admin USER_ID"); return
    try:
        new_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Bad ID."); return
    conn.execute("INSERT OR IGNORE INTO admins (user_id, added_at) VALUES (?,?)",
                 (new_id, utcnow_iso()))
    log_admin(update.effective_user.id, "add_admin", new_id)
    await update.message.reply_text(f"✅ Added <code>{new_id}</code> as admin.", parse_mode="HTML")


async def remove_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Only the main admin can remove admins."); return
    if not context.args:
        await update.message.reply_text("Usage: /remove_admin USER_ID"); return
    try:
        old_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Bad ID."); return
    if old_id == ADMIN_ID:
        await update.message.reply_text("❌ Can't remove main admin."); return
    conn.execute("DELETE FROM admins WHERE user_id=?", (old_id,))
    log_admin(update.effective_user.id, "remove_admin", old_id)
    await update.message.reply_text(f"✅ Removed <code>{old_id}</code>.", parse_mode="HTML")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text(
            "🛠️ <b>Admin commands:</b>\n\n"
            "<b>Users:</b>\n"
            "/stats\n/credit USER_ID AMOUNT\n/broadcast TEXT\n"
            "/user_referrals USER_ID\n\n"
            "<b>Wallets:</b>\n"
            "/export_wallets\n/list_wallets\n\n"
            "<b>Lore:</b>\n"
            "/new_chapter ORDER|TITLE|POINTS|BODY[|BODY_EN]\n\n"
            "<b>Admins:</b>\n"
            "/add_admin USER_ID\n/remove_admin USER_ID",
            parse_mode="HTML")
    else:
        lang = get_lang(update.effective_user.id, context)
        if lang == "ar":
            await update.message.reply_text(
                "🤖 <b>الأوامر:</b>\n\n"
                "/start — القائمة الرئيسية\n"
                "/language — تغيير اللغة\n"
                "/cancel — إلغاء العملية الحالية",
                parse_mode="HTML")
        else:
            await update.message.reply_text(
                "🤖 <b>Commands:</b>\n\n"
                "/start — Main menu\n"
                "/language — Change language\n"
                "/cancel — Cancel current action",
                parse_mode="HTML")


# ============================================================
# 🌐 Web Server (Health Check + Telegram Webhook)
# ============================================================
async def health_handler(request):
    """نقطة نهاية UptimeRobot."""
    return web.Response(text="🔮 ORACLE Bot is alive", status=200)


async def root_handler(request):
    return web.Response(text="🔮 ORACLE Bot", status=200)


def build_telegram_app():
    """يبني تطبيق تلجرام مع كل المعالجات."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("language", language_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("credit", credit_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("export_wallets", export_wallets_cmd))
    app.add_handler(CommandHandler("new_chapter", new_chapter_cmd))
    app.add_handler(CommandHandler("list_wallets", list_wallets_cmd))
    app.add_handler(CommandHandler("user_referrals", user_referrals_cmd))
    app.add_handler(CommandHandler("add_admin", add_admin_cmd))
    app.add_handler(CommandHandler("remove_admin", remove_admin_cmd))

    app.add_handler(CallbackQueryHandler(set_lang_cb, pattern="^set_lang_"))
    app.add_handler(CallbackQueryHandler(menu_cb, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(lore_cb, pattern="^lore$"))
    app.add_handler(CallbackQueryHandler(chapter_cb, pattern="^ch_"))
    app.add_handler(CallbackQueryHandler(locked_cb, pattern="^locked$"))
    app.add_handler(CallbackQueryHandler(daily_cb, pattern="^daily$"))
    app.add_handler(CallbackQueryHandler(answer_cb, pattern="^ans_"))
    app.add_handler(CallbackQueryHandler(dig_cb, pattern="^dig$"))
    app.add_handler(CallbackQueryHandler(cat_cb, pattern="^cat$"))
    app.add_handler(CallbackQueryHandler(top_cb, pattern="^top$"))
    app.add_handler(CallbackQueryHandler(invite_cb, pattern="^invite$"))
    app.add_handler(CallbackQueryHandler(me_cb, pattern="^me$"))
    app.add_handler(CallbackQueryHandler(wallet_cb, pattern="^wallet$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    return app


async def webhook_handler(request):
    """يستقبل تحديثات تيليجرام."""
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        logger.exception(f"Webhook processing error: {e}")
        return web.Response(text="Error", status=500)


telegram_app = None


async def run_bot():
    global telegram_app

    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN missing")
    if ADMIN_ID <= 0:
        raise SystemExit("❌ ADMIN_ID invalid")
    if not WEBHOOK_URL:
        raise SystemExit("❌ WEBHOOK_URL missing")

    telegram_app = build_telegram_app()

    # initialize + start
    await telegram_app.initialize()
    await telegram_app.start()

    # webhook URL secret
    webhook_path = f"/webhook/{BOT_TOKEN}"
    full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"

    await telegram_app.bot.set_webhook(
        url=full_webhook_url,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )
    logger.info(f"✅ Webhook set: {full_webhook_url}")

    # web app
    web_app = web.Application()
    web_app.router.add_get("/", root_handler)
    web_app.router.add_get("/health", health_handler)
    web_app.router.add_post(webhook_path, webhook_handler)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"🔮 $ORACLE Bot v6 running on port {PORT}")
    logger.info(f"🌐 Health: {WEBHOOK_URL}/health")

    # keep alive
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        await runner.cleanup()
        await telegram_app.stop()
        await telegram_app.shutdown()


def main():
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
