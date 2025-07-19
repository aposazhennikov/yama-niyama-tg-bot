"""Command handlers for yoga bot."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

from .storage import JsonStorage, User, Feedback
from .scheduler import YogaScheduler
from .utils import (
    PrinciplesManager, 
    is_valid_timezone, 
    is_valid_time_format, 
    validate_skip_days,
    format_principle_message
)


logger = logging.getLogger(__name__)


# Multilingual texts
TEXTS = {
    "en": {
        "welcome": (
            "🕊️ **Welcome to Yoga Principles Bot!**\n\n"
            "🎯 **What I do:**\n"
            "Every day I send you one of the 10 fundamental yoga principles (yamas and niyamas) "
            "at your preferred time with full description and practical tips.\n\n"
            "🌟 **Who will find this useful:**\n"
            "• Yoga practitioners of any level\n"
            "• Those who want to develop mindfulness\n"
            "• People striving for spiritual growth\n"
            "• Anyone interested in yoga philosophy\n\n"
            "🔄 **How it works:**\n"
            "• Principles are chosen randomly for each user\n"
            "• Repetitions are possible — this is normal and helpful!\n"
            "• Each principle is a daily lesson\n"
            "• You can skip certain days of the week\n\n"
            "Let's start with choosing your preferred language:"
        ),
        "language_chosen": "✅ Language set to English!",
        "timezone_step": (
            "📍 **Step 1/3: Time Zone**\n"
                "Choose your time zone:"
        ),
        "timezone_custom": "⌨️ Enter manually",
        "timezone_saved": "✅ Time zone saved!",
        "time_step": (
            "⏰ **Step 2/3: Send Time**\n"
            "Please specify time in HH:MM format (e.g., 08:00, 20:30)\n\n"
            "Morning time is recommended for better perception of principles."
        ),
        "time_saved": "✅ Send time saved!",
        "skip_days_step": (
            "📅 **Step 3/3: Days to Skip (optional)**\n"
            "Specify weekdays when you DON'T want to receive messages.\n\n"
            "Format: day numbers separated by commas (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)\n"
            "Examples:\n"
            "• `5,6` - skip weekends\n"
            "• `0,2,4` - skip Mon, Wed, Fri\n"
            "• `-` or just Enter - don't skip days"
        ),
        "setup_complete": (
            "🎉 **Setup Complete!**\n\n"
            "📋 **Your Settings:**\n"
            "🕐 Time: {time}\n"
            "🌍 Time Zone: {timezone}\n"
            "📅 Skip Days: {skip_days}\n\n"
            "✨ Your first yoga principle will be sent at the next scheduled time!\n\n"
            "Use /test to get a test message."
        ),
        "already_subscribed": (
            "🧘 You're already subscribed to daily yoga principles!\n\n"
            "Use /settings to change settings or /stop to unsubscribe."
        ),
        "unsubscribed": (
            "😔 You have unsubscribed from yoga principles newsletter.\n\n"
            "Use /start to subscribe again."
        ),
        "not_subscribed": "You were not subscribed to the newsletter.",
        "current_settings": (
            "⚙️ **Your Current Settings:**\n\n"
            "🌐 Language: {user_language}\n"
            "🕐 Send Time: `{time}`\n"
            "🌍 Time Zone: `{timezone}`\n"
            "📅 Skip Days: {skip_days}\n\n"
            "To change settings, use /start for new setup."
        ),
        "not_subscribed_test": "You're not subscribed to the newsletter. Use /start to subscribe.",
        "test_failed": "Failed to send test message.",
        "invalid_timezone": "❌ Invalid time zone format. Please try again.\n\nExamples: Europe/Moscow, Asia/Tashkent, UTC",
        "invalid_time": "❌ Invalid time format. Use HH:MM format (e.g., 08:00)",
        "invalid_skip_days": "❌ Invalid days format. Use numbers from 0 to 6 separated by commas.",
        "setup_error": "❌ Error saving settings. Please try again.",
        "error": "An error occurred. Please try again.",
        "choose_language": "Please choose your language:",
        "english": "🇺🇸 English",
        "russian": "🇷🇺 Русский",
        "menu": "📋 **Main Menu**",
        "menu_settings": "⚙️ Settings",
        "menu_test": "🧪 Test Message",
        "sending_test": "🧪 Sending test message...",
        "menu_about": "ℹ️ About Bot",
        "menu_feedback": "💌 Feedback & Ideas",
        "menu_stop": "❌ Unsubscribe",
        "settings_menu": "⚙️ **Settings Menu**\n\nWhat would you like to change?",
        "change_language": "🌐 Change Language",
        "change_time": "⏰ Change Send Time",
        "change_timezone": "🌍 Change Time Zone",
        "change_skip_days": "📅 Change Skip Days",
        "back_to_menu": "🔙 Back to Menu",
        "skip_days_improved": (
            "📅 **Days to Skip (optional)**\n\n"
            "You can:\n"
            "• Enter day numbers: `5,6` (skip weekends)\n"
            "• Enter day numbers: `0,2,4` (skip Mon, Wed, Fri)\n"
            "• Type anything else to not skip any days\n\n"
            "Examples: 'no skip', 'don't skip', '-', or just press Enter"
        ),
        "no_skip_days": "✅ No days will be skipped",
        "about_text": (
            "🕊️ **Yama/Niyama Training Bot**\n\n"
            "This bot helps you practice yoga principles (Yama and Niyama) daily. "
            "Each day you receive one principle that becomes your focus of attention for the entire day.\n\n"
            "🌟 **Features:**\n"
            "• Principles are chosen randomly - everyone has their own path!\n"
            "• Repetitions help better understand the principles\n"
            "• Practice the principle throughout the day\n"
            "• Develop mindfulness in everyday life\n\n"
            "⚙️ **Capabilities:**\n"
            "🔹 **Random selection** of principle for each user\n"
            "🔹 **Two languages:** English and Russian\n"
            "🔹 **Flexible settings** for receiving time\n"
            "🔹 **Skip days** when you need to rest\n\n"
            "Created with ❤️ for your spiritual growth. Let's change for the better together!"
        ),
        "feedback_prompt": (
            "💌 **Share Your Feedback & Ideas**\n\n"
            "Your opinion and suggestions matter! Please share:\n"
            "• How do you like the bot?\n"
            "• What features would you like to see?\n"
            "• Any suggestions for improvement?\n"
            "• Issues you've encountered\n"
            "• Ideas for new principles or content\n\n"
            "Just write your message below:"
        ),
        "feedback_sent": "✅ Thank you for your feedback! Your message has been sent to the developers.",
        "feedback_too_long": "❌ Message too long. Please keep it under 1000 characters.",
        "feedback_rate_limit": "⏰ Please wait before sending another feedback. You can send feedback once every 10 minutes.",
        "feedback_error": "❌ Error saving your feedback. Please try again later."
    },
    "ru": {
        "welcome": (
            "🕊️ **Добро пожаловать в бот принципов йоги!**\n\n"
            "🎯 **Что я делаю:**\n"
            "Каждый день отправляю вам один из 10 основных принципов йоги (ямы и ниямы) "
            "в удобное для вас время.\n\n"
            "🌟 **Для кого это будет полезно:**\n"
            "• Практикующим йогу любого уровня\n"
            "• Тем, кто хочет развивать осознанность\n"
            "• Людям, которые стремятся к Развитию\n"
            "• Всем, кто интересуется философией йоги\n\n"
            "🔄 **Как это работает:**\n"
            "• Принципы выбираются случайно для каждого пользователя\n"
            "• Повторения возможны — это нормально и полезно - укаждого своя судьба!\n"
            "• Каждый принцип — это урок на день, мы стараемся придерживаться этого принципа на протяжении всего дня, во всех аспектах жизни\n"
            "• Вы можете пропускать определённые дни недели\n\n"
            "Начнём с выбора предпочитаемого языка:"
        ),
        "language_chosen": "✅ Язык установлен: Русский!",
        "timezone_step": (
            "📍 **Шаг 1/3: Часовой пояс**\n"
            "Выберите ваш часовой пояс:"
        ),
        "timezone_custom": "⌨️ Ввести вручную",
        "timezone_saved": "✅ Часовой пояс сохранён!",
        "time_step": (
            "⏰ **Шаг 2/3: Время отправки**\n"
            "Укажите время в формате ЧЧ:ММ (например: 08:00, 20:30)\n\n"
            "Рекомендуется утреннее время для лучшего восприятия принципов."
        ),
        "time_saved": "✅ Время отправки сохранено!",
        "skip_days_step": (
            "📅 **Шаг 3/3: Дни для пропуска (необязательно)**\n"
            "Укажите дни недели, в которые НЕ нужно присылать сообщения.\n\n"
            "Формат: номера дней через запятую (0=Пн, 1=Вт, 2=Ср, 3=Чт, 4=Пт, 5=Сб, 6=Вс)\n"
            "Примеры:\n"
            "• `5,6` - пропустить выходные\n"
            "• `0,2,4` - пропустить пн, ср, пт\n"
            "• `-` или просто Enter - не пропускать дни"
        ),
        "setup_complete": (
            "🎉 **Настройка завершена!**\n\n"
            "📋 **Ваши настройки:**\n"
            "🕐 Время: {time}\n"
            "🌍 Часовой пояс: {timezone}\n"
            "📅 Пропускать: {skip_days}\n\n"
            "✨ Первый принцип йоги будет отправлен в ближайшее запланированное время!\n\n"
            "Используйте /test для получения тестового сообщения."
        ),
        "already_subscribed": (
            "🧘 Вы уже подписаны на ежедневные принципы йоги!\n\n"
            "Используйте /settings для изменения настроек или /stop для отписки."
        ),
        "unsubscribed": (
            "😔 Вы отписались от рассылки принципов йоги.\n\n"
            "Используйте /start чтобы подписаться снова."
        ),
        "not_subscribed": "Вы не были подписаны на рассылку.",
        "current_settings": (
            "⚙️ **Ваши текущие настройки:**\n\n"
            "🌐 Язык: {user_language}\n"
            "🕐 Время отправки: `{time}`\n"
            "🌍 Часовой пояс: `{timezone}`\n"
            "📅 Пропускать дни: {skip_days}\n\n"
            "Чтобы изменить настройки, используйте /start для новой настройки."
        ),
        "not_subscribed_test": "Вы не подписаны на рассылку. Используйте /start для подписки.",
        "test_failed": "Не удалось отправить тестовое сообщение.",
        "invalid_timezone": "❌ Неверный формат часового пояса. Попробуйте еще раз.\n\nПримеры: Europe/Moscow, Asia/Tashkent, UTC",
        "invalid_time": "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например: 08:00)",
        "invalid_skip_days": "❌ Неверный формат дней. Используйте числа от 0 до 6 через запятую.",
        "setup_error": "❌ Ошибка при сохранении настроек. Попробуйте еще раз.",
        "error": "Произошла ошибка. Попробуйте еще раз.",
        "choose_language": "Пожалуйста, выберите ваш язык:",
        "english": "🇺🇸 English",
        "russian": "🇷🇺 Русский",
        "menu": "📋 **Главное меню**",
        "menu_settings": "⚙️ Настройки",
        "menu_test": "🧪 Тестовое сообщение",
        "sending_test": "🧪 Отправляю тестовое сообщение...",
        "menu_about": "ℹ️ О боте",
        "menu_feedback": "💌 Отзывы и идеи",
        "menu_stop": "❌ Отписаться",
        "settings_menu": "⚙️ **Меню настроек**\n\nЧто вы хотите изменить?",
        "change_language": "🌐 Изменить язык",
        "change_time": "⏰ Изменить время отправки",
        "change_timezone": "🌍 Изменить часовой пояс",
        "change_skip_days": "📅 Изменить дни пропуска",
        "back_to_menu": "🔙 Назад в меню",
        "skip_days_improved": (
            "📅 **Дни для пропуска (необязательно)**\n\n"
            "Вы можете:\n"
            "• Ввести номера дней: `5,6` (пропустить выходные)\n"
            "• Ввести номера дней: `0,2,4` (пропустить пн, ср, пт)\n"
            "• Написать что угодно другое, чтобы не пропускать дни\n\n"
            "Примеры: 'не пропускать', 'нет', '-', или просто нажмите Enter"
        ),
        "no_skip_days": "✅ Дни не будут пропускаться",
        "about_text": (
            "🕊️ **Бот для тренировки Ямы/Ниямы**\n\n"
            "Этот бот помогает вам ежедневно практиковать принципы йоги (Яма и Нияма). "
            "Каждый день вы получаете один принцип, который становится вашим фокусом внимания на весь день.\n\n"
            "🌟 **Особенности:**\n"
            "• Принципы выбираются случайно - у каждого своя судьба!\n"
            "• Повторения принципов помогают лучше их усвоить\n"
            "• Практикуем принцип в течение всего дня\n"
            "• Развиваем осознанность в повседневной жизни\n\n"
            "⚙️ **Возможности:**\n"
            "🔹 **Случайный выбор** принципа для каждого\n"
            "🔹 **Два языка:** русский и английский\n"
            "🔹 **Гибкие настройки** времени получения\n"
            "🔹 **Пропуск дней** когда нужно отдохнуть\n\n"
            "Создано с ❤️ для вашего духовного развития. Давайте меняться к лучшему вместе!"
        ),
        "feedback_prompt": (
            "💌 **Поделитесь отзывом и идеями**\n\n"
            "Ваше мнение и предложения очень важны! Поделитесь:\n"
            "• Как вам бот?\n"
            "• Какие функции хотели бы видеть?\n"
            "• Есть предложения по улучшению?\n"
            "• Нашли какие-то проблемы?\n"
            "• Идеи для новых принципов или контента\n\n"
            "Просто напишите ваше сообщение ниже:"
        ),
        "feedback_sent": "✅ Спасибо за ваш отзыв! Ваше сообщение отправлено разработчикам.",
        "feedback_too_long": "❌ Сообщение слишком длинное. Пожалуйста, сократите его до 1000 символов.",
        "feedback_rate_limit": "⏰ Пожалуйста, подождите перед отправкой другого отзыва. Вы можете отправить отзыв один раз каждые 10 минут.",
        "feedback_error": "❌ Ошибка при сохранении вашего отзыва. Пожалуйста, попробуйте позже."
    },
    "uz": {
        "welcome": (
            "🕊️ **Yoga tamoyillari botiga xush kelibsiz!**\n\n"
            "🎯 **Men nima qilaman:**\n"
            "Har kuni sizga 10 ta asosiy yoga tamoyilidan birini (yamalar va niyamalar) "
            "siz uchun qulay vaqtda yuboran.\n\n"
            "🌟 **Bu kimlar uchun foydali:**\n"
            "• Har qanday darajadagi yoga amaliyotchilari\n"
            "• Onglilikni rivojlantirmoqchi bo'lganlar\n"
            "• Ruhiy o'sishga intiluvchi odamlar\n"
            "• Yoga falsafasiga qiziquvchi barcha kishilar\n\n"
            "🔄 **Bu qanday ishlaydi:**\n"
            "• Tamoyillar har bir foydalanuvchi uchun tasodifiy tanlanadi\n"
            "• Takrorlashlar mumkin — bu normal va foydali!\n"
            "• Har bir tamoyil — kunlik darsdir\n"
            "• Siz haftaning ma'lum kunlarini o'tkazib yuborishingiz mumkin\n\n"
            "Keling, kerakli tilni tanlashdan boshlaylik:"
        ),
        "language_chosen": "✅ Til o'zbekchaga o'rnatildi!",
        "timezone_step": (
            "📍 **1/3-qadam: Vaqt mintaqasi**\n"
            "Vaqt mintaqangizni tanlang:"
        ),
        "timezone_custom": "⌨️ Qo'lda kiriting",
        "timezone_saved": "✅ Vaqt mintaqasi saqlandi!",
        "time_step": (
            "⏰ **2/3-qadam: Yuborish vaqti**\n"
            "Vaqtni SS:DD formatida ko'rsating (masalan: 08:00, 20:30)\n\n"
            "Tamoyillarni yaxshiroq qabul qilish uchun ertalabki vaqt tavsiya etiladi."
        ),
        "time_saved": "✅ Yuborish vaqti saqlandi!",
        "skip_days_step": (
            "📅 **3/3-qadam: O'tkazib yuborish kunlari (ixtiyoriy)**\n"
            "Xabar yuborilmasligi kerak bo'lgan hafta kunlarini ko'rsating.\n\n"
            "Format: vergul bilan ajratilgan kunlar raqamlari (0=Du, 1=Se, 2=Ch, 3=Pa, 4=Ju, 5=Sh, 6=Ya)\n"
            "Misollar:\n"
            "• `5,6` - dam olish kunlarini o'tkazib yuborish\n"
            "• `0,2,4` - Du, Ch, Ju kunlarini o'tkazib yuborish\n"
            "• `-` yoki oddiy Enter - kunlarni o'tkazib yubormaslik"
        ),
        "skip_days_saved": "✅ O'tkazib yuborish kunlari saqlandi!",
        "setup_complete": (
            "🎉 **Sozlash yakunlandi!**\n\n"
            "📋 **Sizning sozlamalaringiz:**\n"
            "🕐 Vaqt: {time}\n"
            "🌍 Vaqt mintaqasi: {timezone}\n"
            "📅 O'tkazib yuborish kunlari: {skip_days}\n\n"
            "✨ Birinchi yoga tamoyili keyingi rejalashtirilgan vaqtda yuboriladi!\n\n"
            "/test dan test xabarini olish uchun foydalaning."
        ),
        "already_subscribed": "Siz allaqachon obuna bo'lgansiz. Sozlamalarni o'zgartirish uchun /settings dan foydalaning.",
        "unsubscribed": "✅ Siz muvaffaqiyatli obunani bekor qildingiz. Qayta obuna bo'lish uchun /start dan foydalaning.",
        "not_subscribed": "Siz yangiliklar ro'yxatiga obuna bo'lmagan edingiz.",
        "current_settings": (
            "⚙️ **Sizning joriy sozlamalaringiz:**\n\n"
            "🌐 Til: {user_language}\n"
            "🕐 Yuborish vaqti: `{time}`\n"
            "🌍 Vaqt mintaqasi: `{timezone}`\n"
            "📅 O'tkazib yuborish kunlari: {skip_days}\n\n"
            "Sozlamalarni o'zgartirish uchun yangi sozlash uchun /start dan foydalaning."
        ),
        "not_subscribed_test": "Siz yangiliklar ro'yxatiga obuna bo'lmagansiz. Obuna bo'lish uchun /start dan foydalaning.",
        "test_failed": "Test xabarini yuborishda xatolik yuz berdi.",
        "invalid_timezone": "❌ Noto'g'ri vaqt mintaqasi formati. Iltimos, qayta urinib ko'ring.\n\nMisollar: Asia/Tashkent, Europe/Moscow, UTC",
        "invalid_time": "❌ Noto'g'ri vaqt formati. SS:DD formatidan foydalaning (masalan, 08:00)",
        "invalid_skip_days": "❌ Noto'g'ri kunlar formati. Vergul bilan ajratilgan 0 dan 6 gacha raqamlardan foydalaning.",
        "setup_error": "❌ Sozlamalarni saqlashda xatolik. Iltimos, qayta urinib ko'ring.",
        "error": "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
        "choose_language": "Iltimos, tilingizni tanlang:",
        "english": "🇺🇸 English",
        "russian": "🇷🇺 Русский",
        "uzbek": "🇺🇿 O'zbek",
        "menu": "📋 **Asosiy menyu**",
        "menu_settings": "⚙️ Sozlamalar",
        "menu_test": "🧪 Test xabari",
        "sending_test": "🧪 Test xabarini yubormoqdaman...",
        "menu_about": "ℹ️ Bot haqida",
        "menu_feedback": "💌 Fikr va takliflar",
        "menu_stop": "❌ Obunani bekor qilish",
        "settings_menu": "⚙️ **Sozlamalar menyusi**\n\nNimani o'zgartirmoqchisiz?",
        "change_language": "🌐 Tilni o'zgartirish",
        "change_time": "⏰ Yuborish vaqtini o'zgartirish",
        "change_timezone": "🌍 Vaqt mintaqasini o'zgartirish",
        "change_skip_days": "📅 O'tkazib yuborish kunlarini o'zgartirish",
        "back_to_menu": "🔙 Menyuga qaytish",
        "about_text": (
            "🕊️ **Yoga tamoyillari boti haqida**\n\n"
            "Bu bot sizga har kuni yoga tamoyillaridan birini yuboradi.\n\n"
            "🎯 **Maqsad:** Yoga tamoyillarini kundalik hayotingizga kiritishga yordam berish\n\n"
            "📖 **Tamoyillar:**\n"
            "• 5 ta Yama (ijtimoiy tartib tamoyillari)\n"
            "• 5 ta Niyama (shaxsiy tartib tamoyillari)\n\n"
            "💝 **Bepul va ochiq manba**\n\n"
            "🌟 Har bir tamoyil sizning ruhiy o'sishingiz uchun kichik qadamdir!"
        ),
        "feedback_request": (
            "💌 **Fikr va takliflaringiz**\n\n"
            "Botni yaxshilash uchun fikrlaringizni yuboring:\n"
            "• Qanday xususiyatlar qo'shilsin?\n"
            "• Nimani o'zgartirish kerak?\n"
            "• Umumiy taassurotlaringiz\n\n"
            "Xabaringizni yozing:"
        ),
        "feedback_received": "✅ Rahmat! Sizning fikringiz qabul qilindi va ko'rib chiqiladi.",
        "feedback_too_long": "❌ Xabar juda uzun. Iltimos, uni 1000 belgigacha qisqartiring.",
        "feedback_rate_limit": "⏰ Iltimos, boshqa fikr yuborishdan oldin kuting. Har 10 daqiqada bir marta fikr yuborishingiz mumkin.",
        "feedback_error": "❌ Fikringizni saqlashda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
    },
    "kz": {
        "welcome": (
            "🕊️ **Йога принциптері ботына қош келдіңіз!**\n\n"
            "🎯 **Мен не істеймін:**\n"
            "Күн сайын сізге 10 негізгі йога принциптерінің бірін (ямалар мен ниямалар) "
            "сізге ыңғайлы уақытта жіберемін.\n\n"
            "🌟 **Бұл кімдерге пайдалы:**\n"
            "• Кез келген деңгейдегі йога практиктері\n"
            "• Саналылықты дамытқысы келетіндер\n"
            "• Рухани өсуге ұмтылушылар\n"
            "• Йога философиясына қызығушылық танытушылар\n\n"
            "🔄 **Бұл қалай жұмыс істейді:**\n"
            "• Принциптер әрбір пайдаланушы үшін кездейсоқ таңдалады\n"
            "• Қайталаулар мүмкін — бұл қалыпты және пайдалы!\n"
            "• Әрбір принцип — күнделікті сабақ\n"
            "• Сіз аптаның белгілі күндерін өткізіп жіберуіңізге болады\n\n"
            "Келіңіз, қажетті тілді таңдаудан бастайық:"
        ),
        "language_chosen": "✅ Тіл қазақшаға орнатылды!",
        "timezone_step": (
            "📍 **1/3-қадам: Уақыт белдеуі**\n"
            "Уақыт белдеуіңізді таңдаңыз:"
        ),
        "timezone_custom": "⌨️ Қолмен енгізу",
        "timezone_saved": "✅ Уақыт белдеуі сақталды!",
        "time_step": (
            "⏰ **2/3-қадам: Жіберу уақыты**\n"
            "Уақытты СС:ДД форматында көрсетіңіз (мысалы: 08:00, 20:30)\n\n"
            "Принциптерді жақсырақ қабылдау үшін таңертеңгілік уақыт ұсынылады."
        ),
        "time_saved": "✅ Жіберу уақыты сақталды!",
        "skip_days_step": (
            "📅 **3/3-қадам: Өткізіп жіберу күндері (қосымша)**\n"
            "Хабар жіберілмеу керек болатын апта күндерін көрсетіңіз.\n\n"
            "Формат: үтірмен бөлінген күндер сандары (0=Дс, 1=Сс, 2=Ср, 3=Бс, 4=Жм, 5=Сб, 6=Жк)\n"
            "Мысалдар:\n"
            "• `5,6` - демалыс күндерін өткізіп жіберу\n"
            "• `0,2,4` - Дс, Ср, Жм күндерін өткізіп жіберу\n"
            "• `-` немесе жай Enter - күндерді өткізіп жібермеу"
        ),
        "skip_days_saved": "✅ Өткізіп жіберу күндері сақталды!",
        "setup_complete": (
            "🎉 **Баптау аяқталды!**\n\n"
            "📋 **Сіздің баптауларыңыз:**\n"
            "🕐 Уақыт: {time}\n"
            "🌍 Уақыт белдеуі: {timezone}\n"
            "📅 Өткізіп жіберу күндері: {skip_days}\n\n"
            "✨ Алғашқы йога принципі келесі жоспарланған уақытта жіберіледі!\n\n"
            "/test арқылы тест хабарын алу үшін пайдаланыңыз."
        ),
        "already_subscribed": "Сіз қазірдің өзінде жазылғансыз. Баптауларды өзгерту үшін /settings пайдаланыңыз.",
        "unsubscribed": "✅ Сіз сәтті жазылудан бас тарттыңыз. Қайта жазылу үшін /start пайдаланыңыз.",
        "not_subscribed": "Сіз жаңалықтар тізіміне жазылмағансыз.",
        "current_settings": (
            "⚙️ **Сіздің ағымдағы баптауларыңыз:**\n\n"
            "🌐 Тіл: {user_language}\n"
            "🕐 Жіберу уақыты: `{time}`\n"
            "🌍 Уақыт белдеуі: `{timezone}`\n"
            "📅 Өткізіп жіберу күндері: {skip_days}\n\n"
            "Баптауларды өзгерту үшін жаңа баптау үшін /start пайдаланыңыз."
        ),
        "not_subscribed_test": "Сіз жаңалықтар тізіміне жазылмағансыз. Жазылу үшін /start пайдаланыңыз.",
        "test_failed": "Тест хабарын жіберуде қате орын алды.",
        "invalid_timezone": "❌ Дұрыс емес уақыт белдеуі форматы. Қайтадан көріңіз.\n\nМысалдар: Asia/Almaty, Europe/Moscow, UTC",
        "invalid_time": "❌ Дұрыс емес уақыт форматы. СС:ДД форматын пайдаланыңыз (мысалы, 08:00)",
        "invalid_skip_days": "❌ Дұрыс емес күндер форматы. Үтірмен бөлінген 0 мен 6 арасындағы сандарды пайдаланыңыз.",
        "setup_error": "❌ Баптауларды сақтауда қате. Қайтадан көріңіз.",
        "error": "Қате орын алды. Қайтадан көріңіз.",
        "choose_language": "Тіліңізді таңдаңыз:",
        "english": "🇺🇸 English",
        "russian": "🇷🇺 Русский",
        "uzbek": "🇺🇿 O'zbek",
        "kazakh": "🇰🇿 Қазақша",
        "menu": "📋 **Негізгі мәзір**",
        "menu_settings": "⚙️ Баптаулар",
        "menu_test": "🧪 Тест хабар",
        "sending_test": "🧪 Тест хабарын жіберуде...",
        "menu_about": "ℹ️ Бот туралы",
        "menu_feedback": "💌 Пікірлер мен ұсыныстар",
        "menu_stop": "❌ Жазылудан бас тарту",
        "settings_menu": "⚙️ **Баптаулар мәзірі**\n\nНені өзгерткіңіз келеді?",
        "change_language": "🌐 Тілді өзгерту",
        "change_time": "⏰ Жіберу уақытын өзгерту",
        "change_timezone": "🌍 Уақыт белдеуін өзгерту",
        "change_skip_days": "📅 Өткізіп жіберу күндерін өзгерту",
        "back_to_menu": "🔙 Мәзірге қайту",
        "about_text": (
            "🕊️ **Йога принциптері боты туралы**\n\n"
            "Бұл бот сізге күн сайын йога принциптерінің бірін жібереді.\n\n"
            "🎯 **Мақсаты:** Йога принциптерін күнделікті өміріңізге енгізуге көмектесу\n\n"
            "📖 **Принциптер:**\n"
            "• 5 Яма (әлеуметтік тәртіп принциптері)\n"
            "• 5 Нияма (жеке тәртіп принциптері)\n\n"
            "💝 **Тегін және ашық көз**\n\n"
            "🌟 Әрбір принцип сіздің рухани өсуіңіз үшін кішкентай қадам!"
        ),
        "feedback_request": (
            "💌 **Пікірлер мен ұсыныстарыңыз**\n\n"
            "Ботты жақсарту үшін пікірлеріңізді жіберіңіз:\n"
            "• Қандай мүмкіндіктер қосылсын?\n"
            "• Нені өзгерту керек?\n"
            "• Жалпы әсерлеріңіз\n\n"
            "Хабарыңызды жазыңыз:"
        ),
        "feedback_received": "✅ Рахмет! Сіздің пікіріңіз қабылданды және қаралады.",
        "feedback_too_long": "❌ Хабар тым ұзын. Оны 1000 таңбаға дейін қысқартыңыз.",
        "feedback_rate_limit": "⏰ Басқа пікір жібермес бұрын күтіңіз. Әр 10 минутта бір рет пікір жібере аласыз.",
        "feedback_error": "❌ Пікіріңізді сақтауда қате орын алды. Кейінірек көріңіз."
    }
}

# Admin texts (always in English, no Markdown to avoid parsing errors)
ADMIN_TEXTS = {
    "next_principle": "📋 Random principle for user {user_id}:\n\n{principle}\n\n💡 Principles are chosen randomly for each user",
    "no_principles": "No available principles for user {user_id}.",
    "add_usage": "Usage: /add <principle text>",
    "add_empty": "Principle text cannot be empty.",
    "add_success": "✅ Principle '{name}' successfully added!",
    "add_error": "❌ Error adding principle.",
    "stats": (
        "📊 Bot Statistics:\n\n"
        "👥 Total users: {total_users}\n"
        "✅ Active: {active_users}\n"
        "📨 Messages sent: {total_messages_sent}\n\n"
        "⏰ Scheduler:\n"
        "🔄 Scheduled jobs: {total_jobs}\n"
        "🎯 Jobs created: {jobs_created}\n"
        "🚀 Status: {status}"
    ),
    "broadcast_usage": "Usage: /broadcast <message>",
    "broadcast_empty": "Message text cannot be empty.",
    "broadcast_start": "📢 Starting broadcast to {count} users...",
    "broadcast_result": (
        "📢 Broadcast Results:\n\n"
        "✅ Sent: {sent}\n"
        "❌ Errors: {failed}\n"
        "👥 Total: {total}"
    ),
    "feedback_stats": (
        "💌 Feedback Statistics:\n\n"
        "📝 Total feedback: {total_feedback}\n"
        "📏 Average length: {average_length} chars\n"
        "💾 File size: {file_size_mb} MB\n\n"
        "🌐 By Language:\n{by_language}\n\n"
        "Use /feedback_list to see recent feedback"
    ),
    "feedback_list_header": "💌 Recent Feedback ({count} items):\n\n",
    "feedback_item": (
        "#{id} | {timestamp}\n"
        "👤 User: {chat_id} (@{username})\n"
        "🌐 Lang: {language} | 📏 {length} chars\n"
        "💬 {message}\n"
        "─────────────────\n"
    ),
    "no_feedback": "No feedback received yet.",
    "feedback_list_usage": "Usage: /feedback_list [limit] (default: 10, max: 50)",
    "admin_help": (
        "🔧 Admin Commands:\n\n"
        "📊 Statistics:\n"
        "• stats - Bot usage statistics\n"
        "• feedback_stats - Feedback statistics\n"
        "• feedback_list [limit] - View recent feedback\n\n"
        "📨 Messages:\n"
        "• next - Show random principle for user\n"
        "• broadcast <message> - Send message to all users\n\n"
        "🛠️ Management:\n"
        "• add <text> - Add new principle (not implemented)\n\n"
        "All commands are admin-only and require proper permissions."
    )
}


class BotHandlers:
    """Handlers for bot commands."""
    
    def __init__(
        self, 
        application: Application, 
        storage: JsonStorage, 
        scheduler: YogaScheduler,
        principles_manager: PrinciplesManager,
        admin_ids: List[int]
    ):
        self.application = application
        self.storage = storage
        self.scheduler = scheduler
        self.principles_manager = principles_manager
        self.admin_ids = admin_ids
        self.user_states = {}  # Track user registration states.
        
        # Register handlers.
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register all event handlers."""
        
        # User commands.
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("stop", self._handle_stop))
        self.application.add_handler(CommandHandler("settings", self._handle_settings))
        self.application.add_handler(CommandHandler("test", self._handle_test))
        self.application.add_handler(CommandHandler("menu", self._handle_menu))
        
        # Admin commands.
        self.application.add_handler(CommandHandler("next", self._handle_next))
        self.application.add_handler(CommandHandler("add", self._handle_add_principle))
        self.application.add_handler(CommandHandler("stats", self._handle_stats))
        self.application.add_handler(CommandHandler("broadcast", self._handle_broadcast))
        self.application.add_handler(CommandHandler("feedback_stats", self._handle_feedback_stats))
        self.application.add_handler(CommandHandler("feedback_list", self._handle_feedback_list))
        self.application.add_handler(CommandHandler("admin", self._handle_admin))
        
        # Callback query handlers.
        self.application.add_handler(CallbackQueryHandler(self._handle_language_callback, pattern="^lang_"))
        self.application.add_handler(CallbackQueryHandler(self._handle_timezone_callback, pattern="^tz_"))
        self.application.add_handler(CallbackQueryHandler(self._handle_skipday_callback, pattern="^skipday_"))
        self.application.add_handler(CallbackQueryHandler(self._handle_menu_callback, pattern="^menu_"))
        self.application.add_handler(CallbackQueryHandler(self._handle_settings_callback, pattern="^settings_"))
        self.application.add_handler(CallbackQueryHandler(self._handle_change_callback, pattern="^change_"))
        
        # General message handler for registration flow.
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
    
    def _get_text(self, key: str, language: str = "en", **kwargs) -> str:
        """Get localized text."""
        return TEXTS.get(language, TEXTS["en"]).get(key, key).format(**kwargs)
    
    def _get_admin_text(self, key: str, **kwargs) -> str:
        """Get admin text."""
        return ADMIN_TEXTS.get(key, key).format(**kwargs)
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        chat_id = update.effective_chat.id
        
        try:
            # Check if user already exists.
            user = await self.storage.get_user(chat_id)
            if user and user.is_active:
                text = self._get_text("already_subscribed", user.language)
                await update.message.reply_text(text, parse_mode='Markdown')
                return
            
            # Start with language selection.
            keyboard = [
                [
                    InlineKeyboardButton(TEXTS["en"]["english"], callback_data="lang_en"),
                    InlineKeyboardButton(TEXTS["en"]["russian"], callback_data="lang_ru")
                ],
                [
                    InlineKeyboardButton(TEXTS["uz"]["uzbek"], callback_data="lang_uz"),
                    InlineKeyboardButton(TEXTS["kz"]["kazakh"], callback_data="lang_kz")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show language selection message
            welcome_message = (
                "🕊️ **Welcome to Yoga Principles Bot!**\n\n"
                "Please choose your language / Пожалуйста, выберите язык:"
            )
            
            message = await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
            await self.storage.add_bot_message(chat_id, message.message_id, "welcome")
            
        except Exception as e:
            logger.error(f"Error in start handler for user {chat_id}: {e}")
            # Try to get user language for error message
            try:
                user = await self.storage.get_user(chat_id)
                error_lang = user.language if user else "en"
            except:
                error_lang = "en"
            await update.message.reply_text(self._get_text("error", language=error_lang))
    
    async def _handle_language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle language selection callback."""
        query = update.callback_query
        chat_id = query.message.chat.id
        language = query.data.split("_")[1]  # Extract language from callback data.
        
        try:
            await query.answer()
            logger.debug(f"User {chat_id} selected language: {language}")
            
            # Check if user already exists (changing language) or new registration
            user = await self.storage.get_user(chat_id)
            logger.debug(f"User {chat_id} exists: {user is not None}, active: {user.is_active if user else 'N/A'}")
            
            if user and user.is_active:
                # User exists - changing language
                logger.debug(f"Changing language for existing user {chat_id} from {user.language} to {language}")
                old_language = user.language
                user.language = language
                success = await self.storage.save_user(user)
                logger.debug(f"Language save success for user {chat_id}: {success}")
                
                if success:
                    # Clear any previous dialog before showing new menu
                    await self._clear_user_dialog(chat_id)
                    logger.debug(f"Cleared dialog for user {chat_id} before language change")
                    
                    confirmation = self._get_text("language_chosen", language)
                    text = f"{confirmation}\n\n{self._get_text('menu', language)}"
                    keyboard = self._create_main_menu_keyboard(language)
                    logger.debug(f"Sending menu in {language} to user {chat_id}")
                    
                    message = await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                    if message:
                        await self.storage.add_bot_message(chat_id, message.message_id, "menu")
                        logger.debug(f"Stored menu message for user {chat_id}")
                else:
                    logger.error(f"Failed to save language change for user {chat_id}")
                    await query.edit_message_text(self._get_text("setup_error", language))
            else:
                # New user registration
                logger.debug(f"Starting registration for new user {chat_id} in language {language}")
                self.user_states[chat_id] = {
                    "step": "timezone",
                    "language": language,
                    "registration_message_id": query.message.message_id  # Save message ID for editing
                }
                
                # Send language confirmation and timezone step with buttons.
                confirmation = self._get_text("language_chosen", language)
                timezone_msg = self._get_text("timezone_step", language)
                
                combined_msg = f"{confirmation}\n\n{timezone_msg}"
                keyboard = self._create_timezone_keyboard(language)
                
                logger.debug(f"Sending timezone selection in {language} to user {chat_id}")
                await query.edit_message_text(combined_msg, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in language callback for user {chat_id}: {e}")
            await query.edit_message_text(self._get_text("error", language))
    
    async def _handle_timezone_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle timezone selection callback."""
        query = update.callback_query
        chat_id = query.message.chat.id
        tz_data = query.data.split("_", 1)[1]  # Extract timezone or 'custom'
        
        try:
            await query.answer()
            logger.debug(f"Timezone callback for user {chat_id}: {tz_data}")
            
            user_state = self.user_states.get(chat_id)
            if not user_state or user_state.get("step") not in ["timezone", "change_timezone"]:
                logger.debug(f"Invalid state for user {chat_id}: {user_state}")
                return
            
            language = user_state["language"]
            logger.debug(f"User {chat_id} timezone selection in language: {language}")
            message_id = user_state.get("registration_message_id")
            
            if tz_data == "custom":
                # Switch to manual input mode
                if user_state.get("step") == "change_timezone":
                    self.user_states[chat_id]["step"] = "change_timezone_manual"
                else:
                    self.user_states[chat_id]["step"] = "timezone_manual"
                    
                custom_msg = (
                    f"{self._get_text('timezone_step', language)}\n\n"
                    "Please enter your timezone in IANA format:\n\n"
                    "Examples: Europe/Moscow, Asia/Tashkent, UTC"
                )
                await query.edit_message_text(custom_msg, parse_mode='Markdown')
            else:
                # Use selected timezone
                timezone_str = tz_data
                if is_valid_timezone(timezone_str):
                    if user_state.get("step") == "change_timezone":
                        # Handle timezone change
                        user = await self.storage.get_user(chat_id)
                        if user:
                            user.timezone = timezone_str
                            success = await self.storage.save_user(user)
                            
                            if success:
                                # Reschedule user messages with new timezone
                                await self.scheduler.schedule_user_immediately(chat_id)
                                
                                # Clean up state and show menu
                                del self.user_states[chat_id]
                                
                                text = f"{self._get_text('timezone_saved', language)}\n\n{self._get_text('menu', language)}"
                                keyboard = self._create_main_menu_keyboard(language)
                                await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                            else:
                                await query.edit_message_text(self._get_text("setup_error", language), parse_mode='Markdown')
                    else:
                        # Handle new registration
                        self.user_states[chat_id]["timezone"] = timezone_str
                        self.user_states[chat_id]["step"] = "time"
                        
                        confirmation = self._get_text("timezone_saved", language)
                        time_msg = self._get_text("time_step", language)
                        
                        combined_msg = f"{confirmation}\n\n{time_msg}"
                        
                        await query.edit_message_text(combined_msg, parse_mode='Markdown')
                else:
                    await query.edit_message_text(self._get_text("invalid_timezone", language), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in timezone callback for user {chat_id}: {e}")
            language = self.user_states.get(chat_id, {}).get("language", "en")
            await query.edit_message_text(self._get_text("error", language))
    
    async def _handle_skipday_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle skip days selection callback."""
        query = update.callback_query
        chat_id = query.message.chat.id
        skipday_data = query.data.split("_", 1)[1]  # Extract day number or action
        
        try:
            await query.answer()
            logger.debug(f"Skip day callback for user {chat_id}: {skipday_data}")
            
            user_state = self.user_states.get(chat_id)
            if not user_state or user_state.get("step") not in ["skip_days", "change_skip_days"]:
                logger.debug(f"Invalid state for skipday callback {chat_id}: {user_state}")
                return
            
            language = user_state["language"]
            
            # Initialize selected days if not exists
            if "selected_skip_days" not in user_state:
                user_state["selected_skip_days"] = []
            
            selected_days = user_state["selected_skip_days"]
            
            if skipday_data == "finish":
                # Finish selection and proceed
                await self._complete_skip_days_selection(update, selected_days, language)
                
            elif skipday_data == "none":
                # Clear all selections
                user_state["selected_skip_days"] = []
                await self._update_skip_days_keyboard(query, language, [])
                
            elif skipday_data == "weekends":
                # Select weekends (Saturday=5, Sunday=6)
                user_state["selected_skip_days"] = [5, 6]
                await self._update_skip_days_keyboard(query, language, [5, 6])
                
            elif skipday_data.isdigit():
                # Toggle specific day
                day = int(skipday_data)
                if day in selected_days:
                    selected_days.remove(day)
                else:
                    selected_days.append(day)
                
                user_state["selected_skip_days"] = selected_days
                await self._update_skip_days_keyboard(query, language, selected_days)
            
        except Exception as e:
            logger.error(f"Error in skipday callback for user {chat_id}: {e}")
            language = self.user_states.get(chat_id, {}).get("language", "en")
            await query.edit_message_text(self._get_text("error", language))
    
    async def _update_skip_days_keyboard(self, query, language: str, selected_days: List[int]) -> None:
        """Update skip days keyboard with current selection."""
        text = self._get_text("skip_days_step", language)
        
        # Add current selection info
        if selected_days:
            days_display = self._format_skip_days(selected_days, language)
            if language == "en":
                text += f"\n\n🔸 **Selected days to skip:** {days_display}"
            elif language == "ru":
                text += f"\n\n🔸 **Выбранные дни для пропуска:** {days_display}"
            elif language == "uz":
                text += f"\n\n🔸 **O'tkazib yuborish uchun tanlangan kunlar:** {days_display}"
            elif language == "kz":
                text += f"\n\n🔸 **Өткізіп жіберу үшін таңдалған күндер:** {days_display}"
        else:
            if language == "en":
                text += f"\n\n🔸 **No days selected** - messages will be sent daily"
            elif language == "ru":
                text += f"\n\n🔸 **Дни не выбраны** - сообщения будут отправляться ежедневно"
            elif language == "uz":
                text += f"\n\n🔸 **Kunlar tanlanmagan** - xabarlar har kuni yuboriladi"
            elif language == "kz":
                text += f"\n\n🔸 **Күндер таңдалмаған** - хабарлар күн сайын жіберіледі"
        
        keyboard = self._create_skip_days_keyboard(language, selected_days)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _complete_skip_days_selection(self, update: Update, selected_days: List[int], language: str) -> None:
        """Complete skip days selection and create user or update settings."""
        query = update.callback_query
        chat_id = query.message.chat.id
        user_state = self.user_states[chat_id]
        
        if user_state.get("step") == "change_skip_days":
            # Handle settings change
            try:
                user = await self.storage.get_user(chat_id)
                if user:
                    user.skip_day_id = selected_days
                    success = await self.storage.save_user(user)
                    
                    if success:
                        # Reschedule user messages with new skip days
                        await self.scheduler.schedule_user_immediately(chat_id)
                        
                        # Clean up state and show menu
                        del self.user_states[chat_id]
                        
                        if selected_days:
                            skip_days_display = self._format_skip_days(selected_days, language)
                            confirmation = f"✅ {skip_days_display}"
                        else:
                            if language == "en":
                                confirmation = "✅ Skip days cleared - daily messages enabled"
                            elif language == "ru":
                                confirmation = "✅ Дни пропуска очищены - включены ежедневные сообщения"
                            elif language == "uz":
                                confirmation = "✅ O'tkazib yuborish kunlari tozalandi - kundalik xabarlar yoqildi"
                            elif language == "kz":
                                confirmation = "✅ Өткізіп жіберу күндері тазаланды - күнделікті хабарлар қосылды"
                        
                        text = f"{confirmation}\n\n{self._get_text('menu', language)}"
                        keyboard = self._create_main_menu_keyboard(language)
                        
                        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                    else:
                        await query.edit_message_text(self._get_text("setup_error", language), parse_mode='Markdown')
                        
            except Exception as e:
                logger.error(f"Error updating skip days for user {chat_id}: {e}")
                await query.edit_message_text(self._get_text("error", language), parse_mode='Markdown')
                
        else:
            # Handle new registration
            from bot.storage import User
            
            user = User(
                chat_id=chat_id,
                language=language,
                timezone=user_state["timezone"],
                time_for_send=user_state["time"],
                skip_day_id=selected_days,
                is_active=True
            )
            
            success = await self.storage.save_user(user)
            if success:
                # Schedule user messages
                await self.scheduler.schedule_user_immediately(chat_id)
                
                # Clean up state
                del self.user_states[chat_id]
                
                skip_days_display = self._format_skip_days(selected_days, language)
                
                text = self._get_text(
                    "setup_complete",
                    language,
                    time=user.time_for_send,
                    timezone=user.timezone,
                    skip_days=skip_days_display
                )
                logger.debug(f"Setup complete text for user {chat_id} in language {language}: {text[:100]}...")
                
                # Add menu after setup completion
                text += f"\n\n{self._get_text('menu', language)}"
                keyboard = self._create_main_menu_keyboard(language)
                logger.debug(f"Final setup message for user {chat_id} in language {language}: {text[:150]}...")
                
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                # Store the final message ID
                await self.storage.add_bot_message(chat_id, query.message.message_id, "setup_complete")
            else:
                await query.edit_message_text(self._get_text("setup_error", language), parse_mode='Markdown')
    
    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command."""
        chat_id = update.effective_chat.id
        
        try:
            user = await self.storage.get_user(chat_id)
            language = user.language if user else "ru"  # Default to Russian
            
            # Delete user's /stop command message first
            await self._delete_message_safe(chat_id, update.message.message_id)
            
            # Clear entire dialog - try to delete recent messages aggressively
            await self._clear_entire_dialog(chat_id)
            
            success = await self.storage.deactivate_user(chat_id)
            if success:
                text = self._get_text("unsubscribed", language)
                # Remove user from scheduler
                await self.scheduler.remove_user_jobs(chat_id)
            else:
                text = self._get_text("not_subscribed", language)
            
            # Send final message directly through bot API
            await self.application.bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in stop handler for user {chat_id}: {e}")
            try:
                user = await self.storage.get_user(chat_id)
                error_lang = user.language if user else "ru"
                await self.application.bot.send_message(chat_id=chat_id, text=self._get_text("error", error_lang))
            except:
                await self.application.bot.send_message(chat_id=chat_id, text="Произошла ошибка.")
    
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command."""
        chat_id = update.effective_chat.id
        
        try:
            user = await self.storage.get_user(chat_id)
            if not user or not user.is_active:
                await update.message.reply_text(self._get_text("not_subscribed_test", language="en"))
                return
            
            language_display = {"en": "English", "ru": "Русский", "uz": "O'zbek", "kz": "Қазақша"}.get(user.language, "English")
            skip_days_display = self._format_skip_days(user.skip_day_id, user.language)
            
            text = self._get_text(
                "current_settings", 
                language=user.language,
                user_language=language_display,
                time=user.time_for_send,
                timezone=user.timezone,
                skip_days=skip_days_display
            )
            
            # Show settings menu instead of just text
            text += f"\n\n{self._get_text('settings_menu', language=user.language)}"
            keyboard = self._create_settings_menu_keyboard(user.language)
            
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in settings handler for user {chat_id}: {e}")
            # Try to get user language for error message
            try:
                user = await self.storage.get_user(chat_id)
                error_lang = user.language if user else "en"
            except:
                error_lang = "en"
            await update.message.reply_text(self._get_text("error", language=error_lang))
    
    async def _handle_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /test command."""
        chat_id = update.effective_chat.id
        
        try:
            user = await self.storage.get_user(chat_id)
            if not user or not user.is_active:
                lang = user.language if user else "en"
                await update.message.reply_text(self._get_text("not_subscribed_test", language=lang))
                return
            
            success = await self.scheduler.send_test_message(chat_id, user.language)
            if not success:
                text = self._get_text("test_failed", user.language)
                await update.message.reply_text(text)
                
        except Exception as e:
            logger.error(f"Error in test handler for user {chat_id}: {e}")
            # Try to get user language for error message
            try:
                user = await self.storage.get_user(chat_id)
                error_lang = user.language if user else "en"
            except:
                error_lang = "en"
            await update.message.reply_text(self._get_text("error", language=error_lang))
    
    # Admin handlers.
    async def _handle_next(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /next command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        # Check if update has message
        if not update.message:
            logger.warning("next called without message")
            return
        
        try:
            args = context.args
            target_chat_id = int(args[0]) if args else chat_id
            
            principle = await self.scheduler.get_next_principle_for_user(target_chat_id)
            if principle:
                principle_text = format_principle_message(principle)
                message_text = self._get_admin_text("next_principle", user_id=target_chat_id, principle=principle_text)
                # Send without Markdown to avoid parsing errors
                await update.message.reply_text(message_text)
            else:
                text = self._get_admin_text("no_principles", user_id=target_chat_id)
                await update.message.reply_text(text)
                
        except Exception as e:
            logger.error(f"Error in next handler: {e}")
            try:
                await update.message.reply_text("Error getting next principle.")
            except:
                logger.error(f"Could not send error message to {chat_id}")
    
    async def _handle_add_principle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /add command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        # Check if update has message
        if not update.message:
            logger.warning("add_principle called without message")
            return
        
        try:
            if not context.args:
                await update.message.reply_text(self._get_admin_text("add_usage"))
                return
            
            principle_text = " ".join(context.args)
            if not principle_text:
                await update.message.reply_text(self._get_admin_text("add_empty"))
                return
            
            # Simple parsing for new principle.
            lines = principle_text.split('\n')
            name = lines[0] if lines else "New Principle"
            description = '\n'.join(lines[1:]) if len(lines) > 1 else principle_text
            
            new_principle = {
                "name": name,
                "emoji": "🧘",
                "short_description": name,
                "description": description,
                "practice_tip": ""
            }
            
            success = await self.principles_manager.add_principle(new_principle)
            if success:
                text = self._get_admin_text("add_success", name=name)
            else:
                text = self._get_admin_text("add_error")
            
            await update.message.reply_text(text)
                
        except Exception as e:
            logger.error(f"Error in add principle handler: {e}")
            try:
                await update.message.reply_text(self._get_admin_text("add_error"))
            except:
                logger.error(f"Could not send error message to {chat_id}")
    
    async def _handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        # Check if update has message
        if not update.message:
            logger.warning("stats called without message")
            return
        
        try:
            # Get storage stats.
            storage_stats = await self.storage.get_stats()
            
            # Get scheduler stats.
            scheduler_stats = self.scheduler.get_scheduler_stats()
            
            status = "Running" if scheduler_stats['running'] else "Stopped"
            
            text = self._get_admin_text(
                "stats",
                total_users=storage_stats['total_users'],
                active_users=storage_stats['active_users'],
                total_messages_sent=storage_stats['total_messages_sent'],
                total_jobs=scheduler_stats['total_jobs'],
                jobs_created=scheduler_stats['jobs_created'],
                status=status
            )
            
            # Send without Markdown to avoid parsing errors
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Error in stats handler: {e}")
            try:
                await update.message.reply_text("Error getting statistics.")
            except:
                logger.error(f"Could not send error message to {chat_id}")
    
    async def _handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /broadcast command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        # Check if update has message
        if not update.message:
            logger.warning("broadcast called without message")
            return
        
        try:
            if not context.args:
                await update.message.reply_text(self._get_admin_text("broadcast_usage"))
                return
            
            broadcast_text = " ".join(context.args)
            if not broadcast_text:
                await update.message.reply_text(self._get_admin_text("broadcast_empty"))
                return
            
            # Get all active users.
            active_users = await self.storage.get_all_active_users()
            
            sent_count = 0
            failed_count = 0
            
            await update.message.reply_text(self._get_admin_text("broadcast_start", count=len(active_users)))
            
            for user in active_users:
                try:
                    # Send broadcast without Markdown to avoid parsing errors
                    await context.bot.send_message(user.chat_id, broadcast_text)
                    sent_count += 1
                except Exception:
                    failed_count += 1
            
            result_text = self._get_admin_text(
                "broadcast_result",
                sent=sent_count,
                failed=failed_count,
                total=len(active_users)
            )
            
            # Send result without Markdown to avoid parsing errors
            await update.message.reply_text(result_text)
            
        except Exception as e:
            logger.error(f"Error in broadcast handler: {e}")
            try:
                await update.message.reply_text("Error during broadcast.")
            except:
                logger.error(f"Could not send error message to {chat_id}")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle general messages for registration flow."""
        chat_id = update.effective_chat.id
        message_text = update.message.text
        message_id = update.message.message_id
        
        # Always delete user's message for clean dialog (with small delay for better UX)
        asyncio.create_task(self._delete_user_message_delayed(chat_id, message_id))
        
        # Check if user is in registration flow.
        if chat_id not in self.user_states:
            return
        
        try:
            user_state = self.user_states[chat_id]
            step = user_state["step"]
            language = user_state["language"]
            
            if step == "timezone" or step == "timezone_manual":
                await self._handle_timezone_input(update, message_text, language)
            elif step == "time":
                await self._handle_time_input(update, message_text, language)
            elif step == "change_timezone" or step == "change_timezone_manual":
                await self._handle_change_timezone_input(update, message_text, language)
            elif step == "change_time":
                await self._handle_change_time_input(update, message_text, language)
            elif step == "feedback":
                await self._handle_feedback_input(update, message_text, language)
                
        except Exception as e:
            logger.error(f"Error in message handler for user {chat_id}: {e}")
            language = self.user_states.get(chat_id, {}).get("language", "en")
            await update.message.reply_text(self._get_text("error", language))
    
    async def _handle_timezone_input(self, update: Update, timezone_str: str, language: str) -> None:
        """Handle timezone input during registration."""
        chat_id = update.effective_chat.id
        user_state = self.user_states[chat_id]
        message_id = user_state.get("registration_message_id")
        
        if not is_valid_timezone(timezone_str):
            if message_id:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=self._get_text("invalid_timezone", language),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(self._get_text("invalid_timezone", language), parse_mode='Markdown')
            return
        
        # Save timezone and move to next step.
        self.user_states[chat_id]["timezone"] = timezone_str
        self.user_states[chat_id]["step"] = "time"
        
        confirmation = self._get_text("timezone_saved", language)
        time_msg = self._get_text("time_step", language)
        
        combined_msg = f"{confirmation}\n\n{time_msg}"
        
        if message_id:
            await self.application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=combined_msg,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(combined_msg, parse_mode='Markdown')
    
    async def _handle_time_input(self, update: Update, time_str: str, language: str) -> None:
        """Handle time input during registration."""
        chat_id = update.effective_chat.id
        user_state = self.user_states[chat_id]
        message_id = user_state.get("registration_message_id")
        
        if not is_valid_time_format(time_str):
            if message_id:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=self._get_text("invalid_time", language),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(self._get_text("invalid_time", language))
            return
        
        # Save time and move to next step.
        self.user_states[chat_id]["time"] = time_str
        self.user_states[chat_id]["step"] = "skip_days"
        self.user_states[chat_id]["selected_skip_days"] = []  # Initialize empty selection
        
        confirmation = self._get_text("time_saved", language)
        skip_days_msg = self._get_text("skip_days_step", language)
        
        combined_msg = f"{confirmation}\n\n{skip_days_msg}"
        
        # Add info about no days selected initially
        if language == "en":
            combined_msg += f"\n\n🔸 **No days selected** - messages will be sent daily"
        elif language == "ru":
            combined_msg += f"\n\n🔸 **Дни не выбраны** - сообщения будут отправляться ежедневно"
        elif language == "uz":
            combined_msg += f"\n\n🔸 **Kunlar tanlanmagan** - xabarlar har kuni yuboriladi"
        elif language == "kz":
            combined_msg += f"\n\n🔸 **Күндер таңдалмаған** - хабарлар күн сайын жіберіледі"
        
        keyboard = self._create_skip_days_keyboard(language, [])
        
        if message_id:
            await self.application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=combined_msg,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(combined_msg, parse_mode='Markdown')
    

    
    def _format_skip_days(self, skip_days: List[int], language: str) -> str:
        """Format skip days for display."""
        if not skip_days:
            day_none = {"ru": "Нет", "en": "None", "uz": "Yo'q", "kz": "Жоқ"}
            return day_none.get(language, "None")
        
        day_names_map = {
            "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "uz": ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"],
            "kz": ["Дс", "Сс", "Ср", "Бс", "Жм", "Сб", "Жк"]
        }
        
        day_names = day_names_map.get(language, day_names_map["en"])
        return ", ".join([day_names[day] for day in skip_days])
    
    def _create_timezone_keyboard(self, language: str, add_back_button: bool = False) -> InlineKeyboardMarkup:
        """Create timezone selection keyboard."""
        timezones = {
            "en": [
                # Популярные часовые пояса для региона
                ("🇷🇺 Moscow +3", "Europe/Moscow"),
                ("🇺🇿 Tashkent +5", "Asia/Tashkent"),
                ("🇰🇿 Almaty +6", "Asia/Almaty"),
                ("🇺🇦 Kiev +2", "Europe/Kiev"),
                ("🇹🇷 Istanbul +3", "Europe/Istanbul"),
                ("🇦🇿 Baku +4", "Asia/Baku"),
                ("🇦🇲 Yerevan +4", "Asia/Yerevan"),
                ("🇬🇪 Tbilisi +4", "Asia/Tbilisi"),
                ("🇰🇬 Bishkek +6", "Asia/Bishkek"),
                ("🇹🇲 Ashgabat +5", "Asia/Ashgabat"),
                ("🇲🇳 Ulaanbaatar +8", "Asia/Ulaanbaatar"),
                ("🌍 UTC +0", "UTC"),
            ],
            "ru": [
                ("🇷🇺 Москва +3", "Europe/Moscow"),
                ("🇺🇿 Ташкент +5", "Asia/Tashkent"),
                ("🇰🇿 Алматы +6", "Asia/Almaty"),
                ("🇺🇦 Киев +2", "Europe/Kiev"),
                ("🇹🇷 Стамбул +3", "Europe/Istanbul"),
                ("🇦🇿 Баку +4", "Asia/Baku"),
                ("🇦🇲 Ереван +4", "Asia/Yerevan"),
                ("🇬🇪 Тбилиси +4", "Asia/Tbilisi"),
                ("🇰🇬 Бишкек +6", "Asia/Bishkek"),
                ("🇹🇲 Ашхабад +5", "Asia/Ashgabat"),
                ("🇲🇳 Улан-Батор +8", "Asia/Ulaanbaatar"),
                ("🌍 UTC +0", "UTC"),
            ],
            "uz": [
                ("🇺🇿 Toshkent +5", "Asia/Tashkent"),
                ("🇺🇿 Samarqand +5", "Asia/Samarkand"),
                ("🇰🇿 Almaty +6", "Asia/Almaty"),
                ("🇷🇺 Moskva +3", "Europe/Moscow"),
                ("🇹🇷 Istanbul +3", "Europe/Istanbul"),
                ("🇦🇿 Boku +4", "Asia/Baku"),
                ("🇦🇲 Yerevan +4", "Asia/Yerevan"),
                ("🇬🇪 Tbilisi +4", "Asia/Tbilisi"),
                ("🇰🇬 Bishkek +6", "Asia/Bishkek"),
                ("🇹🇲 Ashgabat +5", "Asia/Ashgabat"),
                ("🇺🇦 Kiev +2", "Europe/Kiev"),
                ("🌍 UTC +0", "UTC"),
            ],
            "kz": [
                ("🇰🇿 Алматы +6", "Asia/Almaty"),
                ("🇰🇿 Нұр-Сұлтан +6", "Asia/Almaty"),
                ("🇰🇿 Ақтөбе +5", "Asia/Aqtobe"),
                ("🇺🇿 Ташкент +5", "Asia/Tashkent"),
                ("🇷🇺 Мәскеу +3", "Europe/Moscow"),
                ("🇰🇬 Бішкек +6", "Asia/Bishkek"),
                ("🇹🇷 Стамбул +3", "Europe/Istanbul"),
                ("🇦🇿 Баку +4", "Asia/Baku"),
                ("🇦🇲 Ереван +4", "Asia/Yerevan"),
                ("🇬🇪 Тбилиси +4", "Asia/Tbilisi"),
                ("🇺🇦 Киев +2", "Europe/Kiev"),
                ("🌍 UTC +0", "UTC"),
            ]
        }
        
        keyboard = []
        tz_list = timezones.get(language, timezones["en"])
        
        # Create rows of 2 buttons each for better mobile experience
        for i in range(0, len(tz_list), 2):
            row = []
            for j in range(i, min(i + 2, len(tz_list))):
                display_name, tz_code = tz_list[j]
                row.append(InlineKeyboardButton(display_name, callback_data=f"tz_{tz_code}"))
            keyboard.append(row)
        
        # Add manual input button as last row
        keyboard.append([InlineKeyboardButton(
            self._get_text("timezone_custom", language), 
            callback_data="tz_custom"
        )])
        
        # Add back button if requested
        if add_back_button:
            keyboard.append([InlineKeyboardButton(
                self._get_text("back_to_menu", language), 
                callback_data="settings_back"
            )])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _create_skip_days_keyboard(self, language: str, selected_days: List[int] = None, add_back_button: bool = False) -> InlineKeyboardMarkup:
        """Create skip days selection keyboard."""
        if selected_days is None:
            selected_days = []
            
        day_names = {
            "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "ru": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
            "uz": ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"],
            "kz": ["Дүйсенбі", "Сейсенбі", "Сәрсенбі", "Бейсенбі", "Жұма", "Сенбі", "Жексенбі"]
        }
        
        days = day_names.get(language, day_names["en"])
        keyboard = []
        
        # Create buttons for each day (2 per row)
        for i in range(0, 7, 2):
            row = []
            for j in range(i, min(i + 2, 7)):
                day_idx = j
                is_selected = day_idx in selected_days
                emoji = "✅" if is_selected else "📅"
                day_name = days[day_idx]
                
                # Shorten day names for better mobile display
                if len(day_name) > 8:
                    day_name = day_name[:7] + "."
                
                button_text = f"{emoji} {day_name}"
                callback_data = f"skipday_{day_idx}"
                
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            keyboard.append(row)
        
        # Add action buttons - split into two rows for better layout
        if language == "en":
            keyboard.append([InlineKeyboardButton("🎯 No Skip Days", callback_data="skipday_none")])
            keyboard.append([InlineKeyboardButton("📅 Weekends Only", callback_data="skipday_weekends")])
        elif language == "ru":
            keyboard.append([InlineKeyboardButton("🎯 Не пропускать", callback_data="skipday_none")])
            keyboard.append([InlineKeyboardButton("📅 Только выходные", callback_data="skipday_weekends")])
        elif language == "uz":
            keyboard.append([InlineKeyboardButton("🎯 Kunlarni o'tkazmaslik", callback_data="skipday_none")])
            keyboard.append([InlineKeyboardButton("📅 Faqat dam olish kunlari", callback_data="skipday_weekends")])
        elif language == "kz":
            keyboard.append([InlineKeyboardButton("🎯 Күндерді өткізбеу", callback_data="skipday_none")])
            keyboard.append([InlineKeyboardButton("📅 Тек демалыс күндері", callback_data="skipday_weekends")])
        
        # Add finish button
        finish_text = {
            "en": "✅ Continue",
            "ru": "✅ Продолжить", 
            "uz": "✅ Davom etish",
            "kz": "✅ Жалғастыру"
        }
        
        keyboard.append([InlineKeyboardButton(
            finish_text.get(language, finish_text["en"]), 
            callback_data="skipday_finish"
        )])
        
        # Add back button if requested
        if add_back_button:
            keyboard.append([InlineKeyboardButton(
                self._get_text("back_to_menu", language), 
                callback_data="settings_back"
            )])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _create_main_menu_keyboard(self, language: str) -> InlineKeyboardMarkup:
        """Create main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(self._get_text("menu_settings", language), callback_data="menu_settings"),
                InlineKeyboardButton(self._get_text("menu_test", language), callback_data="menu_test")
            ],
            [
                InlineKeyboardButton(self._get_text("menu_about", language), callback_data="menu_about"),
                InlineKeyboardButton(self._get_text("menu_feedback", language), callback_data="menu_feedback")
            ],
            [
                InlineKeyboardButton(self._get_text("menu_stop", language), callback_data="menu_stop")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_settings_menu_keyboard(self, language: str) -> InlineKeyboardMarkup:
        """Create settings menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(self._get_text("change_language", language), callback_data="change_language"),
                InlineKeyboardButton(self._get_text("change_time", language), callback_data="change_time")
            ],
            [
                InlineKeyboardButton(self._get_text("change_timezone", language), callback_data="change_timezone"),
                InlineKeyboardButton(self._get_text("change_skip_days", language), callback_data="change_skip_days")
            ],
            [
                InlineKeyboardButton(self._get_text("back_to_menu", language), callback_data="menu_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def _handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /menu command."""
        chat_id = update.effective_chat.id
        
        try:
            user = await self.storage.get_user(chat_id)
            language = user.language if user else "en"
            
            if not user or not user.is_active:
                await update.message.reply_text(self._get_text("not_subscribed_test", language))
                return
            
            text = self._get_text("menu", language)
            keyboard = self._create_main_menu_keyboard(language)
            
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in menu handler for user {chat_id}: {e}")
            # Try to get user language for error message
            try:
                user = await self.storage.get_user(chat_id)
                error_lang = user.language if user else "en"
            except:
                error_lang = "en"
            await update.message.reply_text(self._get_text("error", language=error_lang))
    
    async def _handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle main menu callback queries."""
        query = update.callback_query
        chat_id = query.message.chat.id
        action = query.data.split("_", 1)[1]  # Extract action after "menu_"
        
        try:
            await query.answer()
            
            user = await self.storage.get_user(chat_id)
            language = user.language if user else "en"
            
            if action == "settings":
                text = self._get_text("settings_menu", language)
                keyboard = self._create_settings_menu_keyboard(language)
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                
            elif action == "test":
                await query.edit_message_text(self._get_text("sending_test", language))
                success = await self.scheduler.send_test_message(chat_id, language)
                if success:
                    text = self._get_text("menu", language)
                    keyboard = self._create_main_menu_keyboard(language)
                    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                else:
                    await query.edit_message_text(self._get_text("test_failed", language))
                    
            elif action == "about":
                text = self._get_text("about_text", language)
                keyboard = [[InlineKeyboardButton(self._get_text("back_to_menu", language), callback_data="menu_main")]]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                
            elif action == "feedback":
                # Set user state to expect feedback input
                self.user_states[chat_id] = {"step": "feedback", "language": language}
                
                text = self._get_text("feedback_prompt", language)
                keyboard = [[InlineKeyboardButton(self._get_text("back_to_menu", language), callback_data="menu_main")]]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                
            elif action == "stop":
                success = await self.storage.deactivate_user(chat_id)
                if success:
                    await query.edit_message_text(self._get_text("unsubscribed", language), parse_mode='Markdown')
                else:
                    await query.edit_message_text(self._get_text("not_subscribed", language))
                    
            elif action == "main":
                text = self._get_text("menu", language)
                keyboard = self._create_main_menu_keyboard(language)
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in menu callback for user {chat_id}: {e}")
            await query.edit_message_text(self._get_text("error", language))
    
    async def _handle_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle settings callback queries (back to settings menu)."""
        query = update.callback_query
        chat_id = query.message.chat.id
        
        try:
            await query.answer()
            
            user = await self.storage.get_user(chat_id)
            language = user.language if user else "en"
            
            text = self._get_text("settings_menu", language)
            keyboard = self._create_settings_menu_keyboard(language)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in settings callback for user {chat_id}: {e}")
            await query.edit_message_text(self._get_text("error", language))
    
    async def _handle_change_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle change settings callback queries."""
        query = update.callback_query
        chat_id = query.message.chat.id
        setting = query.data.split("_", 1)[1]  # Extract setting after "change_"
        
        try:
            await query.answer()
            
            user = await self.storage.get_user(chat_id)
            language = user.language if user else "en"
            
            if setting == "language":
                keyboard = [
                    [
                        InlineKeyboardButton(TEXTS["en"]["english"], callback_data="lang_en"),
                        InlineKeyboardButton(TEXTS["en"]["russian"], callback_data="lang_ru")
                    ],
                    [
                        InlineKeyboardButton(TEXTS["uz"]["uzbek"], callback_data="lang_uz"),
                        InlineKeyboardButton(TEXTS["kz"]["kazakh"], callback_data="lang_kz")
                    ],
                    [
                        InlineKeyboardButton(self._get_text("back_to_menu", language), callback_data="settings_back")
                    ]
                ]
                await query.edit_message_text(
                    self._get_text("choose_language", language), 
                    reply_markup=InlineKeyboardMarkup(keyboard), 
                    parse_mode='Markdown'
                )
                
            elif setting == "time":
                self.user_states[chat_id] = {"step": "change_time", "language": language, "settings_message_id": query.message.message_id}
                keyboard = [[InlineKeyboardButton(self._get_text("back_to_menu", language), callback_data="settings_back")]]
                await query.edit_message_text(
                    self._get_text("time_step", language), 
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
            elif setting == "timezone":
                self.user_states[chat_id] = {"step": "change_timezone", "language": language, "settings_message_id": query.message.message_id}
                keyboard = self._create_timezone_keyboard(language, add_back_button=True)
                await query.edit_message_text(
                    self._get_text("timezone_step", language), 
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
            elif setting == "skip_days":
                # Get current user skip days
                current_skip_days = user.skip_day_id if user else []
                self.user_states[chat_id] = {
                    "step": "change_skip_days", 
                    "language": language, 
                    "settings_message_id": query.message.message_id,
                    "selected_skip_days": current_skip_days.copy()
                }
                
                text = self._get_text("skip_days_step", language)
                
                # Add current selection info
                if current_skip_days:
                    days_display = self._format_skip_days(current_skip_days, language)
                    if language == "en":
                        text += f"\n\n🔸 **Current selection:** {days_display}"
                    elif language == "ru":
                        text += f"\n\n🔸 **Текущий выбор:** {days_display}"
                    elif language == "uz":
                        text += f"\n\n🔸 **Joriy tanlov:** {days_display}"
                    elif language == "kz":
                        text += f"\n\n🔸 **Ағымдағы таңдау:** {days_display}"
                else:
                    if language == "en":
                        text += f"\n\n🔸 **No days selected** - messages are sent daily"
                    elif language == "ru":
                        text += f"\n\n🔸 **Дни не выбраны** - сообщения отправляются ежедневно"
                    elif language == "uz":
                        text += f"\n\n🔸 **Kunlar tanlanmagan** - xabarlar har kuni yuboriladi"
                    elif language == "kz":
                        text += f"\n\n🔸 **Күндер таңдалмаған** - хабарлар күн сайын жіберіледі"
                
                keyboard = self._create_skip_days_keyboard(language, current_skip_days, add_back_button=True)
                
                await query.edit_message_text(
                    text, 
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in change callback for user {chat_id}: {e}")
            await query.edit_message_text(self._get_text("error", language))
    
    async def _handle_change_timezone_input(self, update: Update, timezone_str: str, language: str) -> None:
        """Handle timezone change input."""
        chat_id = update.effective_chat.id
        user_state = self.user_states[chat_id]
        message_id = user_state.get("settings_message_id")
        
        if not is_valid_timezone(timezone_str):
            if message_id:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=self._get_text("invalid_timezone", language),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(self._get_text("invalid_timezone", language), parse_mode='Markdown')
            return
        
        try:
            user = await self.storage.get_user(chat_id)
            if user:
                user.timezone = timezone_str
                success = await self.storage.save_user(user)
                
                if success:
                    # Reschedule user messages with new timezone
                    await self.scheduler.schedule_user_immediately(chat_id)
                    
                    # Clean up state and show menu
                    del self.user_states[chat_id]
                    
                    text = f"{self._get_text('timezone_saved', language)}\n\n{self._get_text('menu', language)}"
                    keyboard = self._create_main_menu_keyboard(language)
                    
                    if message_id:
                        await self.application.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
                else:
                    error_text = self._get_text("setup_error", language)
                    if message_id:
                        await self.application.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=error_text,
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(error_text)
            else:
                error_text = self._get_text("not_subscribed_test", language)
                if message_id:
                    await self.application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=error_text,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(error_text)
                
        except Exception as e:
            logger.error(f"Error changing timezone for user {chat_id}: {e}")
            error_text = self._get_text("error", language)
            if message_id:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(error_text)
    
    async def _handle_change_time_input(self, update: Update, time_str: str, language: str) -> None:
        """Handle time change input."""
        chat_id = update.effective_chat.id
        user_state = self.user_states[chat_id]
        message_id = user_state.get("settings_message_id")
        
        if not is_valid_time_format(time_str):
            if message_id:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=self._get_text("invalid_time", language),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(self._get_text("invalid_time", language))
            return
        
        try:
            user = await self.storage.get_user(chat_id)
            if user:
                user.time_for_send = time_str
                success = await self.storage.save_user(user)
                
                if success:
                    # Reschedule user messages with new time
                    await self.scheduler.schedule_user_immediately(chat_id)
                    
                    # Clean up state and show menu
                    del self.user_states[chat_id]
                    
                    text = f"{self._get_text('time_saved', language)}\n\n{self._get_text('menu', language)}"
                    keyboard = self._create_main_menu_keyboard(language)
                    
                    if message_id:
                        await self.application.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
                else:
                    error_text = self._get_text("setup_error", language)
                    if message_id:
                        await self.application.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=error_text,
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(error_text)
            else:
                error_text = self._get_text("not_subscribed_test", language)
                if message_id:
                    await self.application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=error_text,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(error_text)
                
        except Exception as e:
            logger.error(f"Error changing time for user {chat_id}: {e}")
            error_text = self._get_text("error", language)
            if message_id:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(error_text)
    

    
    async def _delete_message_safe(self, chat_id: int, message_id: int) -> bool:
        """Safely delete a message without raising errors."""
        try:
            await self.application.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except Exception as e:
            logger.debug(f"Could not delete message {message_id} in chat {chat_id}: {e}")
            return False
    
    async def _delete_user_message_delayed(self, chat_id: int, message_id: int, delay: float = 0.5) -> None:
        """Delete user message with a small delay for better UX."""
        try:
            await asyncio.sleep(delay)
            await self._delete_message_safe(chat_id, message_id)
        except Exception as e:
            logger.debug(f"Error deleting user message {message_id} in chat {chat_id}: {e}")
    
    async def _send_and_store_message(self, chat_id: int, text: str, message_type: str = "general", **kwargs) -> Optional[int]:
        """Send message and store its ID for dialog cleanup."""
        try:
            message = await self.application.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            await self.storage.add_bot_message(chat_id, message.message_id, message_type)
            return message.message_id
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return None
    
    async def _reply_and_store_message(self, update: Update, text: str, message_type: str = "general", **kwargs) -> Optional[int]:
        """Reply to message and store its ID for dialog cleanup."""
        try:
            message = await update.message.reply_text(text, **kwargs)
            await self.storage.add_bot_message(update.effective_chat.id, message.message_id, message_type)
            return message.message_id
        except Exception as e:
            logger.error(f"Error replying to message in {update.effective_chat.id}: {e}")
            return None
    
    async def _clear_user_dialog(self, chat_id: int) -> None:
        """Clear user dialog by deleting all stored bot messages."""
        try:
            bot_messages = await self.storage.get_user_bot_messages(chat_id)
            
            deleted_count = 0
            for bot_message in bot_messages:
                success = await self._delete_message_safe(chat_id, bot_message.message_id)
                if success:
                    deleted_count += 1
            
            # Clear stored messages after deletion attempt
            await self.storage.clear_user_bot_messages(chat_id)
            
            logger.info(f"Cleared dialog for user {chat_id}: deleted {deleted_count}/{len(bot_messages)} messages")
            
        except Exception as e:
            logger.error(f"Error clearing dialog for user {chat_id}: {e}")
    
    async def _clear_entire_dialog(self, chat_id: int) -> None:
        """Clear entire dialog by deleting all stored bot messages and attempting to clear more."""
        try:
            # Clear all stored bot messages
            await self._clear_user_dialog(chat_id)
            
            # Try to clear user state and any temporary messages
            if chat_id in self.user_states:
                del self.user_states[chat_id]
            
            logger.info(f"Cleared entire dialog for user {chat_id}")
                
        except Exception as e:
            logger.error(f"Error in clearing entire dialog for user {chat_id}: {e}")
    
    async def _handle_feedback_input(self, update: Update, feedback_text: str, language: str) -> None:
        """Handle feedback input from user."""
        chat_id = update.effective_chat.id
        
        try:
            # Validate feedback length
            if len(feedback_text) > 1000:
                text = self._get_text("feedback_too_long", language)
                keyboard = self._create_main_menu_keyboard(language)
                await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
                del self.user_states[chat_id]
                return
            
            # Check rate limiting
            can_send = await self.storage.can_send_feedback(chat_id, rate_limit_minutes=10)
            if not can_send:
                text = self._get_text("feedback_rate_limit", language)
                keyboard = self._create_main_menu_keyboard(language)
                await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
                del self.user_states[chat_id]
                return
            
            # Get user info
            user = await self.storage.get_user(chat_id)
            username = update.message.from_user.username or f"user_{chat_id}"
            
            # Create feedback object
            from datetime import datetime, timezone
            import uuid
            
            feedback = Feedback(
                id=str(uuid.uuid4())[:8],
                chat_id=chat_id,
                username=username,
                language=language,
                message=feedback_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                message_length=len(feedback_text)
            )
            
            # Save feedback
            success = await self.storage.add_feedback(feedback)
            
            # Clean up state
            del self.user_states[chat_id]
            
            if success:
                text = f"{self._get_text('feedback_sent', language)}\n\n{self._get_text('menu', language)}"
                
                # Notify admins about new feedback
                admin_text = f"💌 **New Feedback Received**\n\n" \
                           f"👤 User: {chat_id} (@{username})\n" \
                           f"🌐 Language: {language}\n" \
                           f"📏 Length: {len(feedback_text)} chars\n" \
                           f"💬 Message: {feedback_text}"
                
                for admin_id in self.admin_ids:
                    try:
                        await self.application.bot.send_message(admin_id, admin_text, parse_mode='Markdown')
                    except Exception:
                        pass  # Ignore errors for admin notifications
            else:
                text = f"{self._get_text('feedback_error', language)}\n\n{self._get_text('menu', language)}"
            
            keyboard = self._create_main_menu_keyboard(language)
            message = await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
            
            # Delete the previous bot message (feedback prompt) for clean dialog
            if update.message.reply_to_message:
                await self._delete_message_safe(chat_id, update.message.reply_to_message.message_id)
                
        except Exception as e:
            logger.error(f"Error handling feedback from user {chat_id}: {e}")
            del self.user_states[chat_id]
            text = f"{self._get_text('error', language)}\n\n{self._get_text('menu', language)}"
            keyboard = self._create_main_menu_keyboard(language)
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    
    async def _handle_feedback_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /feedback_stats command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        # Check if update has message
        if not update.message:
            logger.warning("feedback_stats called without message")
            return
        
        try:
            stats = await self.storage.get_feedback_stats()
            
            # Format language statistics
            lang_stats = []
            for lang, count in stats["by_language"].items():
                lang_stats.append(f"  • {lang}: {count}")
            
            lang_text = "\n".join(lang_stats) if lang_stats else "  No data"
            
            text = self._get_admin_text(
                "feedback_stats",
                total_feedback=stats["total_feedback"],
                average_length=stats["average_length"],
                file_size_mb=stats["file_size_mb"],
                by_language=lang_text
            )
            
            # Send without Markdown to avoid parsing errors
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Error in feedback_stats handler: {e}")
            try:
                await update.message.reply_text("Error getting feedback statistics.")
            except:
                logger.error(f"Could not send error message to {chat_id}")
    
    async def _handle_feedback_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /feedback_list command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        # Check if update has message
        if not update.message:
            logger.warning("feedback_list called without message")
            return
        
        try:
            # Parse limit argument
            limit = 10
            if context.args:
                try:
                    limit = int(context.args[0])
                    limit = max(1, min(limit, 50))  # Clamp between 1 and 50
                except ValueError:
                    await update.message.reply_text(self._get_admin_text("feedback_list_usage"))
                    return
            
            # Get feedback
            feedback_list = await self.storage.get_all_feedback(limit=limit)
            
            if not feedback_list:
                await update.message.reply_text(self._get_admin_text("no_feedback"))
                return
            
            # Format feedback list
            message_parts = [self._get_admin_text("feedback_list_header", count=len(feedback_list))]
            
            for feedback in feedback_list:
                # Truncate long messages and escape special characters
                message_text = feedback.message
                if len(message_text) > 100:
                    message_text = message_text[:97] + "..."
                
                # No need to escape since we're not using Markdown
                safe_message = message_text
                safe_username = feedback.username
                
                item_text = self._get_admin_text(
                    "feedback_item",
                    id=feedback.id,
                    timestamp=feedback.timestamp[:16],  # YYYY-MM-DD HH:MM
                    chat_id=feedback.chat_id,
                    username=safe_username,
                    language=feedback.language,
                    length=feedback.message_length,
                    message=safe_message
                )
                message_parts.append(item_text)
            
            full_message = "".join(message_parts)
            
            # Split message if too long and send without Markdown to avoid parsing errors
            if len(full_message) > 4000:
                for i in range(0, len(full_message), 4000):
                    chunk = full_message[i:i+4000]
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(full_message)
            
        except Exception as e:
            logger.error(f"Error in feedback_list handler: {e}")
            try:
                await update.message.reply_text("Error getting feedback list.")
            except:
                logger.error(f"Could not send error message to {chat_id}")
    

    
    async def _handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        # Check if update has message
        if not update.message:
            logger.warning("admin called without message")
            return
        
        try:
            text = self._get_admin_text("admin_help")
            # Send without Markdown to avoid parsing errors
            await update.message.reply_text(text)
            
        except Exception as e:
            logger.error(f"Error in admin handler: {e}")
            try:
                await update.message.reply_text("Error showing admin help.")
            except:
                logger.error(f"Could not send error message to {chat_id}")