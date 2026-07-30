"""Scheduler for yoga bot daily messages."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, Forbidden, BadRequest, NetworkError

from .storage import JsonStorage, User, BotMessage
from .utils import (
    PrinciplesManager,
    MeridiansManager,
    format_principle_message,
    format_meridian_intro,
    format_meridian_point,
    fit_html_caption,
    get_next_send_time,
    get_principle_image_path,
    get_meridian_image_path,
    has_principle_image
)


logger = logging.getLogger(__name__)


class YogaScheduler:
    """Scheduler for yoga bot messages."""
    
    def __init__(self, bot: Bot, storage: JsonStorage, principles_manager: PrinciplesManager, meridians_manager: MeridiansManager = None):
        self.bot = bot
        self.storage = storage
        self.principles_manager = principles_manager
        self.meridians_manager = meridians_manager
        self.scheduler = AsyncIOScheduler(timezone='UTC')
        self.jobs_created = 0

    def _meridian_button_text(self, key: str, language: str) -> str:
        """Return localized labels for meridian reminder buttons."""
        labels = {
            "en": {
                "start": "Start with point 1",
                "prev": "Previous point",
                "next": "Next point",
                "video": "🎥 Meridian video",
                "all": "All points",
                "help": "🖐 How to find a point",
                "complete": "✅ Meridian studied / next",
                "back": "🔙 Back to meridians",
            },
            "ru": {
                "start": "Начать с первой точки",
                "prev": "Предыдущая точка",
                "next": "Следующая точка",
                "video": "🎥 Видео меридиана",
                "all": "Все точки",
                "help": "🖐 Как искать точку",
                "complete": "✅ Меридиан изучен / дальше",
                "back": "🔙 К меридианам",
            },
            "uz": {
                "start": "1-nuqtadan boshlash",
                "prev": "Oldingi nuqta",
                "next": "Keyingi nuqta",
                "video": "🎥 Meridian videosi",
                "all": "Barcha nuqtalar",
                "help": "🖐 Nuqtani topish",
                "complete": "✅ Meridian o‘rganildi / keyingisi",
                "back": "🔙 Meridianlarga qaytish",
            },
            "kz": {
                "start": "1-нүктеден бастау",
                "prev": "Алдыңғы нүкте",
                "next": "Келесі нүкте",
                "video": "🎥 Меридиан видеосы",
                "all": "Барлық нүктелер",
                "help": "🖐 Нүктені табу",
                "complete": "✅ Меридиан зерттелді / келесі",
                "back": "🔙 Меридиандарға қайту",
            },
        }
        language_labels = labels.get(language, labels["en"])
        return language_labels.get(key, labels["en"][key])

    def _create_meridian_reminder_keyboard(
        self,
        language: str,
        point_index: int,
        points_count: int,
        meridian_id: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """Create inline navigation for daily meridian reminder messages."""
        keyboard = []

        if point_index < 0:
            start_callback = (
                f"meridian_point:{meridian_id}:0"
                if meridian_id
                else "meridian_next"
            )
            keyboard.append([
                InlineKeyboardButton(self._meridian_button_text("start", language), callback_data=start_callback)
            ])
        else:
            navigation_row = []
            point_prefix = f"meridian_point:{meridian_id}:" if meridian_id else "meridian_point:"
            if point_index > 0:
                navigation_row.append(
                    InlineKeyboardButton(
                        self._meridian_button_text("prev", language),
                        callback_data=f"{point_prefix}{point_index - 1}"
                    )
                )
            if point_index < points_count - 1:
                navigation_row.append(
                    InlineKeyboardButton(
                        self._meridian_button_text("next", language),
                        callback_data=f"{point_prefix}{point_index + 1}"
                    )
                )
            if navigation_row:
                keyboard.append(navigation_row)

        keyboard.extend([
            [InlineKeyboardButton(self._meridian_button_text("video", language), callback_data="meridian_video")],
            [
                InlineKeyboardButton(self._meridian_button_text("all", language), callback_data="meridian_all"),
                InlineKeyboardButton(self._meridian_button_text("help", language), callback_data="meridian_point_help"),
            ],
            [InlineKeyboardButton(self._meridian_button_text("complete", language), callback_data="meridian_complete")],
            [InlineKeyboardButton(self._meridian_button_text("back", language), callback_data="meridian_main")],
        ])
        return InlineKeyboardMarkup(keyboard)

    def _is_guided_meridian_route_completed(self, user: User) -> bool:
        """Return True when the guided meridian route is finished and waiting for an explicit restart."""
        if (
            not self.meridians_manager
            or user.meridian_learning_mode != "guided"
            or user.current_meridian_id
        ):
            return False

        meridians = self.meridians_manager.get_recommended_path_meridians()
        meridian_ids = [item.get("id") for item in meridians if item.get("id")]
        if not meridian_ids:
            return False

        completed_ids = set(user.completed_meridians or [])
        return all(meridian_id in completed_ids for meridian_id in meridian_ids)
        
    async def start(self) -> None:
        """Start the scheduler."""
        logger.info("Starting yoga scheduler...")
        self.scheduler.start()
        
        # Schedule daily check for all users at 00:01 UTC.
        self.scheduler.add_job(
            self._schedule_all_users,
            CronTrigger(hour=0, minute=1),
            id="daily_schedule_all_users",
            replace_existing=True
        )
        
        # Initial scheduling for all users.
        await self._schedule_all_users()
        
        logger.info("Yoga scheduler started successfully.")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        logger.info("Stopping yoga scheduler...")
        self.scheduler.shutdown()
        logger.info("Yoga scheduler stopped.")
    
    async def _schedule_all_users(self) -> None:
        """Schedule messages for all active users."""
        logger.info("Scheduling messages for all active users...")
        
        active_users = await self.storage.get_all_active_users()
        logger.info(f"Found {len(active_users)} active users.")
        
        for user in active_users:
            await self._schedule_user_jobs(user)
    
    async def _schedule_user_jobs(self, user: User) -> None:
        """Schedule enabled practice messages for a specific user."""
        await self._schedule_user_message(user)
        await self._schedule_user_meridian_message(user)

    async def _schedule_user_message(self, user: User) -> None:
        """Schedule next principle message for specific user."""
        try:
            existing_jobs = [job for job in self.scheduler.get_jobs() if job.id.startswith(f"principle_user_{user.chat_id}_")]
            for job in existing_jobs:
                self.scheduler.remove_job(job.id)

            if not user.principles_enabled:
                return

            # Calculate next send time.
            next_send_time = get_next_send_time(
                user.timezone,
                user.time_for_send,
                user.skip_day_id
            )
            
            # Convert to UTC for scheduler.
            next_send_time_utc = next_send_time.astimezone(timezone.utc).replace(tzinfo=None)
            
            # Create unique job ID.
            job_id = f"principle_user_{user.chat_id}_{next_send_time_utc.strftime('%Y%m%d_%H%M')}"
            
            # Schedule new job.
            self.scheduler.add_job(
                self._send_principle_to_user,
                DateTrigger(run_date=next_send_time_utc),
                args=[user.chat_id],
                id=job_id,
                replace_existing=True
            )
            
            self.jobs_created += 1
            logger.info(f"Scheduled message for user {user.chat_id} at {next_send_time_utc} UTC")
            
        except Exception as e:
            logger.error(f"Error scheduling message for user {user.chat_id}: {e}")

    async def _schedule_user_meridian_message(self, user: User) -> None:
        """Schedule next meridian reminder for a specific user."""
        try:
            existing_jobs = [job for job in self.scheduler.get_jobs() if job.id.startswith(f"meridian_user_{user.chat_id}_")]
            for job in existing_jobs:
                self.scheduler.remove_job(job.id)

            if not user.meridians_enabled or not user.meridian_learning_mode:
                return
            if self._is_guided_meridian_route_completed(user):
                logger.info(f"Guided meridian route is completed for user {user.chat_id}; reminder is not scheduled.")
                return

            next_send_time = get_next_send_time(
                user.timezone,
                user.meridian_time_for_send,
                user.skip_day_id
            )
            next_send_time_utc = next_send_time.astimezone(timezone.utc).replace(tzinfo=None)
            job_id = f"meridian_user_{user.chat_id}_{next_send_time_utc.strftime('%Y%m%d_%H%M')}"

            self.scheduler.add_job(
                self._send_meridian_to_user,
                DateTrigger(run_date=next_send_time_utc),
                args=[user.chat_id],
                id=job_id,
                replace_existing=True
            )

            self.jobs_created += 1
            logger.info(f"Scheduled meridian reminder for user {user.chat_id} at {next_send_time_utc} UTC")

        except Exception as e:
            logger.error(f"Error scheduling meridian reminder for user {user.chat_id}: {e}")
    
    async def _send_principle_to_user(self, chat_id: int) -> bool:
        """Send principle message to user."""
        try:
            logger.info(f"Sending principle to user {chat_id}...")
            
            # Get user data.
            user = await self.storage.get_user(chat_id)
            if not user or not user.is_active or not user.principles_enabled:
                logger.warning(f"User {chat_id} not found, inactive, or principle practice is disabled.")
                return False
            
            # Get completely random principle for this user in their language.
            principle = self.principles_manager.get_random_principle(user.language)
            if not principle:
                logger.warning(f"No principles available for user {chat_id} in language {user.language}.")
                return False
            
            # Format message.
            message_text = format_principle_message(principle, user.language)
            
            # Send message with retry logic.
            success = await self._send_message_with_retry(chat_id, message_text, principle_id=principle["id"])
            
            if success:
                # Log sent message.
                await self.storage.add_sent_log(chat_id, principle["id"])
                logger.info(f"Successfully sent principle {principle['id']} to user {chat_id}.")
            else:
                logger.error(f"Failed to send message to user {chat_id}.")

            # Always schedule the next message for active users. A temporary
            # Telegram timeout should not break the daily delivery chain.
            current_user = await self.storage.get_user(chat_id)
            if current_user and current_user.is_active and current_user.principles_enabled:
                await self._schedule_user_message(current_user)
            return success

        except Exception as e:
            logger.error(f"Error sending principle to user {chat_id}: {e}")
            return False

    async def _send_meridian_to_user(self, chat_id: int) -> bool:
        """Send current meridian focus to user without advancing progress."""
        try:
            logger.info(f"Sending meridian focus to user {chat_id}...")
            user = await self.storage.get_user(chat_id)
            if not user or not user.is_active or not user.meridians_enabled or not user.meridian_learning_mode:
                return False
            if not self.meridians_manager:
                logger.warning("Meridians manager is not configured.")
                return False
            if self._is_guided_meridian_route_completed(user):
                logger.info(f"Guided meridian route is completed for user {chat_id}; reminder is skipped.")
                return False

            meridian = self.meridians_manager.get_meridian_by_id(user.current_meridian_id) if user.current_meridian_id else None
            if not meridian:
                meridian = self.meridians_manager.get_first_meridian()
                if not meridian:
                    return False
                user.current_meridian_id = meridian["id"]
                user.current_point_index = -1
                await self.storage.save_user(user)

            points = meridian.get("points", [])
            if user.current_point_index < -1 or user.current_point_index >= len(points):
                user.current_point_index = -1
                await self.storage.save_user(user)

            if user.current_point_index >= 0:
                message_text = format_meridian_point(meridian, user.current_point_index, user.language)
                point_code = points[user.current_point_index].get("code") if user.current_point_index < len(points) else None
                image_path = get_meridian_image_path(meridian["id"], point_code)
            else:
                message_text = format_meridian_intro(meridian, user.language)
                image_path = get_meridian_image_path(meridian["id"])

            keyboard = self._create_meridian_reminder_keyboard(
                user.language, user.current_point_index, len(points), meridian.get("id")
            )
            success = await self._send_meridian_message_with_retry(chat_id, message_text, image_path, keyboard)

            current_user = await self.storage.get_user(chat_id)
            if current_user and current_user.is_active and current_user.meridians_enabled:
                await self._schedule_user_meridian_message(current_user)
            return success

        except Exception as e:
            logger.error(f"Error sending meridian focus to user {chat_id}: {e}")
            return False

    async def resend_daily_reminders_to_all(self) -> tuple[int, int, int]:
        """Resend enabled daily practices to every active user."""
        active_users = await self.storage.get_all_active_users()
        reached_users = 0
        failed_users = 0
        deliveries = 0

        for user in active_users:
            attempted = 0
            successful = 0

            if user.principles_enabled:
                attempted += 1
                if await self._send_principle_to_user(user.chat_id):
                    successful += 1

            if user.meridians_enabled and user.meridian_learning_mode:
                attempted += 1
                if await self._send_meridian_to_user(user.chat_id):
                    successful += 1

            deliveries += successful
            if successful:
                reached_users += 1
            if attempted and successful < attempted:
                failed_users += 1

        return reached_users, failed_users, deliveries

    async def _send_meridian_message_with_retry(
        self,
        chat_id: int,
        message: str,
        image_path: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        max_retries: int = 3
    ) -> bool:
        """Send meridian message with optional image."""
        for attempt in range(max_retries):
            try:
                sent_message = None
                if image_path:
                    caption = fit_html_caption(message)
                    try:
                        with open(image_path, 'rb') as media_file:
                            if image_path.lower().endswith(".gif"):
                                sent_message = await self.bot.send_animation(
                                    chat_id=chat_id,
                                    animation=media_file,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    parse_mode='HTML'
                                )
                            else:
                                sent_message = await self.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=media_file,
                                    caption=caption,
                                    reply_markup=reply_markup,
                                    parse_mode='HTML'
                                )
                    except NetworkError:
                        raise
                    except Exception as img_error:
                        logger.error(f"Error sending meridian image {image_path}: {img_error}")
                        sent_message = await self.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                else:
                    sent_message = await self.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )

                if sent_message:
                    await self.storage.add_bot_message(chat_id, sent_message.message_id, "meridian")
                return True

            except Forbidden:
                logger.warning(f"User {chat_id} blocked the bot, deactivating.")
                await self.storage.deactivate_user(chat_id)
                return False
            except BadRequest as e:
                logger.error(f"Bad request for user {chat_id}: {e}")
                return False
            except NetworkError as e:
                logger.warning(f"Telegram network error for user {chat_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except TelegramError as e:
                logger.error(f"Telegram error for user {chat_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for meridian message to user {chat_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        return False
    
    async def _send_message_with_retry(self, chat_id: int, message: str, max_retries: int = 3, principle_id: Optional[int] = None) -> bool:
        """Send message with retry logic for error handling."""
        for attempt in range(max_retries):
            try:
                sent_message = None
                message_type = "principle" if principle_id else "general"
                
                # Check if principle has an image
                if principle_id:
                    logger.info(f"Checking for image for principle ID: {principle_id}")
                    has_image = has_principle_image(principle_id)
                    logger.info(f"Has image for principle {principle_id}: {has_image}")
                    
                    if has_image:
                        image_path = get_principle_image_path(principle_id)
                        logger.info(f"Image path for principle {principle_id}: {image_path}")
                        
                        if image_path:
                            try:
                                # Send image with caption
                                logger.info(f"Attempting to send image: {image_path}")
                                with open(image_path, 'rb') as photo:
                                    sent_message = await self.bot.send_photo(
                                        chat_id=chat_id, 
                                        photo=photo, 
                                        caption=message, 
                                        parse_mode='HTML'
                                    )
                                logger.info(f"Successfully sent image for principle {principle_id}")
                            except NetworkError:
                                raise
                            except Exception as img_error:
                                logger.error(f"Error sending image {image_path}: {img_error}")
                                # Fallback to text message
                                sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                                logger.info("Sent fallback text message")
                        else:
                            logger.warning(f"Image path is None for principle {principle_id}")
                            # Fallback to text message
                            sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                    else:
                        logger.info(f"No image found for principle {principle_id}, sending text only")
                        # Send text message
                        sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                else:
                    logger.info("No principle_id provided, sending text message")
                    # Send text message
                    sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                
                # Store message ID for dialog cleanup
                if sent_message:
                    await self.storage.add_bot_message(chat_id, sent_message.message_id, message_type)
                
                return True
                
            except Forbidden:
                logger.warning(f"User {chat_id} blocked the bot, deactivating.")
                await self.storage.deactivate_user(chat_id)
                return False
                
            except BadRequest as e:
                logger.error(f"Bad request for user {chat_id}: {e}")
                return False
            except NetworkError as e:
                logger.warning(f"Telegram network error for user {chat_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff.

            except TelegramError as e:
                logger.error(f"Telegram error for user {chat_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff.
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for user {chat_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff.
                
        return False
    
    async def schedule_user_immediately(self, chat_id: int) -> None:
        """Schedule user for immediate message delivery (for testing)."""
        user = await self.storage.get_user(chat_id)
        if user:
            await self._schedule_user_jobs(user)
    
    async def send_reminder_check_message(self, chat_id: int, language: str = None) -> bool:
        """Send a reminder check message to user."""
        try:
            # Get user to determine language if not provided.
            user = await self.storage.get_user(chat_id)
            if language is None:
                language = user.language if user else "en"
            
            # Get completely random principle.
            principle = self.principles_manager.get_random_principle(language)
            
            if not principle:
                return False
            
            # Reminder check in user's language.
            test_prefixes = {
                "en": "🧪 <b>Reminder check</b>\n\n",
                "ru": "🧪 <b>Проверка напоминания</b>\n\n",
                "uz": "🧪 <b>Eslatmani tekshirish</b>\n\n",
                "kz": "🧪 <b>Еске салуды тексеру</b>\n\n"
            }
            test_prefix = test_prefixes.get(language, test_prefixes["en"])

            message_text = f"{test_prefix}{format_principle_message(principle, language, max_length=1024 - len(test_prefix))}"
            
            return await self._send_message_with_retry(chat_id, message_text, principle_id=principle["id"])
            
        except Exception as e:
            logger.error(f"Error sending reminder check message to user {chat_id}: {e}")
            return False

    async def send_test_message(self, chat_id: int, language: str = None) -> bool:
        """Backward-compatible alias for older handler code."""
        return await self.send_reminder_check_message(chat_id, language)

    async def send_full_reminder_check_message(self, chat_id: int, language: str = None) -> bool:
        """Send reminder checks for every active practice mode."""
        try:
            user = await self.storage.get_user(chat_id)
            if language is None:
                language = user.language if user else "en"

            sent_any = False
            should_send_principle = not user or getattr(user, "principles_enabled", True)
            should_send_meridian = bool(
                user
                and getattr(user, "meridians_enabled", False)
                and getattr(user, "meridian_learning_mode", None)
            )

            if should_send_principle:
                sent_any = await self._send_principle_reminder_check(chat_id, language) or sent_any

            if should_send_meridian:
                sent_any = await self._send_meridian_reminder_check(user, language) or sent_any

            return sent_any
        except Exception as e:
            logger.error(f"Error sending full reminder check message to user {chat_id}: {e}")
            return False

    async def _send_principle_reminder_check(self, chat_id: int, language: str) -> bool:
        """Send a Yama/Niyama reminder check."""
        principle = self.principles_manager.get_random_principle(language)
        if not principle:
            return False

        prefixes = {
            "en": "🧪 <b>Reminder check: Yama/Niyama</b>\n\n",
            "ru": "🧪 <b>Проверка напоминания: Яма/Нияма</b>\n\n",
            "uz": "🧪 <b>Eslatma tekshiruvi: Yama/Niyama</b>\n\n",
            "kz": "🧪 <b>Еске салуды тексеру: Яма/Нияма</b>\n\n",
        }
        prefix = prefixes.get(language, prefixes["en"])
        message_text = f"{prefix}{format_principle_message(principle, language, max_length=1024 - len(prefix))}"
        return await self._send_message_with_retry(chat_id, message_text, principle_id=principle["id"])

    async def _send_meridian_reminder_check(self, user: User, language: str) -> bool:
        """Send a meridian reminder check without advancing progress."""
        if not self.meridians_manager or self._is_guided_meridian_route_completed(user):
            return False

        meridian = self.meridians_manager.get_meridian_by_id(user.current_meridian_id) if user.current_meridian_id else None
        if not meridian:
            if getattr(user, "meridian_learning_mode", None) == "guided":
                meridian = self.meridians_manager.get_next_meridian(None, user.completed_meridians)
            if not meridian:
                meridian = self.meridians_manager.get_first_meridian()
            if not meridian:
                return False
            user.current_meridian_id = meridian["id"]
            user.current_point_index = -1
            await self.storage.save_user(user)

        points = meridian.get("points", [])
        if user.current_point_index < -1 or user.current_point_index >= len(points):
            user.current_point_index = -1
            await self.storage.save_user(user)

        prefixes = {
            "en": "🧪 <b>Reminder check: Meridians</b>\n\n",
            "ru": "🧪 <b>Проверка напоминания: Меридианы</b>\n\n",
            "uz": "🧪 <b>Eslatma tekshiruvi: Meridianlar</b>\n\n",
            "kz": "🧪 <b>Еске салуды тексеру: Меридиандар</b>\n\n",
        }
        prefix = prefixes.get(language, prefixes["en"])

        if user.current_point_index >= 0:
            message_text = prefix + format_meridian_point(meridian, user.current_point_index, language)
            point_code = points[user.current_point_index].get("code") if user.current_point_index < len(points) else None
            image_path = get_meridian_image_path(meridian["id"], point_code)
        else:
            message_text = prefix + format_meridian_intro(meridian, language)
            image_path = get_meridian_image_path(meridian["id"])

        keyboard = self._create_meridian_reminder_keyboard(
            language, user.current_point_index, len(points), meridian.get("id")
        )
        return await self._send_meridian_message_with_retry(user.chat_id, message_text, image_path, keyboard)
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        jobs = self.scheduler.get_jobs()
        
        return {
            "total_jobs": len(jobs),
            "jobs_created": self.jobs_created,
            "running": self.scheduler.running,
            "next_jobs": [
                {
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs[:5]  # Show first 5 jobs.
            ]
        }
    
    async def get_next_principle_for_user(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get next principle that will be sent to user."""
        user = await self.storage.get_user(chat_id)
        language = user.language if user else "en"
        return self.principles_manager.get_random_principle(language)
    
    async def remove_user_jobs(self, chat_id: int) -> int:
        """Remove all scheduled jobs for a specific user."""
        try:
            existing_jobs = [
                job for job in self.scheduler.get_jobs()
                if job.id.startswith(f"user_{chat_id}_")
                or job.id.startswith(f"principle_user_{chat_id}_")
                or job.id.startswith(f"meridian_user_{chat_id}_")
            ]
            removed_count = 0
            
            for job in existing_jobs:
                self.scheduler.remove_job(job.id)
                removed_count += 1
                logger.info(f"Removed job {job.id} for user {chat_id}")
            
            logger.info(f"Removed {removed_count} jobs for user {chat_id}")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error removing jobs for user {chat_id}: {e}")
            return 0
