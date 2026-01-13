"""Main application entry point for GammaOption."""
import sys
import argparse
from datetime import datetime
from loguru import logger
from config import config
from data_fetcher import DataFetcher
from gamma_engine import GammaEngine
from es_converter import SPXtoESConverter
from alert_system import AlertSystem
import json
from reporting import write_daily_table


def setup_logging():
    """Setup logging configuration."""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # File logging
    logger.add(
        config.logs_dir / "app_{time}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    logger.info("Logging initialized")


def run_full_analysis():
    """Run complete gamma analysis pipeline."""
    logger.info("=" * 80)
    logger.info("STARTING FULL GAMMA ANALYSIS")
    logger.info("=" * 80)
    
    try:
        # Initialize components
        fetcher = DataFetcher()
        engine = GammaEngine()
        converter = SPXtoESConverter()
        alerts = AlertSystem()
        
        # Step 1: Get SPX price
        logger.info("\n[STEP 1] Fetching SPX price...")
        spx_price = fetcher.get_spx_price()
        if not spx_price:
            logger.error("Failed to fetch SPX price")
            return False
        
        # Step 2: Get ES price and calculate spread
        logger.info("\n[STEP 2] Fetching ES price and calculating spread...")
        es_price = fetcher.get_es_price()
        if not es_price:
            logger.error("Failed to fetch ES price")
            return False
        
        spread = converter.calculate_spread(spx_price, es_price)
        logger.info(f"Spread: {spread:.2f}")
        
        # Step 3: Get 0DTE options
        logger.info("\n[STEP 3] Fetching 0DTE options...")
        options_df = fetcher.get_0dte_options()
        if options_df.empty:
            logger.error("No options data retrieved")
            return False
        
        # Step 4: Filter options by range
        logger.info("\n[STEP 4] Filtering options by price range...")
        filtered_df = fetcher.filter_options_by_range(options_df, spx_price)
        
        # Save raw data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fetcher.save_data(filtered_df, f"options_{timestamp}.csv")
        
        # Step 5: Calculate gamma levels
        logger.info("\n[STEP 5] Calculating gamma levels...")
        df_agg, levels, regime = engine.process_options_data(filtered_df, spx_price)
        
        # Step 6: Convert to ES levels
        logger.info("\n[STEP 6] Converting levels to ES...")
        price_levels = {k: v for k, v in levels.items() if k in {"put_wall", "call_wall", "gamma_flip"}}
        converted_levels = converter.convert_levels_dict(price_levels)
        
        # Step 7: Setup alerts
        logger.info("\n[STEP 7] Setting up alerts...")
        alerts.setup_levels(converted_levels)
        
        # Prepare results
        results = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().date().isoformat(),
            'spx_price': spx_price,
            'es_price': es_price,
            'spread': spread,
            'regime': regime,
            'levels': levels,
            'converted_levels': converted_levels,
            'gamma_profile': df_agg[['strike', 'net_gamma', 'call_gamma', 'put_gamma']].head(200).to_dict('records')
        }
        
        # Save results
        with open(config.data_dir / "latest_levels.json", 'w') as f:
            json.dump(results, f, indent=2)

        # Save daily table (CSV)
        try:
            table_path = write_daily_table(config.data_dir, results)
            logger.info(f"Daily table saved: {table_path}")
        except Exception as e:
            logger.warning(f"Could not write daily table: {e}")
        
        # Display summary
        logger.info("\n" + "=" * 80)
        logger.info("ANALYSIS COMPLETE - SUMMARY")
        logger.info("=" * 80)
        logger.info(f"SPX Price: ${spx_price:.2f}")
        logger.info(f"ES Price: ${es_price:.2f}")
        logger.info(f"Spread: {spread:+.2f}")
        logger.info(f"Regime: {regime.upper()}")
        logger.info("\nKey Levels (ES):")
        for level_name, level_data in converted_levels.items():
            logger.info(f"  {level_name.upper()}: ${level_data['es']:.2f} (SPX: ${level_data['spx']:.2f})")
        logger.info("\n" + "=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in full analysis: {e}", exc_info=True)
        return False


def run_quick_update():
    """Quick update of current prices and check alerts."""
    logger.info("Running quick update...")
    
    try:
        fetcher = DataFetcher()
        converter = SPXtoESConverter()
        alerts = AlertSystem()
        
        # Get current prices
        spx_price = fetcher.get_spx_price()
        es_price = fetcher.get_es_price()
        
        if not spx_price or not es_price:
            logger.warning("Could not fetch prices")
            return False
        
        # Load existing levels
        levels_file = config.data_dir / "latest_levels.json"
        if levels_file.exists():
            with open(levels_file, 'r') as f:
                data = json.load(f)
            
            converted_levels = data.get('converted_levels', {})
            
            # Setup alerts if not already done
            if not alerts.conditions:
                alerts.setup_levels(converted_levels)
            
            # Check alert conditions
            triggered = alerts.check_all_conditions(es_price)
            
            if triggered:
                logger.warning(f"⚠️ {len(triggered)} ALERTS TRIGGERED!")
                for condition in triggered:
                    alerts.send_alert(condition, es_price)
            
            # Display current status
            logger.info(f"SPX: ${spx_price:.2f} | ES: ${es_price:.2f}")
            logger.info("Levels:")
            for level_name, level_data in converted_levels.items():
                distance = es_price - level_data['es']
                logger.info(f"  {level_name.upper()}: ${level_data['es']:.2f} ({distance:+.2f})")
            
        else:
            logger.warning("No levels data found. Run full analysis first.")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error in quick update: {e}")
        return False


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="GammaOption - SPX 0DTE Gamma Level Analysis")
    
    parser.add_argument(
        'command',
        choices=['analyze', 'update', 'schedule', 'dashboard'],
        help='Command to run'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    logger.info(f"GammaOption v1.0 - Command: {args.command}")
    
    # Execute command
    if args.command == 'analyze':
        success = run_full_analysis()
        sys.exit(0 if success else 1)
        
    elif args.command == 'update':
        success = run_quick_update()
        sys.exit(0 if success else 1)
        
    elif args.command == 'schedule':
        from scheduler import GammaScheduler
        scheduler = GammaScheduler()
        scheduler.run()
        
    elif args.command == 'dashboard':
        import subprocess
        logger.info("Starting Streamlit dashboard...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard.py"])


if __name__ == "__main__":
    main()
