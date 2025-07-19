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
            "Please specify your time zone in IANA format:\n\n"
            "Popular options:\n"
            "• `Europe/Moscow` - Moscow\n"
            "• `Asia/Tashkent` - Tashkent\n"
            "• `Europe/Kiev` - Kiev\n"
            "• `Asia/Almaty` - Almaty\n"
            "• `UTC` - UTC time"
        ),
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
            "Укажите ваш часовой пояс в формате IANA:\n\n"
            "Популярные варианты:\n"
            "• `Europe/Moscow` - Москва\n"
            "• `Asia/Tashkent` - Ташкент\n"
            "• `Europe/Kiev` - Киев\n"
            "• `Asia/Almaty` - Алматы\n"
            "• `UTC` - UTC время"
        ),
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
    }
}

# Admin texts (always in English)
ADMIN_TEXTS = {
    "next_principle": "📋 **Random principle for user {user_id}:**\n\n{principle}\n\n💡 *Principles are chosen randomly for each user*",
    "no_principles": "No available principles for user {user_id}.",
    "add_usage": "Usage: /add <principle text>",
    "add_empty": "Principle text cannot be empty.",
    "add_success": "✅ Principle '{name}' successfully added!",
    "add_error": "❌ Error adding principle.",
    "stats": (
        "📊 **Bot Statistics:**\n\n"
        "👥 Total users: {total_users}\n"
        "✅ Active: {active_users}\n"
        "📨 Messages sent: {total_messages_sent}\n\n"
        "⏰ **Scheduler:**\n"
        "🔄 Scheduled jobs: {total_jobs}\n"
        "🎯 Jobs created: {jobs_created}\n"
        "🚀 Status: {status}"
    ),
    "broadcast_usage": "Usage: /broadcast <message>",
    "broadcast_empty": "Message text cannot be empty.",
    "broadcast_start": "📢 Starting broadcast to {count} users...",
    "broadcast_result": (
        "📢 **Broadcast Results:**\n\n"
        "✅ Sent: {sent}\n"
        "❌ Errors: {failed}\n"
        "👥 Total: {total}"
    ),
    "feedback_stats": (
        "💌 **Feedback Statistics:**\n\n"
        "📝 Total feedback: {total_feedback}\n"
        "📏 Average length: {average_length} chars\n"
        "💾 File size: {file_size_mb} MB\n\n"
        "🌐 **By Language:**\n{by_language}\n\n"
        "Use /feedback_list to see recent feedback"
    ),
    "feedback_list_header": "💌 **Recent Feedback ({count} items):**\n\n",
    "feedback_item": (
        "**#{id}** | {timestamp}\n"
        "👤 User: {chat_id} (@{username})\n"
        "🌐 Lang: {language} | 📏 {length} chars\n"
        "💬 {message}\n"
        "─────────────────\n"
    ),
    "no_feedback": "No feedback received yet.",
    "feedback_list_usage": "Usage: /feedback_list [limit] (default: 10, max: 50)",
    "admin_help": (
        "🔧 **Admin Commands:**\n\n"
        "📊 **Statistics:**\n"
        "• `stats` - Bot usage statistics\n"
        "• `feedback_stats` - Feedback statistics\n"
        "• `feedback_list [limit]` - View recent feedback\n\n"
        "📨 **Messages:**\n"
        "• `next` - Show random principle for user\n"
        "• `broadcast <message>` - Send message to all users\n\n"
        "🛠️ **Management:**\n"
        "• `add <text>` - Add new principle (not implemented)\n\n"
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
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show welcome message in both languages.
            welcome_en = TEXTS["en"]["welcome"] + "\n\n" + TEXTS["en"]["choose_language"]
            welcome_ru = "\n\n" + TEXTS["ru"]["welcome"] + "\n\n" + TEXTS["ru"]["choose_language"]
            
            combined_welcome = welcome_en + welcome_ru
            
            message = await update.message.reply_text(combined_welcome, reply_markup=reply_markup, parse_mode='Markdown')
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
            
            # Check if user already exists (changing language) or new registration
            user = await self.storage.get_user(chat_id)
            
            if user and user.is_active:
                # User exists - changing language
                user.language = language
                success = await self.storage.save_user(user)
                
                if success:
                    confirmation = self._get_text("language_chosen", language)
                    text = f"{confirmation}\n\n{self._get_text('menu', language)}"
                    keyboard = self._create_main_menu_keyboard(language)
                    message = await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                    if message:
                        await self.storage.add_bot_message(chat_id, message.message_id, "menu")
                else:
                    await query.edit_message_text(self._get_text("setup_error", language))
            else:
                # New user registration
                self.user_states[chat_id] = {
                    "step": "timezone",
                    "language": language,
                    "registration_message_id": query.message.message_id  # Save message ID for editing
                }
                
                # Send language confirmation and timezone step.
                confirmation = self._get_text("language_chosen", language)
                timezone_msg = self._get_text("timezone_step", language)
                
                combined_msg = f"{confirmation}\n\n{timezone_msg}"
                
                await query.edit_message_text(combined_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in language callback for user {chat_id}: {e}")
            await query.edit_message_text(self._get_text("error", language))
    
    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command."""
        chat_id = update.effective_chat.id
        
        try:
            # Delete user's /stop command message
            await self._delete_message_safe(chat_id, update.message.message_id)
            
            user = await self.storage.get_user(chat_id)
            language = user.language if user else "en"
            
            # Clear dialog - delete all bot messages except the last one we'll send
            await self._clear_user_dialog(chat_id)
            
            success = await self.storage.deactivate_user(chat_id)
            if success:
                text = self._get_text("unsubscribed", language)
                # Remove user from scheduler
                await self.scheduler.remove_user_jobs(chat_id)
            else:
                text = self._get_text("not_subscribed", language)
            
            # Send final message (don't store this message ID as it should remain in dialog)
            await update.message.reply_text(text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in stop handler for user {chat_id}: {e}")
            await update.message.reply_text("An error occurred while processing your request.")
    
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command."""
        chat_id = update.effective_chat.id
        
        try:
            user = await self.storage.get_user(chat_id)
            if not user or not user.is_active:
                await update.message.reply_text(self._get_text("not_subscribed_test", language="en"))
                return
            
            language_display = "English" if user.language == "en" else "Русский"
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
            
            success = await self.scheduler.send_test_message(chat_id)
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
        
        try:
            args = context.args
            target_chat_id = int(args[0]) if args else chat_id
            
            principle = await self.scheduler.get_next_principle_for_user(target_chat_id)
            if principle:
                principle_text = format_principle_message(principle)
                message_text = self._get_admin_text("next_principle", user_id=target_chat_id, principle=principle_text)
                await update.message.reply_text(message_text, parse_mode='Markdown')
            else:
                text = self._get_admin_text("no_principles", user_id=target_chat_id)
                await update.message.reply_text(text)
                
        except Exception as e:
            logger.error(f"Error in next handler: {e}")
            await update.message.reply_text("Error getting next principle.")
    
    async def _handle_add_principle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /add command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
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
            await update.message.reply_text(self._get_admin_text("add_error"))
    
    async def _handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
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
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in stats handler: {e}")
            await update.message.reply_text("Error getting statistics.")
    
    async def _handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /broadcast command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
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
                    await context.bot.send_message(user.chat_id, broadcast_text, parse_mode='Markdown')
                    sent_count += 1
                except Exception:
                    failed_count += 1
            
            result_text = self._get_admin_text(
                "broadcast_result",
                sent=sent_count,
                failed=failed_count,
                total=len(active_users)
            )
            
            await update.message.reply_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in broadcast handler: {e}")
            await update.message.reply_text("Error during broadcast.")
    
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
            
            if step == "timezone":
                await self._handle_timezone_input(update, message_text, language)
            elif step == "time":
                await self._handle_time_input(update, message_text, language)
            elif step == "skip_days":
                await self._handle_skip_days_input(update, message_text, language)
            elif step == "change_timezone":
                await self._handle_change_timezone_input(update, message_text, language)
            elif step == "change_time":
                await self._handle_change_time_input(update, message_text, language)
            elif step == "change_skip_days":
                await self._handle_change_skip_days_input(update, message_text, language)
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
        
        confirmation = self._get_text("time_saved", language)
        skip_days_msg = self._get_text("skip_days_improved", language)
        
        combined_msg = f"{confirmation}\n\n{skip_days_msg}"
        
        if message_id:
            await self.application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=combined_msg,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(combined_msg, parse_mode='Markdown')
    
    async def _handle_skip_days_input(self, update: Update, skip_days_str: str, language: str) -> None:
        """Handle skip days input during registration."""
        chat_id = update.effective_chat.id
        user_state = self.user_states[chat_id]
        message_id = user_state.get("registration_message_id")
        
        skip_days = []
        
        # Parse skip days - improved validation: any non-number input = no skip days
        if skip_days_str.strip():
            try:
                # Try to parse as comma-separated numbers
                skip_days = [int(x.strip()) for x in skip_days_str.split(',') if x.strip()]
                if not validate_skip_days(skip_days):
                    # Invalid numbers, treat as "no skip days"
                    skip_days = []
            except ValueError:
                # Any non-number input means "no skip days"
                skip_days = []
        
        # Create and save user.
        user = User(
            chat_id=chat_id,
            language=language,
            timezone=user_state["timezone"],
            time_for_send=user_state["time"],
            skip_day_id=skip_days,
            is_active=True
        )
        
        success = await self.storage.save_user(user)
        if success:
            # Schedule user messages.
            await self.scheduler.schedule_user_immediately(chat_id)
            
            # Clean up state.
            del self.user_states[chat_id]
            
            skip_days_display = self._format_skip_days(skip_days, language)
            
            text = self._get_text(
                "setup_complete",
                language,
                time=user.time_for_send,
                timezone=user.timezone,
                skip_days=skip_days_display
            )
            
            # Add menu after setup completion
            text += f"\n\n{self._get_text('menu', language)}"
            keyboard = self._create_main_menu_keyboard(language)
            
            if message_id:
                await self.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                # Store the final message ID
                await self.storage.add_bot_message(chat_id, message_id, "setup_complete")
            else:
                message = await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
                await self.storage.add_bot_message(chat_id, message.message_id, "setup_complete")
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
            
            del self.user_states[chat_id]
    
    def _format_skip_days(self, skip_days: List[int], language: str) -> str:
        """Format skip days for display."""
        if not skip_days:
            return "Нет" if language == "ru" else "None"
        
        if language == "ru":
            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        else:
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        return ", ".join([day_names[day] for day in skip_days])
    
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
                await query.edit_message_text("🧪 Sending test message...")
                success = await self.scheduler.send_test_message(chat_id)
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
                keyboard = [[InlineKeyboardButton(self._get_text("back_to_menu", language), callback_data="settings_back")]]
                await query.edit_message_text(
                    self._get_text("timezone_step", language), 
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
            elif setting == "skip_days":
                self.user_states[chat_id] = {"step": "change_skip_days", "language": language, "settings_message_id": query.message.message_id}
                keyboard = [[InlineKeyboardButton(self._get_text("back_to_menu", language), callback_data="settings_back")]]
                await query.edit_message_text(
                    self._get_text("skip_days_improved", language), 
                    reply_markup=InlineKeyboardMarkup(keyboard),
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
    
    async def _handle_change_skip_days_input(self, update: Update, skip_days_str: str, language: str) -> None:
        """Handle skip days change input."""
        chat_id = update.effective_chat.id
        user_state = self.user_states[chat_id]
        message_id = user_state.get("settings_message_id")
        
        skip_days = []
        
        # Parse skip days - improved validation: any non-number input = no skip days
        if skip_days_str.strip():
            try:
                # Try to parse as comma-separated numbers
                skip_days = [int(x.strip()) for x in skip_days_str.split(',') if x.strip()]
                if not validate_skip_days(skip_days):
                    # Invalid numbers, treat as "no skip days"
                    skip_days = []
            except ValueError:
                # Any non-number input means "no skip days"
                skip_days = []
        
        try:
            user = await self.storage.get_user(chat_id)
            if user:
                user.skip_day_id = skip_days
                success = await self.storage.save_user(user)
                
                if success:
                    # Reschedule user messages with new skip days
                    await self.scheduler.schedule_user_immediately(chat_id)
                    
                    # Clean up state and show menu
                    del self.user_states[chat_id]
                    
                    if skip_days:
                        skip_days_display = self._format_skip_days(skip_days, language)
                        confirmation = f"✅ {skip_days_display}"
                    else:
                        confirmation = self._get_text("no_skip_days", language)
                    
                    text = f"{confirmation}\n\n{self._get_text('menu', language)}"
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
            logger.error(f"Error changing skip days for user {chat_id}: {e}")
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
            from datetime import datetime
            import uuid
            
            feedback = Feedback(
                id=str(uuid.uuid4())[:8],
                chat_id=chat_id,
                username=username,
                language=language,
                message=feedback_text,
                timestamp=datetime.utcnow().isoformat(),
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
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in feedback_stats handler: {e}")
            await update.message.reply_text("Error getting feedback statistics.")
    
    async def _handle_feedback_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /feedback_list command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
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
                # Truncate long messages
                message_text = feedback.message
                if len(message_text) > 100:
                    message_text = message_text[:97] + "..."
                
                item_text = self._get_admin_text(
                    "feedback_item",
                    id=feedback.id,
                    timestamp=feedback.timestamp[:16],  # YYYY-MM-DD HH:MM
                    chat_id=feedback.chat_id,
                    username=feedback.username,
                    language=feedback.language,
                    length=feedback.message_length,
                    message=message_text
                )
                message_parts.append(item_text)
            
            full_message = "".join(message_parts)
            
            # Split message if too long
            if len(full_message) > 4000:
                for i in range(0, len(full_message), 4000):
                    chunk = full_message[i:i+4000]
                    await update.message.reply_text(chunk, parse_mode='Markdown')
            else:
                await update.message.reply_text(full_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in feedback_list handler: {e}")
            await update.message.reply_text("Error getting feedback list.")
    
    async def _handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin command (admin only)."""
        chat_id = update.effective_chat.id
        
        if chat_id not in self.admin_ids:
            return
        
        try:
            text = self._get_admin_text("admin_help")
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in admin handler: {e}")
            await update.message.reply_text("Error showing admin help.")