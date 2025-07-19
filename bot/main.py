"""Main entry point for yoga bot."""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import List
from aiohttp import web
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from telegram import Bot
from telegram.ext import Application, ContextTypes
from pydantic_settings import BaseSettings
from pydantic import Field
import re

from .storage import JsonStorage
from .scheduler import YogaScheduler
from .handlers import BotHandlers
from .utils import PrinciplesManager, HealthCheck, get_prometheus_metrics


class Settings(BaseSettings):
    """Application settings."""
    
    # Telegram settings.
    bot_token: str = Field(..., description="Telegram bot token")
    
    # Admin settings.
    admin_ids: str = Field(default="", description="Comma-separated admin user IDs")
    
    # Storage settings.
    data_dir: str = Field(default="data", description="Data directory path")
    
    # Monitoring settings.
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")
    http_port: int = Field(default=8080, description="HTTP server port for healthcheck")
    
    # Logging settings.
    log_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_admin_ids(self) -> List[int]:
        """Get list of admin IDs."""
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


def setup_logging(log_level: str) -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from some libraries.
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Hide sensitive information (tokens) from logs
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram.request').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext.updater').setLevel(logging.WARNING)
    
    # Custom log filter to hide bot tokens
    class TokenFilter(logging.Filter):
        def filter(self, record):
            if hasattr(record, 'message'):
                # Hide bot token from URLs
                record.message = re.sub(r'/bot\d+:[A-Za-z0-9_-]+/', '/bot***HIDDEN***/', str(record.msg))
                record.msg = re.sub(r'/bot\d+:[A-Za-z0-9_-]+/', '/bot***HIDDEN***/', str(record.msg))
            return True
    
    # Apply filter to all handlers
    for handler in logging.getLogger().handlers:
        handler.addFilter(TokenFilter())


def setup_sentry(dsn: str) -> None:
    """Setup Sentry error tracking."""
    if not dsn:
        return
    
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )
    
    sentry_sdk.init(
        dsn=dsn,
        integrations=[sentry_logging],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production")
    )


