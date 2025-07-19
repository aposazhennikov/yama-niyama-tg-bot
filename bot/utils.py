"""Utility functions for yoga bot."""

import json
import random
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import pytz
import aiofiles


class PrinciplesManager:
    """Manager for yoga principles."""
    
    def __init__(self, principles_file: str = "bot/principles.json"):
        self.principles_file = principles_file
        self._principles: List[Dict[str, Any]] = []
    
    async def load_principles(self) -> None:
        """Load principles from JSON file."""
        try:
            async with aiofiles.open(self.principles_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                self._principles = json.loads(content)
        except Exception as e:
            print(f"Error loading principles: {e}")
            self._principles = {"en": [], "ru": []}
    
    def get_principle_by_id(self, principle_id: int) -> Optional[Dict[str, Any]]:
        """Get principle by ID."""
        for principle in self._principles:
            if principle["id"] == principle_id:
                return principle
        return None
    
    def get_random_principle(self, language: str = "en", excluded_ids: List[int] = None) -> Optional[Dict[str, Any]]:
        """Get completely random principle for specified language."""
        if not self._principles:
            return None
        
        # Get principles for specified language
        lang_principles = self._principles.get(language, self._principles.get("en", []))
        if not lang_principles:
            return None
        
        return random.choice(lang_principles)
    
    def get_all_principles(self, language: str = "en") -> List[Dict[str, Any]]:
        """Get all principles for specified language."""
        if not self._principles:
            return []
        
        return self._principles.get(language, self._principles.get("en", [])).copy()
    
    async def add_principle(self, principle: Dict[str, Any]) -> bool:
        """Add new principle."""
        # Get max ID and increment.
        max_id = max([p["id"] for p in self._principles], default=0)
        principle["id"] = max_id + 1
        
        self._principles.append(principle)
        
        # Save to file.
        try:
            async with aiofiles.open(self.principles_file, 'w', encoding='utf-8') as f:
                content = json.dumps(self._principles, ensure_ascii=False, indent=2)
                await f.write(content)
            return True
        except Exception:
            # Remove from memory if saving failed.
            self._principles.remove(principle)
            return False


def format_principle_message(principle: Dict[str, Any]) -> str:
    """Format principle for sending to user."""
    emoji = principle.get("emoji", "🧘")
    name = principle.get("name", "")
    short_desc = principle.get("short_description", "")
    description = principle.get("description", "")
    practice_tip = principle.get("practice_tip", "")
    
    message = f"**{name}** {emoji}\n\n"
    message += f"{short_desc}\n\n"
    message += f"{description}\n\n"
    
    if practice_tip:
        message += f"💡 *{practice_tip}*"
    
    return message


def is_valid_timezone(timezone_str: str) -> bool:
    """Check if timezone string is valid."""
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def is_valid_time_format(time_str: str) -> bool:
    """Check if time string is in HH:MM format."""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def get_user_local_time(user_timezone: str, target_time: str) -> datetime:
    """Get next occurrence of target time in user's timezone."""
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.UTC
    
    # Parse target time.
    target_hour, target_minute = map(int, target_time.split(":"))
    
    # Get current time in user's timezone.
    now = datetime.now(tz)
    
    # Create target datetime for today.
    target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    # If target time already passed today, schedule for tomorrow.
    if target_dt <= now:
        target_dt += timedelta(days=1)
    
    return target_dt


def should_skip_today(skip_days: List[int], target_datetime: datetime) -> bool:
    """Check if should skip sending today based on user's skip days."""
    # Monday = 0, Sunday = 6.
    weekday = target_datetime.weekday()
    return weekday in skip_days


def get_next_send_time(user_timezone: str, target_time: str, skip_days: List[int]) -> datetime:
    """Get next valid send time considering skip days."""
    target_dt = get_user_local_time(user_timezone, target_time)
    
    # Keep checking future days until we find one that's not skipped.
    while should_skip_today(skip_days, target_dt):
        target_dt += timedelta(days=1)
    
    return target_dt


def validate_skip_days(skip_days: List[int]) -> bool:
    """Validate skip days list."""
    if not isinstance(skip_days, list):
        return False
    
    for day in skip_days:
        if not isinstance(day, int) or day < 0 or day > 6:
            return False
    
    return True


class HealthCheck:
    """Health check utilities."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "status": "healthy",
            "uptime_seconds": int(uptime.total_seconds()),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics format."""
    # Basic metrics for now.
    uptime = datetime.utcnow() - datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    metrics = [
        "# HELP yoga_bot_uptime_seconds Bot uptime in seconds",
        "# TYPE yoga_bot_uptime_seconds counter",
        f"yoga_bot_uptime_seconds {int(uptime.total_seconds())}",
        "",
        "# HELP yoga_bot_info Bot information",
        "# TYPE yoga_bot_info gauge",
        'yoga_bot_info{version="1.0.0"} 1'
    ]
    
    return "\n".join(metrics)


def get_principle_image_path(principle_id: int) -> Optional[str]:
    """Get image path for principle by ID."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Get the directory where this file is located
    current_dir = Path(__file__).parent.parent
    
    # Try different possible locations for images
    possible_paths = [
        current_dir / "images" / f"{principle_id}.jpg",  # From project root
        Path("images") / f"{principle_id}.jpg",  # Relative to current dir
        Path("../images") / f"{principle_id}.jpg",  # One level up
        Path(f"./images/{principle_id}.jpg"),  # Current directory
        Path(f"/app/images/{principle_id}.jpg"),  # Docker absolute path
    ]
    
    for image_path in possible_paths:
        logger.debug(f"Checking image path: {image_path}")
        if image_path.exists():
            logger.info(f"Found image for principle {principle_id}: {image_path}")
            return str(image_path)
    
    logger.warning(f"No image found for principle {principle_id}. Checked paths: {[str(p) for p in possible_paths]}")
    return None


def has_principle_image(principle_id: int) -> bool:
    """Check if principle has an associated image."""
    return get_principle_image_path(principle_id) is not None 