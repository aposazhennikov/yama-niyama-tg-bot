"""Storage module for yoga bot data management."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import aiofiles


@dataclass
class User:
    """User data model."""
    chat_id: int
    language: str = "en"  # Default to English
    timezone: str = "Europe/Moscow"
    time_for_send: str = "06:00"
    skip_day_id: List[int] = None
    is_active: bool = True
    last_feedback_time: Optional[float] = None  # Unix timestamp for rate limiting
    
    def __post_init__(self):
        """Initialize default values."""
        if self.skip_day_id is None:
            self.skip_day_id = []
        # Ensure last_feedback_time is None if not set
        if not hasattr(self, 'last_feedback_time'):
            self.last_feedback_time = None


@dataclass 
class SentLog:
    """Sent message log model."""
    chat_id: int
    principle_id: int
    sent_at: str


@dataclass
class Feedback:
    """User feedback model."""
    id: str
    chat_id: int
    username: str
    language: str
    message: str
    timestamp: str
    message_length: int


@dataclass
class BotMessage:
    """Bot message data model for dialog cleanup."""
    chat_id: int
    message_id: int
    sent_at: str
    message_type: str  # "principle", "menu", "test", etc.


class JsonStorage:
    """JSON-based storage for bot data."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.logs_file = os.path.join(data_dir, "sent_logs.json")
        self.principles_file = os.path.join(data_dir, "user_principles.json")
        self.feedback_file = os.path.join(data_dir, "feedback.json")
        self.messages_file = os.path.join(data_dir, "bot_messages.json")
        
        # Ensure data directory exists.
        os.makedirs(data_dir, exist_ok=True)
        
    async def _read_json(self, filepath: str) -> Dict[str, Any]:
        """Read JSON file asynchronously."""
        try:
            if os.path.exists(filepath):
                async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            return {}
        except Exception:
            return {}
    
    async def _write_json(self, filepath: str, data: Dict[str, Any]) -> bool:
        """Write JSON file asynchronously."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write data to file
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                content = json.dumps(data, ensure_ascii=False, indent=2)
                await f.write(content)
                logger.info(f"Successfully wrote data to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing to {filepath}: {e}")
            return False
    
    async def get_user(self, chat_id: int) -> Optional[User]:
        """Get user by chat_id."""
        users_data = await self._read_json(self.users_file)
        user_data = users_data.get(str(chat_id))
        if user_data:
            return User(**user_data)
        return None
    
    async def save_user(self, user: User) -> bool:
        """Save or update user."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            users_data = await self._read_json(self.users_file)
            user_dict = asdict(user)
            users_data[str(user.chat_id)] = user_dict
            logger.info(f"Saving user data: {user_dict}")
            
            success = await self._write_json(self.users_file, users_data)
            if not success:
                logger.error(f"Failed to write user data to {self.users_file}")
            return success
            
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
            return False
    
    async def get_all_active_users(self) -> List[User]:
        """Get all active users."""
        users_data = await self._read_json(self.users_file)
        active_users = []
        for user_data in users_data.values():
            if user_data.get("is_active", True):
                active_users.append(User(**user_data))
        return active_users
    
    async def deactivate_user(self, chat_id: int) -> bool:
        """Deactivate user."""
        user = await self.get_user(chat_id)
        if user:
            user.is_active = False
            return await self.save_user(user)
        return False
    
    async def add_sent_log(self, chat_id: int, principle_id: int) -> bool:
        """Add sent message log."""
        logs_data = await self._read_json(self.logs_file)
        
        # Initialize logs for user if not exists.
        chat_id_str = str(chat_id)
        if chat_id_str not in logs_data:
            logs_data[chat_id_str] = []
        
        # Add new log entry.
        log_entry = {
            "chat_id": chat_id,
            "principle_id": principle_id,
            "sent_at": datetime.utcnow().isoformat()
        }
        logs_data[chat_id_str].append(log_entry)
        
        return await self._write_json(self.logs_file, logs_data)
    
    async def get_user_sent_principles(self, chat_id: int) -> List[int]:
        """Get list of principle IDs already sent to user."""
        logs_data = await self._read_json(self.logs_file)
        user_logs = logs_data.get(str(chat_id), [])
        return [log["principle_id"] for log in user_logs]
    
    async def reset_user_cycle(self, chat_id: int) -> bool:
        """Reset user's principle cycle."""
        logs_data = await self._read_json(self.logs_file)
        logs_data[str(chat_id)] = []
        return await self._write_json(self.logs_file, logs_data)
    
    async def add_bot_message(self, chat_id: int, message_id: int, message_type: str = "general") -> bool:
        """Add bot message for dialog cleanup."""
        messages_data = await self._read_json(self.messages_file)
        
        # Initialize messages for user if not exists.
        chat_id_str = str(chat_id)
        if chat_id_str not in messages_data:
            messages_data[chat_id_str] = []
        
        # Add new message entry.
        message_entry = {
            "chat_id": chat_id,
            "message_id": message_id,
            "sent_at": datetime.utcnow().isoformat(),
            "message_type": message_type
        }
        messages_data[chat_id_str].append(message_entry)
        
        # Keep only last 50 messages per user to avoid file growth.
        messages_data[chat_id_str] = messages_data[chat_id_str][-50:]
        
        return await self._write_json(self.messages_file, messages_data)
    
    async def get_user_bot_messages(self, chat_id: int) -> List[BotMessage]:
        """Get list of bot messages for user."""
        messages_data = await self._read_json(self.messages_file)
        user_messages = messages_data.get(str(chat_id), [])
        
        result = []
        for msg_data in user_messages:
            try:
                result.append(BotMessage(**msg_data))
            except Exception:
                continue  # Skip invalid message entries.
        
        return result
    
    async def clear_user_bot_messages(self, chat_id: int) -> bool:
        """Clear all stored bot messages for user."""
        messages_data = await self._read_json(self.messages_file)
        chat_id_str = str(chat_id)
        
        if chat_id_str in messages_data:
            del messages_data[chat_id_str]
            return await self._write_json(self.messages_file, messages_data)
        
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        users_data = await self._read_json(self.users_file)
        logs_data = await self._read_json(self.logs_file)
        
        total_users = len(users_data)
        active_users = sum(1 for user in users_data.values() if user.get("is_active", True))
        total_messages = sum(len(logs) for logs in logs_data.values())
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_messages_sent": total_messages
        }
    
    async def can_send_feedback(self, chat_id: int, rate_limit_minutes: int = 10) -> bool:
        """Check if user can send feedback (rate limiting)."""
        import time
        
        user = await self.get_user(chat_id)
        if not user or not user.last_feedback_time:
            return True
        
        time_since_last = time.time() - user.last_feedback_time
        return time_since_last >= (rate_limit_minutes * 60)
    
    async def add_feedback(self, feedback: Feedback) -> bool:
        """Add user feedback to storage."""
        import time
        import uuid
        
        try:
            # Check file size limit (10MB)
            if os.path.exists(self.feedback_file):
                file_size = os.path.getsize(self.feedback_file)
                if file_size > 10 * 1024 * 1024:  # 10MB limit
                    return False
            
            feedback_data = await self._read_json(self.feedback_file)
            
            # Generate unique ID if not provided
            if not feedback.id:
                feedback.id = str(uuid.uuid4())[:8]
            
            # Add feedback to list
            if "feedback" not in feedback_data:
                feedback_data["feedback"] = []
            
            feedback_data["feedback"].append(asdict(feedback))
            
            # Update user's last feedback time
            user = await self.get_user(feedback.chat_id)
            if user:
                user.last_feedback_time = time.time()
                await self.save_user(user)
            
            return await self._write_json(self.feedback_file, feedback_data)
            
        except Exception:
            return False
    
    async def get_all_feedback(self, limit: int = 50) -> List[Feedback]:
        """Get all feedback with optional limit."""
        try:
            feedback_data = await self._read_json(self.feedback_file)
            feedback_list = feedback_data.get("feedback", [])
            
            # Sort by timestamp (newest first) and limit
            feedback_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            limited_feedback = feedback_list[:limit]
            
            # Convert to Feedback objects
            result = []
            for item in limited_feedback:
                try:
                    result.append(Feedback(**item))
                except Exception:
                    continue  # Skip invalid feedback entries
            
            return result
            
        except Exception:
            return []
    
    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        try:
            feedback_data = await self._read_json(self.feedback_file)
            feedback_list = feedback_data.get("feedback", [])
            
            total_feedback = len(feedback_list)
            avg_length = 0
            if feedback_list:
                avg_length = sum(item.get("message_length", 0) for item in feedback_list) / total_feedback
            
            # Count by language
            lang_count = {}
            for item in feedback_list:
                lang = item.get("language", "unknown")
                lang_count[lang] = lang_count.get(lang, 0) + 1
            
            return {
                "total_feedback": total_feedback,
                "average_length": round(avg_length, 1),
                "by_language": lang_count,
                "file_size_mb": round(os.path.getsize(self.feedback_file) / (1024*1024), 2) if os.path.exists(self.feedback_file) else 0
            }
            
        except Exception:
            return {
                "total_feedback": 0,
                "average_length": 0,
                "by_language": {},
                "file_size_mb": 0
            } 