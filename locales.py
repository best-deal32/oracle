# -*- coding: utf-8 -*-
"""نصوص البوت بلغتين: عربي (ar) + إنجليزي (en) — v5"""

STRINGS = {
    # ============ اللغة ============
    "choose_lang": {
        "ar": "🌐 اختر لغتك / Choose your language:",
        "en": "🌐 Choose your language / اختر لغتك:",
    },
    "lang_set": {
        "ar": "✅ تم ضبط اللغة على العربية.",
        "en": "✅ Language set to English.",
    },

    # ============ الترحيب ============
    "welcome": {
        "ar": (
            "🔮 <b>أهلاً بك في غابة سيلاس</b>\n\n"
            "👋 <b>{name}</b>\n"
            "💠 شظاياك: <code>{pts}</code>\n"
            "📊 حصتك من إجمالي الشظايا: <code>{share}%</code>\n\n"
            "🎯 اجمع \"شظايا العين\" عبر المهام المجانية.\n"
            "💎 يوم إطلاق <b>$ORACLE</b>، تُحوَّل شظاياك إلى عملة حقيقية على Solana.\n\n"
            "<i>\"The chart doesn't lie. People do.\"</i>\n\n"
            "اختر من القائمة:"
        ),
        "en": (
            "🔮 <b>Welcome to Silas's Forest</b>\n\n"
            "👋 <b>{name}</b>\n"
            "💠 Your Shards: <code>{pts}</code>\n"
            "📊 Your share: <code>{share}%</code>\n\n"
            "🎯 Collect \"Eye Shards\" through free tasks.\n"
            "💎 On <b>$ORACLE</b> launch day, your shards become real coins on Solana.\n\n"
            "<i>\"The chart doesn't lie. People do.\"</i>\n\n"
            "Choose from the menu:"
        ),
    },

    # ============ القائمة الرئيسية ============
    "btn_lore":     {"ar": "📜 الفصول",          "en": "📜 Chapters"},
    "btn_daily":    {"ar": "🎯 المهمة اليومية",   "en": "🎯 Daily Task"},
    "btn_cat":      {"ar": "🐈‍⬛ القطة أوراكل",     "en": "🐈‍⬛ Oracle Cat"},
    "btn_dig":      {"ar": "🌊 البحيرة",          "en": "🌊 The Lake"},
    "btn_top":      {"ar": "🏆 المتصدرون",        "en": "🏆 Leaderboard"},
    "btn_invite":   {"ar": "👥 دعوة",             "en": "👥 Invite"},
    "btn_me":       {"ar": "💼 حسابي",            "en": "💼 My Account"},
    "btn_wallet":   {"ar": "💎 تسجيل المحفظة",    "en": "💎 Register Wallet"},
    "btn_back":     {"ar": "🔙 القائمة",          "en": "🔙 Menu"},
    "btn_back_chapters": {"ar": "🔙 الفصول", "en": "🔙 Chapters"},

    "main_menu_title": {
        "ar": "🏠 <b>القائمة الرئيسية</b>\n\n💠 شظاياك: <code>{pts}</code>",
        "en": "🏠 <b>Main Menu</b>\n\n💠 Your Shards: <code>{pts}</code>",
    },

    # ============ الفصول ============
    "lore_header": {
        "ar": "📜 <b>فصول عرّاف الكريبتو</b>\n\n💠 شظاياك: <code>{pts}</code>\n📖 كل فصل جديد يمنحك <code>+{lore_pts} شظية</code>\n\nاختر فصلًا:",
        "en": "📜 <b>Chapters of The Crypto Oracle</b>\n\n💠 Your Shards: <code>{pts}</code>\n📖 Each new chapter gives <code>+{lore_pts} Shards</code>\n\nChoose a chapter:",
    },
    "lore_unlocked":    {"ar": "🔓 {title}", "en": "🔓 {title}"},
    "lore_read":        {"ar": "✅ {title}", "en": "✅ {title}"},
    "lore_locked":      {"ar": "🔒 فصل {num} — يحتاج {pts} شظية", "en": "🔒 Chapter {num} — needs {pts} Shards"},
    "lore_locked_alert": {"ar": "🔒 اجمع المزيد من الشظايا لفتح هذا الفصل.", "en": "🔒 Collect more Shards to unlock this chapter."},
    "lore_not_enough":  {"ar": "🔒 تحتاج {pts} شظية.", "en": "🔒 You need {pts} Shards."},
    "lore_earned":      {"ar": "💠 <b>+{pts} شظية</b>", "en": "💠 <b>+{pts} Shards</b>"},

    # ============ المهمة اليومية ============
    "daily_cooldown": {
        "ar": "⏳ عدت مبكرًا!\n\n🎯 مهمتك القادمة بعد: <code>{h} ساعة</code>",
        "en": "⏳ You came back too early!\n\n🎯 Next task in: <code>{h} hours</code>",
    },
    "daily_wrong_cooldown": {
        "ar": "⏳ إجابة خاطئة سابقًا.\n\n🎯 يمكنك المحاولة مجددًا بعد: <code>{m} دقيقة</code>",
        "en": "⏳ Previous wrong answer.\n\n🎯 You can retry in: <code>{m} minutes</code>",
    },
    "daily_header": {
        "ar": "🎯 <b>مهمة اليوم</b>\n\n{q}\n\n💠 الإجابة الصحيحة = <code>+{pts} شظية</code>",
        "en": "🎯 <b>Today's Task</b>\n\n{q}\n\n💠 Correct answer = <code>+{pts} Shards</code>",
    },
    "daily_correct": {
        "ar": "✅ <b>إجابة صحيحة!</b>\n\n💠 <b>+{pts} شظية</b>\n",
        "en": "✅ <b>Correct!</b>\n\n💠 <b>+{pts} Shards</b>\n",
    },
    "daily_streak_bonus": {
        "ar": "🔥 <b>مكافأة streak {streak}!</b> +{pts} شظية\n",
        "en": "🔥 <b>Streak {streak} bonus!</b> +{pts} Shards\n",
    },
    "daily_streak_line": {
        "ar": "\n🔥 Streak الحالي: <code>{streak}</code>",
        "en": "\n🔥 Current Streak: <code>{streak}</code>",
    },
    "daily_wrong": {
        "ar": "❌ <b>إجابة خاطئة.</b>\n\nالإجابة الصحيحة: <code>{correct})</code>\n📖 {expl}\n\n💡 المهمة لم تُحسب — حاول مجددًا بعد 15 دقيقة.",
        "en": "❌ <b>Wrong answer.</b>\n\nCorrect answer: <code>{correct})</code>\n📖 {expl}\n\n💡 Task not counted — try again in 15 minutes.",
    },
    "daily_no_state": {"ar": "انتهت المهمة.", "en": "Task expired."},
    "daily_no_questions": {"ar": "❌ لا توجد أسئلة.", "en": "❌ No questions available."},

    # ============ البحيرة ============
    "dig_cooldown": {"ar": "⏳ عد بعد {h} ساعة", "en": "⏳ Come back in {h} hours"},
    "dig_lucky":    {"ar": "💎 <b>وجدت شيئًا يلمع!</b>", "en": "💎 <b>You found something shiny!</b>"},
    "dig_medium":   {"ar": "🌊 <b>شبكة ممتلئة!</b>", "en": "🌊 <b>A full net!</b>"},
    "dig_small":    {"ar": "🐟 <b>سمكة صغيرة...</b>", "en": "🐟 <b>A small fish...</b>"},
    "dig_result": {
        "ar": "{label}\n\nالبحيرة تحتوي على أسماك. لا يهم.\n\n💠 <b>+{pts} شظية</b>\n⏳ عُد غدًا.",
        "en": "{label}\n\nThe lake has fish. It doesn't matter.\n\n💠 <b>+{pts} Shards</b>\n⏳ Come back tomorrow.",
    },

    # ============ القطة ============
    "cat_cooldown": {"ar": "⏳ القطة نائمة... عُد بعد {h} ساعة", "en": "⏳ The cat is asleep... come back in {h} hours"},
    "cat_lucky":    {"ar": "🐈‍⬛✨ <b>القطة ظهرت... وكانت تحمل كنزًا!</b>", "en": "🐈‍⬛✨ <b>The cat appeared... carrying treasure!</b>"},
    "cat_normal":   {"ar": "🐈‍⬛ <b>القطة ظهرت!</b>", "en": "🐈‍⬛ <b>The cat appeared!</b>"},
    "cat_empty":    {"ar": "🐈‍⬛ <b>لا شيء... فقط آثار أقدام.</b>", "en": "🐈‍⬛ <b>Nothing... just paw prints.</b>"},
    "cat_result": {
        "ar": "{msg}\n\n<i>\"عندما تظهر القطة، يتحرك السوق.\"</i>\n\n💠 <b>+{pts} شظية</b>",
        "en": "{msg}\n\n<i>\"When the cat appears, the market moves.\"</i>\n\n💠 <b>+{pts} Shards</b>",
    },

    # ============ المتصدرون ============
    "top_header": {"ar": "🏆 <b>لوحة المتصدرين — أنبياء الغابة</b>\n\n", "en": "🏆 <b>Leaderboard — Prophets of the Forest</b>\n\n"},
    "top_empty":  {"ar": "لا يوجد أحد بعد.", "en": "No one yet."},
    "top_my_rank": {"ar": "\n📍 ترتيبك: <code>{rank}</code> — <code>{pts}</code> 💠", "en": "\n📍 Your rank: <code>{rank}</code> — <code>{pts}</code> 💠"},

    # ============ الدعوة ============
    "invite_header": {
        "ar": "👥 <b>نظام الدعوة</b>\n\n🔗 رابطك:\n<code>{link}</code>\n\n📊 <b>إحصائياتك:</b>\n• مدعوون: <code>{total}</code>\n• فعّالون: <code>{verified}</code>\n• شظايا مكتسبة: <code>{earned}</code> 💠\n\n💡 <b>كيف يعمل:</b>\n1️⃣ شارك رابطك\n2️⃣ عندما يُكمل صديقك مهمته الأولى → <code>+{ref_pts} شظية</code> لك",
        "en": "👥 <b>Invite System</b>\n\n🔗 Your link:\n<code>{link}</code>\n\n📊 <b>Your stats:</b>\n• Invited: <code>{total}</code>\n• Active: <code>{verified}</code>\n• Shards earned: <code>{earned}</code> 💠\n\n💡 <b>How it works:</b>\n1️⃣ Share your link\n2️⃣ When your friend completes their first task → <code>+{ref_pts} Shards</code> for you",
    },
    "invite_new_join": {
        "ar": "👥 <b>انضم شخص عبر رابطك!</b>\n\n🎁 ستحصل على <code>+{pts} شظية</code> عندما يُكمل مهمته الأولى.",
        "en": "👥 <b>Someone joined via your link!</b>\n\n🎁 You'll get <code>+{pts} Shards</code> when they complete their first task.",
    },
    "invite_reward": {
        "ar": "🎉 <b>مكافأة دعوة!</b>\n\nأكمل أحد مدعويك مهمته الأولى.\n💠 <b>+{pts} شظية</b>",
        "en": "🎉 <b>Referral reward!</b>\n\nOne of your invitees completed their first task.\n💠 <b>+{pts} Shards</b>",
    },

    # ============ حسابي ============
    "me_header": {
        "ar": "💼 <b>حسابك</b>\n\n🆔 <code>{uid}</code>\n💠 الشظايا: <code>{pts}</code>\n📊 حصتك من الإجمالي: <code>{share}%</code>\n\n🔥 Streak: <code>{streak}</code> (الأفضل: {best})\n📖 الفصول المقروءة: <code>{chapters}/{total_chapters}</code>\n👥 المدعوون: <code>{verified}/{total}</code> فعّال\n\n💎 المحفظة: {wallet}",
        "en": "💼 <b>Your Account</b>\n\n🆔 <code>{uid}</code>\n💠 Shards: <code>{pts}</code>\n📊 Your share: <code>{share}%</code>\n\n🔥 Streak: <code>{streak}</code> (Best: {best})\n📖 Chapters read: <code>{chapters}/{total_chapters}</code>\n👥 Invited: <code>{verified}/{total}</code> active\n\n💎 Wallet: {wallet}",
    },
    "me_no_account": {"ar": "لا يوجد حساب.", "en": "No account found."},
    "me_wallet_unset": {"ar": "❌ غير مسجّل", "en": "❌ Not set"},

    # ============ المحفظة ============
    "wallet_exists": {
        "ar": "💎 <b>محفظتك مسجّلة مسبقًا</b>\n\n<code>{wallet}</code>\n\n⚠️ لتغييرها، تواصل مع الأدمن.",
        "en": "💎 <b>Your wallet is already registered</b>\n\n<code>{wallet}</code>\n\n⚠️ Contact admin to change it.",
    },
    "wallet_prompt": {
        "ar": "💎 <b>تسجيل محفظة Solana</b>\n\nسنستخدم عنوان محفظتك لتوزيع <b>$ORACLE</b> يوم الإطلاق.\n\n📍 أرسل عنوان محفظتك (Phantom / Solflare / ...)\n\n<b>مثال:</b>\n<code>7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU</code>\n\n⚠️ تأكد أنه عنوان <b>Solana</b> (ليس Ethereum).\n⚠️ سنستخدمه مرة واحدة ولا يمكن تغييره لاحقًا.\n\nلإلغاء: /cancel",
        "en": "💎 <b>Register Solana Wallet</b>\n\nWe'll use your wallet address to distribute <b>$ORACLE</b> on launch day.\n\n📍 Send your wallet address (Phantom / Solflare / ...)\n\n<b>Example:</b>\n<code>7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU</code>\n\n⚠️ Make sure it's a <b>Solana</b> address (not Ethereum).\n⚠️ Used once and cannot be changed later.\n\nTo cancel: /cancel",
    },
    "wallet_invalid": {
        "ar": "❌ <b>عنوان غير صالح.</b>\n\nيجب أن يكون عنوان Solana (32-44 حرفًا).",
        "en": "❌ <b>Invalid address.</b>\n\nMust be a Solana address (32-44 characters).",
    },
    "wallet_dup": {
        "ar": "❌ <b>هذه المحفظة مسجّلة لمستخدم آخر.</b>\n\nلا يمكن استخدام نفس المحفظة لحسابين.",
        "en": "❌ <b>This wallet is registered to another user.</b>\n\nSame wallet cannot be used for two accounts.",
    },
    "wallet_saved": {
        "ar": "✅ <b>تم تسجيل محفظتك!</b>\n\n<code>{wallet}</code>\n\n💎 يوم إطلاق <b>$ORACLE</b>، ستستلم شظاياك هنا.",
        "en": "✅ <b>Wallet registered!</b>\n\n<code>{wallet}</code>\n\n💎 On <b>$ORACLE</b> launch day, you'll receive your shards here.",
    },

    # ============ أخطاء ============
    "cancelled":       {"ar": "✅ تم الإلغاء.", "en": "✅ Cancelled."},
    "state_cancelled": {"ar": "⚠️ تم إلغاء العملية السابقة.", "en": "⚠️ Previous action was cancelled."},
    "use_menu":        {"ar": "استخدم الأزرار 👇", "en": "Use the buttons 👇"},
    "rate_limited":    {"ar": "⏳ انتظر لحظة ثم أعد المحاولة.", "en": "⏳ Wait a moment and try again."},
}


def t(lang: str, key: str, **kwargs) -> str:
    """يرجع النص المترجم للغة المطلوبة مع استبدال المتغيرات."""
    entry = STRINGS.get(key)
    if not entry:
        return f"[{key}]"
    text = entry.get(lang) or entry.get("ar") or entry.get("en") or f"[{key}]"
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text


def kb_lang():
    """لوحة اختيار اللغة."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇸🇦 العربية", callback_data="set_lang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
        ]
    ])
