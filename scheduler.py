"""Scheduler for automated daily tasks."""
import schedule
import time
from datetime import datetime
import pytz
from loguru import logger
from config import config
from data_fetcher import DataFetcher
from gamma_engine import GammaEngine
from es_converter import SPXtoESConverter
from alert_system import AlertSystem
import json


class GammaScheduler:
    """Automated scheduler for gamma level analysis."""
    
    def __init__(self):
        """Initialize scheduler with all components."""
        self.fetcher = DataFetcher()
        self.engine = GammaEngine()
        self.converter = SPXtoESConverter()
        self.alerts = AlertSystem()
        self.timezone = pytz.timezone(config.timezone)
        
        # State
        self.is_running = False
        self.current_data = {}
        
    def job_load_options(self):
        """Job: Load SPX options data (13:45 CET)."""
        logger.info("🔄 JOB: Loading SPX options data")
        
        try:
            # Get current SPX price
            spx_price = self.fetcher.get_spx_price()
            if not spx_price:
                logger.error("Could not fetch SPX price")
                return
            
            # Get 0DTE options
            options_df = self.fetcher.get_0dte_options()
            if options_df.empty:
                logger.error("No options data retrieved")
                return
            
            # Filter by range
            filtered_df = self.fetcher.filter_options_by_range(options_df, spx_price)
            
            # Save data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.fetcher.save_data(filtered_df, f"options_{timestamp}.csv")
            
            # Store in state
            self.current_data['options_df'] = filtered_df
            self.current_data['spx_price'] = spx_price
            
            logger.info("✅ Options data loaded successfully")
            
        except Exception as e:
            logger.error(f"Error in job_load_options: {e}")
    
    def job_calculate_spread(self):
        """Job: Calculate ES-SPX spread (15:30 CET)."""
        logger.info("🔄 JOB: Calculating ES-SPX spread")
        
        try:
            # Get current prices
            spx_price = self.fetcher.get_spx_price()
            es_price = self.fetcher.get_es_price()
            
            if not spx_price or not es_price:
                logger.error("Could not fetch prices for spread calculation")
                return
            
            # Calculate and cache spread
            spread = self.converter.calculate_spread(spx_price, es_price)
            
            logger.info(f"✅ Spread calculated: {spread:.2f}")
            
        except Exception as e:
            logger.error(f"Error in job_calculate_spread: {e}")
    
    def job_calculate_levels(self):
        """Job: Calculate gamma levels and convert to ES (15:31 CET)."""
        logger.info("🔄 JOB: Calculating gamma levels")
        
        try:
            # Check if we have options data
            if 'options_df' not in self.current_data or 'spx_price' not in self.current_data:
                logger.error("No options data available for level calculation")
                return
            
            options_df = self.current_data['options_df']
            spx_price = self.current_data['spx_price']
            
            # Run gamma analysis
            df_agg, levels, regime = self.engine.process_options_data(options_df, spx_price)
            
            # Convert levels to ES
            converted_levels = self.converter.convert_levels_dict(levels)
            
            # Save results
            results = {
                'timestamp': datetime.now().isoformat(),
                'spx_price': spx_price,
                'levels': levels,
                'converted_levels': converted_levels,
                'regime': regime
            }
            
            with open(config.data_dir / "latest_levels.json", 'w') as f:
                json.dump(results, f, indent=2)
            
            # Store in state
            self.current_data['converted_levels'] = converted_levels
            self.current_data['regime'] = regime
            
            logger.info(f"✅ Levels calculated - Regime: {regime}")
            
        except Exception as e:
            logger.error(f"Error in job_calculate_levels: {e}")
    
    def job_activate_alerts(self):
        """Job: Activate alert monitoring (15:32 CET)."""
        logger.info("🔄 JOB: Activating alerts")
        
        try:
            # Check if we have converted levels
            if 'converted_levels' not in self.current_data:
                logger.error("No converted levels available for alert setup")
                return
            
            converted_levels = self.current_data['converted_levels']
            
            # Setup alert conditions
            self.alerts.setup_levels(converted_levels)
            
            logger.info(f"✅ Alerts activated - {len(self.alerts.conditions)} conditions set")
            
        except Exception as e:
            logger.error(f"Error in job_activate_alerts: {e}")
    
    def job_monitor_alerts(self):
        """Job: Monitor and trigger alerts (runs live every minute)."""
        try:
            # Get current ES price
            es_price = self.fetcher.get_es_price()
            if not es_price:
                return
            
            # Check alert conditions
            triggered = self.alerts.check_all_conditions(es_price)
            
            # Send notifications for triggered alerts
            for condition in triggered:
                self.alerts.send_alert(condition, es_price)
            
        except Exception as e:
            logger.error(f"Error in job_monitor_alerts: {e}")
    
    def job_save_daily_log(self):
        """Job: Save daily log (22:00 CET)."""
        logger.info("🔄 JOB: Saving daily log")
        
        try:
            # Prepare daily summary
            summary = {
                'date': datetime.now().date().isoformat(),
                'timestamp': datetime.now().isoformat(),
                'data': self.current_data,
                'alert_summary': self.alerts.get_alert_summary(),
                'spread_summary': self.converter.get_conversion_summary()
            }
            
            # Save to daily log file
            log_file = config.logs_dir / f"daily_log_{datetime.now().strftime('%Y%m%d')}.json"
            with open(log_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"✅ Daily log saved to {log_file}")
            
            # Reset alerts for next day
            self.alerts.reset_conditions()
            
        except Exception as e:
            logger.error(f"Error in job_save_daily_log: {e}")
    
    def setup_schedule(self):
        """Setup all scheduled jobs."""
        logger.info("Setting up schedule...")
        
        # Clear any existing schedule
        schedule.clear()
        
        # Schedule jobs (CET times)
        schedule.every().day.at("13:45").do(self.job_load_options)
        schedule.every().day.at("15:30").do(self.job_calculate_spread)
        schedule.every().day.at("15:31").do(self.job_calculate_levels)
        schedule.every().day.at("15:32").do(self.job_activate_alerts)
        schedule.every().day.at("22:00").do(self.job_save_daily_log)
        
        # Alert monitoring (every minute during market hours)
        schedule.every(1).minutes.do(self.job_monitor_alerts)
        
        logger.info("✅ Schedule setup complete")
        logger.info("Scheduled jobs:")
        logger.info("  13:45 - Load SPX options")
        logger.info("  15:30 - Calculate spread")
        logger.info("  15:31 - Calculate gamma levels")
        logger.info("  15:32 - Activate alerts")
        logger.info("  Every minute - Monitor alerts")
        logger.info("  22:00 - Save daily log")
    
    def run(self):
        """Start the scheduler."""
        self.setup_schedule()
        self.is_running = True
        
        logger.info("🚀 Scheduler started - waiting for scheduled jobs...")
        logger.info(f"Timezone: {config.timezone}")
        logger.info(f"Current time: {datetime.now(self.timezone)}")
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            self.is_running = False
    
    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        schedule.clear()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    # Setup logging
    logger.add(
        config.logs_dir / "scheduler_{time}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )
    
    # Create and run scheduler
    scheduler = GammaScheduler()
    scheduler.run()