class YogaBot:
    """Main yoga bot application."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize components.
        self.storage = JsonStorage(settings.data_dir)
        self.principles_manager = PrinciplesManager()
        self.health_check = HealthCheck()
        
        # Initialize Telegram application.
        self.application = Application.builder().token(settings.bot_token).build()
        self.bot = self.application.bot
        
        # Initialize scheduler.
        self.scheduler = YogaScheduler(
            self.bot,
            self.storage,
            self.principles_manager
        )
        
        # Initialize handlers.
        self.handlers = BotHandlers(
            self.application,
            self.storage,
            self.scheduler,
            self.principles_manager,
            settings.get_admin_ids()
        )
        
        # HTTP server for healthcheck.
        self.http_app = None
        self.http_runner = None
        self.http_site = None
        
        # Shutdown event.
        self.shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the bot."""
        self.logger.info("Starting yoga bot...")
        
        try:
            # Load principles.
            await self.principles_manager.load_principles()
            self.logger.info(f"Loaded principles for languages: {list(self.principles_manager._principles.keys())}")
            
            # Initialize bot application.
            await self.application.initialize()
            
            # Start scheduler.
            await self.scheduler.start()
            
            # Start HTTP server.
            await self.start_http_server()
            
            # Start bot polling.
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Get bot info.
            bot_info = await self.bot.get_me()
            self.logger.info(f"Bot started successfully: @{bot_info.username}")
            
            # Send startup message to admins.
            startup_msg = (
                f"🚀 **Yoga Bot Started**\n\n"
                f"🕐 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"📊 Languages: {list(self.principles_manager._principles.keys())}\n"
                f"🌐 HTTP server: http://localhost:{self.settings.http_port}"
            )
            
            for admin_id in self.settings.get_admin_ids():
                try:
                    await self.bot.send_message(admin_id, startup_msg, parse_mode='Markdown')
                except Exception as e:
                    self.logger.warning(f"Failed to send startup message to admin {admin_id}: {e}")
            
            self.logger.info("Yoga bot started successfully!")
            
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the bot."""
        self.logger.info("Stopping yoga bot...")
        
        try:
            # Stop scheduler.
            await self.scheduler.stop()
            
            # Stop HTTP server.
            await self.stop_http_server()
            
            # Stop bot application.
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            self.logger.info("Yoga bot stopped successfully.")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def start_http_server(self) -> None:
        """Start HTTP server for healthcheck and metrics."""
        self.http_app = web.Application()
        
        # Add routes.
        self.http_app.router.add_get('/healthz', self.health_handler)
        self.http_app.router.add_get('/metrics', self.metrics_handler)
        self.http_app.router.add_get('/stats', self.stats_handler)
        
        # Start server.
        self.http_runner = web.AppRunner(self.http_app)
        await self.http_runner.setup()
        
        self.http_site = web.TCPSite(
            self.http_runner, 
            '0.0.0.0', 
            self.settings.http_port
        )
        await self.http_site.start()
        
        self.logger.info(f"HTTP server started on port {self.settings.http_port}")
    
    async def stop_http_server(self) -> None:
        """Stop HTTP server."""
        if self.http_site:
            await self.http_site.stop()
        if self.http_runner:
            await self.http_runner.cleanup()
    
    async def health_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        health_status = self.health_check.get_health_status()
        
        # Add bot-specific health info.
        health_status.update({
            "bot_running": self.application.running,
            "scheduler_running": self.scheduler.scheduler.running,
            "languages_loaded": list(self.principles_manager._principles.keys())
        })
        
        return web.json_response(health_status)
    
    async def metrics_handler(self, request: web.Request) -> web.Response:
        """Prometheus metrics endpoint."""
        metrics_text = get_prometheus_metrics()
        
        # Add bot-specific metrics.
        storage_stats = await self.storage.get_stats()
        scheduler_stats = self.scheduler.get_scheduler_stats()
        
        additional_metrics = [
            "",
            "# HELP yoga_bot_users_total Total number of users",
            "# TYPE yoga_bot_users_total gauge",
            f"yoga_bot_users_total {storage_stats['total_users']}",
            "",
            "# HELP yoga_bot_active_users Active users count",
            "# TYPE yoga_bot_active_users gauge", 
            f"yoga_bot_active_users {storage_stats['active_users']}",
            "",
            "# HELP yoga_bot_messages_sent_total Total messages sent",
            "# TYPE yoga_bot_messages_sent_total counter",
            f"yoga_bot_messages_sent_total {storage_stats['total_messages_sent']}",
            "",
            "# HELP yoga_bot_scheduled_jobs Current scheduled jobs",
            "# TYPE yoga_bot_scheduled_jobs gauge",
            f"yoga_bot_scheduled_jobs {scheduler_stats['total_jobs']}"
        ]
        
        full_metrics = metrics_text + "\n" + "\n".join(additional_metrics)
        
        return web.Response(
            text=full_metrics,
            content_type='text/plain; charset=utf-8'
        )
    
    async def stats_handler(self, request: web.Request) -> web.Response:
        """Stats endpoint for debugging."""
        storage_stats = await self.storage.get_stats()
        scheduler_stats = self.scheduler.get_scheduler_stats()
        
        stats = {
            "storage": storage_stats,
            "scheduler": scheduler_stats,
            "bot": {
                "running": self.application.running,
                "uptime_seconds": (datetime.now(timezone.utc) - self.health_check.start_time).total_seconds(),
                "languages": list(self.principles_manager._principles.keys())
            }
        }
        
        return web.json_response(stats)
    
    async def run_forever(self) -> None:
        """Run bot until shutdown signal."""
        # Wait for shutdown signal.
        await self.shutdown_event.wait()
    
    def signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_event.set()


async def main() -> None:
    """Main entry point."""
    try:
        # Load settings.
        settings = Settings()
        
        # Setup logging.
        setup_logging(settings.log_level)
        logger = logging.getLogger(__name__)
        
        # Setup Sentry.
        setup_sentry(settings.sentry_dsn)
        
        logger.info("Starting Yoga Bot application...")
        
        # Create bot instance.
        bot = YogaBot(settings)
        
        # Setup signal handlers.
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, bot.signal_handler)
        
        try:
            # Start bot.
            await bot.start()
            
            # Run forever.
            await bot.run_forever()
            
        finally:
            # Stop bot.
            await bot.stop()
    
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown by user.")
        sys.exit(0) 