"""Intelligent alert system with conditional triggers."""
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path
from loguru import logger
from config import config
import asyncio


class AlertCondition:
    """Define an alert condition."""
    
    def __init__(
        self,
        level_name: str,
        es_level: float,
        distance_threshold: float = None,
        volume_threshold: Optional[float] = None
    ):
        """Initialize alert condition.
        
        Args:
            level_name: Name of the level (e.g., 'put_wall', 'call_wall')
            es_level: ES price level to monitor
            distance_threshold: Distance in points to trigger alert
            volume_threshold: Minimum volume for alert (optional)
        """
        self.level_name = level_name
        self.es_level = es_level
        self.distance_threshold = distance_threshold or config.alert_distance_threshold
        self.volume_threshold = volume_threshold
        self.triggered = False
        self.trigger_time = None
        
    def check(
        self,
        current_es_price: float,
        current_volume: Optional[float] = None,
        velocity: Optional[float] = None
    ) -> bool:
        """Check if alert condition is met.
        
        Args:
            current_es_price: Current ES price
            current_volume: Current volume (optional)
            velocity: Price velocity (optional)
            
        Returns:
            True if alert should trigger
        """
        # Check distance
        distance = abs(current_es_price - self.es_level)
        
        if distance > self.distance_threshold:
            return False
        
        # Check volume if threshold is set
        if self.volume_threshold is not None and current_volume is not None:
            if current_volume < self.volume_threshold:
                return False
        
        # Check velocity if provided (price moving toward level)
        if velocity is not None:
            # If price is moving away from level, don't alert
            if current_es_price < self.es_level and velocity < 0:
                return False
            if current_es_price > self.es_level and velocity > 0:
                return False
        
        return True
    
    def trigger(self):
        """Mark alert as triggered."""
        self.triggered = True
        self.trigger_time = datetime.now()


class AlertSystem:
    """Intelligent alert system with multiple notification channels."""
    
    def __init__(self):
        """Initialize alert system."""
        self.conditions: List[AlertCondition] = []
        self.alert_history: List[Dict] = []
        self.alert_log_file = config.logs_dir / "alerts.jsonl"
        
    def add_condition(self, condition: AlertCondition):
        """Add an alert condition to monitor.
        
        Args:
            condition: AlertCondition to add
        """
        self.conditions.append(condition)
        logger.info(f"Added alert condition: {condition.level_name} @ ES {condition.es_level:.2f} (threshold: ±{condition.distance_threshold})")
    
    def setup_levels(self, converted_levels: Dict[str, Dict[str, float]]):
        """Setup alert conditions from converted levels.
        
        Args:
            converted_levels: Dictionary with SPX and ES levels
        """
        self.conditions.clear()
        
        for level_name, level_data in converted_levels.items():
            if 'es' in level_data:
                condition = AlertCondition(
                    level_name=level_name,
                    es_level=level_data['es']
                )
                self.add_condition(condition)
        
        logger.info(f"Setup {len(self.conditions)} alert conditions")
    
    def check_all_conditions(
        self,
        current_es_price: float,
        current_volume: Optional[float] = None,
        velocity: Optional[float] = None
    ) -> List[AlertCondition]:
        """Check all conditions and return triggered alerts.
        
        Args:
            current_es_price: Current ES price
            current_volume: Current volume (optional)
            velocity: Price velocity (optional)
            
        Returns:
            List of triggered AlertConditions
        """
        triggered = []
        
        for condition in self.conditions:
            # Skip already triggered conditions
            if condition.triggered:
                continue
            
            if condition.check(current_es_price, current_volume, velocity):
                condition.trigger()
                triggered.append(condition)
                
                # Log alert
                alert_data = {
                    'timestamp': condition.trigger_time.isoformat(),
                    'level_name': condition.level_name,
                    'es_level': condition.es_level,
                    'current_price': current_es_price,
                    'distance': abs(current_es_price - condition.es_level),
                    'volume': current_volume,
                    'velocity': velocity
                }
                
                self.alert_history.append(alert_data)
                self._log_alert(alert_data)
                
                logger.warning(f"🚨 ALERT TRIGGERED: {condition.level_name} at ES {condition.es_level:.2f} (current: {current_es_price:.2f})")
        
        return triggered
    
    def _log_alert(self, alert_data: Dict):
        """Log alert to file.
        
        Args:
            alert_data: Alert information dictionary
        """
        with open(self.alert_log_file, 'a') as f:
            f.write(json.dumps(alert_data) + '\n')
    
    async def send_telegram_alert(self, message: str):
        """Send alert via Telegram.
        
        Args:
            message: Alert message
        """
        if not config.telegram_bot_token or not config.telegram_chat_id:
            logger.debug("Telegram not configured")
            return
        
        try:
            from telegram import Bot
            bot = Bot(token=config.telegram_bot_token)
            await bot.send_message(chat_id=config.telegram_chat_id, text=message)
            logger.info("Telegram alert sent")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    def send_discord_alert(self, message: str):
        """Send alert via Discord webhook.
        
        Args:
            message: Alert message
        """
        if not config.discord_webhook_url:
            logger.debug("Discord not configured")
            return
        
        try:
            from discord_webhook import DiscordWebhook
            webhook = DiscordWebhook(url=config.discord_webhook_url, content=message)
            webhook.execute()
            logger.info("Discord alert sent")
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
    
    def send_email_alert(self, subject: str, body: str):
        """Send alert via email.
        
        Args:
            subject: Email subject
            body: Email body
        """
        if not all([config.email_smtp_server, config.email_from, config.email_to]):
            logger.debug("Email not configured")
            return
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = config.email_from
            msg['To'] = config.email_to
            
            with smtplib.SMTP(config.email_smtp_server, config.email_smtp_port) as server:
                server.starttls()
                server.login(config.email_from, config.email_password)
                server.send_message(msg)
            
            logger.info("Email alert sent")
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
    
    def send_alert(self, condition: AlertCondition, current_price: float):
        """Send alert through all configured channels.
        
        Args:
            condition: Triggered condition
            current_price: Current ES price
        """
        message = f"""
🚨 GAMMA LEVEL ALERT 🚨

Level: {condition.level_name.upper()}
ES Target: ${condition.es_level:.2f}
Current Price: ${current_price:.2f}
Distance: ${abs(current_price - condition.es_level):.2f}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Send through available channels
        self.send_discord_alert(message)
        
        # Telegram requires async
        try:
            asyncio.run(self.send_telegram_alert(message))
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
        
        # Email
        self.send_email_alert(
            subject=f"Gamma Alert: {condition.level_name}",
            body=message
        )
    
    def reset_conditions(self):
        """Reset all triggered conditions (e.g., at start of new day)."""
        for condition in self.conditions:
            condition.triggered = False
            condition.trigger_time = None
        
        logger.info("All alert conditions reset")
    
    def get_alert_summary(self) -> Dict:
        """Get summary of alert system state.
        
        Returns:
            Dictionary with alert system information
        """
        return {
            'total_conditions': len(self.conditions),
            'triggered_count': sum(1 for c in self.conditions if c.triggered),
            'active_conditions': [
                {
                    'level_name': c.level_name,
                    'es_level': c.es_level,
                    'triggered': c.triggered,
                    'trigger_time': c.trigger_time.isoformat() if c.trigger_time else None
                }
                for c in self.conditions
            ],
            'alert_history_count': len(self.alert_history)
        }
