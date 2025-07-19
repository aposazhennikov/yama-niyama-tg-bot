"""Scheduler for yoga bot daily messages."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest

from .storage import JsonStorage, User, BotMessage
from .utils import PrinciplesManager, format_principle_message, get_next_send_time, get_principle_image_path, has_principle_image


logger = logging.getLogger(__name__)


class YogaScheduler:
    """Scheduler for yoga bot messages."""
    
    def __init__(self, bot: Bot, storage: JsonStorage, principles_manager: PrinciplesManager):
        self.bot = bot
        self.storage = storage
        self.principles_manager = principles_manager
        self.scheduler = AsyncIOScheduler(timezone='UTC')
        self.jobs_created = 0
        
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
            await self._schedule_user_message(user)
    
    async def _schedule_user_message(self, user: User) -> None:
        """Schedule next message for specific user."""
        try:
            # Calculate next send time.
            next_send_time = get_next_send_time(
                user.timezone,
                user.time_for_send,
                user.skip_day_id
            )
            
            # Convert to UTC for scheduler.
            next_send_time_utc = next_send_time.astimezone().astimezone(tz=None).replace(tzinfo=None)
            
            # Create unique job ID.
            job_id = f"user_{user.chat_id}_{next_send_time_utc.strftime('%Y%m%d_%H%M')}"
            
            # Remove existing job for this user if any.
            existing_jobs = [job for job in self.scheduler.get_jobs() if job.id.startswith(f"user_{user.chat_id}_")]
            for job in existing_jobs:
                self.scheduler.remove_job(job.id)
            
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
    
    async def _send_principle_to_user(self, chat_id: int) -> None:
        """Send principle message to user."""
        try:
            logger.info(f"Sending principle to user {chat_id}...")
            
            # Get user data.
            user = await self.storage.get_user(chat_id)
            if not user or not user.is_active:
                logger.warning(f"User {chat_id} not found or inactive.")
                return
            
            # Get completely random principle for this user in their language.
            principle = self.principles_manager.get_random_principle(user.language)
            if not principle:
                logger.warning(f"No principles available for user {chat_id} in language {user.language}.")
                return
            
            # Format message.
            message_text = format_principle_message(principle)
            
            # Send message with retry logic.
            success = await self._send_message_with_retry(chat_id, message_text, principle_id=principle["id"])
            
            if success:
                # Log sent message.
                await self.storage.add_sent_log(chat_id, principle["id"])
                logger.info(f"Successfully sent principle {principle['id']} to user {chat_id}.")
                
                # Schedule next message.
                await self._schedule_user_message(user)
            else:
                logger.error(f"Failed to send message to user {chat_id}.")
                
        except Exception as e:
            logger.error(f"Error sending principle to user {chat_id}: {e}")
    
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
                                        parse_mode='Markdown'
                                    )
                                logger.info(f"Successfully sent image for principle {principle_id}")
                            except Exception as img_error:
                                logger.error(f"Error sending image {image_path}: {img_error}")
                                # Fallback to text message
                                sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                                logger.info("Sent fallback text message")
                        else:
                            logger.warning(f"Image path is None for principle {principle_id}")
                            # Fallback to text message
                            sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                    else:
                        logger.info(f"No image found for principle {principle_id}, sending text only")
                        # Send text message
                        sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                else:
                    logger.info("No principle_id provided, sending text message")
                    # Send text message
                    sent_message = await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                
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
            await self._schedule_user_message(user)
    
    async def send_test_message(self, chat_id: int, language: str = None) -> bool:
        """Send test message to user."""
        try:
            # Get user to determine language if not provided.
            user = await self.storage.get_user(chat_id)
            if language is None:
                language = user.language if user else "en"
            
            # Get completely random principle.
            principle = self.principles_manager.get_random_principle(language)
            
            if not principle:
                return False
            
            # Test message in user's language
            test_prefixes = {
                "en": "🧪 **Test Message**\n\n",
                "ru": "🧪 **Тестовое сообщение**\n\n",
                "uz": "🧪 **Test xabari**\n\n",
                "kz": "🧪 **Тест хабар**\n\n"
            }
            test_prefix = test_prefixes.get(language, test_prefixes["en"])
                
            message_text = f"{test_prefix}{format_principle_message(principle)}"
            
            return await self._send_message_with_retry(chat_id, message_text, principle_id=principle["id"])
            
        except Exception as e:
            logger.error(f"Error sending test message to user {chat_id}: {e}")
            return False
    
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
            existing_jobs = [job for job in self.scheduler.get_jobs() if job.id.startswith(f"user_{chat_id}_")]
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