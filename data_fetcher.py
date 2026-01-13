"""Data fetching module for SPX options and price data with multiple data sources."""
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import pandas as pd
from loguru import logger
from polygon import RESTClient
import yfinance as yf
import numpy as np
import requests
from urllib.parse import quote
from config import config


class DataFetcher:
    """Fetch SPX options and price data from multiple sources."""
    
    def __init__(self):
        """Initialize the data fetcher with Polygon client."""
        self.use_polygon = bool(config.polygon_api_key)
        if self.use_polygon:
            try:
                self.client = RESTClient(config.polygon_api_key)
                logger.info("Polygon API initialized")
            except Exception as e:
                logger.warning(f"Polygon initialization failed: {e}")
                self.client = None
                self.use_polygon = False
        else:
            logger.warning("No Polygon API key - using free data sources only")
            self.client = None

    def _get_yahoo_chart_price(self, symbol: str) -> Optional[float]:
        """Fetch latest price using Yahoo Finance chart endpoint (no yfinance).

        This is used as a fallback because yfinance can intermittently fail due to
        rate limiting or changes in Yahoo responses.
        """
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}?interval=1d&range=1d"
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )

            if not response.ok:
                logger.warning(f"Yahoo chart returned status {response.status_code} for {symbol}")
                return None

            data = response.json()
            result = (data.get("chart") or {}).get("result")
            if not result:
                return None

            meta = result[0].get("meta") or {}
            if meta.get("regularMarketPrice") is not None:
                return float(meta["regularMarketPrice"])

            indicators = result[0].get("indicators") or {}
            quote_data = (indicators.get("quote") or [{}])[0]
            closes = quote_data.get("close") or []
            closes = [c for c in closes if c is not None]
            if closes:
                return float(closes[-1])

            return None
        except Exception as e:
            logger.warning(f"Yahoo chart fetch failed for {symbol}: {e}")
            return None
        
    def get_spx_price(self) -> Optional[float]:
        """Get current SPX cash price.
        
        Returns:
            Current SPX price or None if fetch fails
        """
        # Try Polygon first if available
        if self.use_polygon and self.client:
            try:
                ticker = f"I:{config.spx_symbol}"
                trades = self.client.get_last_trade(ticker)
                
                if trades:
                    price = trades.price
                    logger.info(f"SPX current price (Polygon): {price}")
                    return price
            except Exception as e:
                logger.warning(f"Polygon SPX fetch failed: {e}")
        
        # Fallback to yfinance (free)
        try:
            logger.info("Using yfinance as fallback for SPX price...")
            spx = yf.Ticker("^GSPC")  # S&P 500 Index
            data = spx.history(period="1d", interval="1m")
            
            if not data.empty:
                price = float(data['Close'].iloc[-1])
                logger.info(f"SPX current price (yfinance): {price}")
                return price
            
            logger.warning("No SPX price data available from yfinance")
        except Exception as e:
            logger.error(f"Error fetching SPX price from yfinance: {e}")

        # Final fallback: direct Yahoo chart endpoint
        logger.info("Using Yahoo chart endpoint as fallback for SPX price...")
        price = self._get_yahoo_chart_price("^GSPC")
        if price is not None:
            logger.info(f"SPX current price (Yahoo chart): {price}")
            return price

        logger.error("All SPX price sources failed")
        return None
    
    def get_es_price(self) -> Optional[float]:
        """Get current ES future price (front month).
        
        Returns:
            Current ES price or None if fetch fails
        """
        # Try Polygon first if available
        if self.use_polygon and self.client:
            try:
                ticker = config.es_symbol
                trades = self.client.get_last_trade(ticker)
                
                if trades:
                    price = trades.price
                    logger.info(f"ES current price (Polygon): {price}")
                    return price
            except Exception as e:
                logger.warning(f"Polygon ES fetch failed: {e}")
        
        # Fallback to yfinance (use ES=F for front month ES futures)
        try:
            logger.info("Using yfinance as fallback for ES price...")
            es = yf.Ticker("ES=F")  # E-mini S&P 500 Futures
            data = es.history(period="1d", interval="1m")
            
            if not data.empty:
                price = float(data['Close'].iloc[-1])
                logger.info(f"ES current price (yfinance): {price}")
                return price
            
            logger.warning("No ES price data available from yfinance")
        except Exception as e:
            logger.error(f"Error fetching ES price from yfinance: {e}")

        # Final fallback: direct Yahoo chart endpoint
        logger.info("Using Yahoo chart endpoint as fallback for ES price...")
        price = self._get_yahoo_chart_price("ES=F")
        if price is not None:
            logger.info(f"ES current price (Yahoo chart): {price}")
            return price

        logger.error("All ES price sources failed")
        return None
    
    def get_0dte_options(self, expiration_date: Optional[date] = None) -> pd.DataFrame:
        """Get 0DTE options data for SPX.
        
        Args:
            expiration_date: Target expiration date (default: today)
            
        Returns:
            DataFrame with options data including strikes, OI, volume, greeks
        """
        if expiration_date is None:
            expiration_date = date.today()
        
        # If Polygon isn't available, try real Yahoo Finance options (free) and otherwise return no data.
        if not self.use_polygon or not self.client:
            logger.warning("Polygon API not available - trying Yahoo Finance options")
            return self._fetch_yfinance_options(expiration_date)
        
        try:
            # Format expiration date for Polygon API
            exp_str = expiration_date.strftime("%Y-%m-%d")
            
            logger.info(f"Fetching 0DTE options for SPX expiring {exp_str}")
            
            # Get options contracts for SPX
            options_data = []
            
            # Fetch both calls and puts
            for contract_type in ['call', 'put']:
                try:
                    contracts = self.client.list_options_contracts(
                        underlying_ticker=config.spx_symbol,
                        contract_type=contract_type,
                        expiration_date=exp_str,
                        limit=1000
                    )
                    
                    for contract in contracts:
                        # Get snapshot for OI, volume, greeks
                        try:
                            snapshot = self.client.get_snapshot_option(
                                underlying_ticker=config.spx_symbol,
                                option_contract=contract.ticker
                            )
                            
                            if snapshot and snapshot.day:
                                options_data.append({
                                    'ticker': contract.ticker,
                                    'strike': contract.strike_price,
                                    'type': contract_type,
                                    'expiration': contract.expiration_date,
                                    'volume': snapshot.day.volume or 0,
                                    'open_interest': snapshot.open_interest or 0,
                                    'implied_volatility': snapshot.implied_volatility,
                                    'delta': snapshot.greeks.delta if snapshot.greeks else None,
                                    'gamma': snapshot.greeks.gamma if snapshot.greeks else None,
                                    'theta': snapshot.greeks.theta if snapshot.greeks else None,
                                    'vega': snapshot.greeks.vega if snapshot.greeks else None,
                                })
                        except Exception as e:
                            logger.debug(f"Could not fetch snapshot for {contract.ticker}: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error fetching {contract_type} contracts: {e}")
                    continue
            
            if not options_data:
                logger.warning("No options data retrieved from Polygon - trying Yahoo Finance")
                return self._fetch_yfinance_options(expiration_date)
            
            df = pd.DataFrame(options_data)
            logger.info(f"Fetched {len(df)} option contracts ({len(df[df['type']=='call'])} calls, {len(df[df['type']=='put'])} puts)")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching 0DTE options: {e}")
            logger.warning("Falling back to Yahoo Finance")
            return self._fetch_yfinance_options(expiration_date)
    
    def _fetch_yfinance_options(self, expiration_date: date) -> pd.DataFrame:
        """Fetch real options data from Yahoo Finance (free).
        
        Args:
            expiration_date: Expiration date for options
            
        Returns:
            DataFrame with real options data from Yahoo Finance
        """
        try:
            logger.info("Fetching real SPX options data from Yahoo Finance...")
            
            # Yahoo uses ^SPX for SPX index
            ticker = yf.Ticker("^SPX")
            
            # Get available expiration dates
            expirations = ticker.options
            
            if not expirations:
                logger.warning("No expirations available from Yahoo Finance")
                return pd.DataFrame()
            
            # Find closest expiration to requested date
            target_date_str = expiration_date.strftime("%Y-%m-%d")
            expiration_str = None
            
            # For 0DTE, get today's expiration if available
            for exp in expirations:
                if exp == target_date_str:
                    expiration_str = exp
                    break
            
            # If exact date not found, use first available (closest)
            if not expiration_str:
                expiration_str = expirations[0]
                logger.warning(f"0DTE not available, using nearest: {expiration_str}")
            
            # Get options chain
            opt_chain = ticker.option_chain(expiration_str)
            
            options_data = []
            
            # Process calls
            if not opt_chain.calls.empty:
                calls = opt_chain.calls
                for _, row in calls.iterrows():
                    # Calculate gamma approximation from delta if not available
                    gamma = self._estimate_gamma(
                        row.get('strike', 0),
                        self.get_spx_price() or 5850,
                        row.get('impliedVolatility', 0.15),
                        'call'
                    )
                    
                    options_data.append({
                        'ticker': f"SPX{int(row['strike'])}C",
                        'strike': row['strike'],
                        'type': 'call',
                        'expiration': expiration_str,
                        'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
                        'open_interest': int(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else 0,
                        'implied_volatility': row.get('impliedVolatility', 0.15),
                        'delta': self._estimate_delta(row['strike'], self.get_spx_price() or 5850, 'call'),
                        'gamma': gamma,
                        'theta': -0.5,  # Approximation
                        'vega': 0.3,    # Approximation
                    })
            
            # Process puts
            if not opt_chain.puts.empty:
                puts = opt_chain.puts
                for _, row in puts.iterrows():
                    gamma = self._estimate_gamma(
                        row.get('strike', 0),
                        self.get_spx_price() or 5850,
                        row.get('impliedVolatility', 0.15),
                        'put'
                    )
                    
                    options_data.append({
                        'ticker': f"SPX{int(row['strike'])}P",
                        'strike': row['strike'],
                        'type': 'put',
                        'expiration': expiration_str,
                        'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
                        'open_interest': int(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else 0,
                        'implied_volatility': row.get('impliedVolatility', 0.16),
                        'delta': self._estimate_delta(row['strike'], self.get_spx_price() or 5850, 'put'),
                        'gamma': gamma,
                        'theta': -0.5,  # Approximation
                        'vega': 0.3,    # Approximation
                    })

            if not options_data:
                logger.warning("Yahoo Finance returned no options rows")
                return pd.DataFrame()

            df = pd.DataFrame(options_data)
            logger.info(f"Fetched {len(df)} option rows from Yahoo Finance")
            return df

        except Exception as e:
            logger.error(f"Error fetching options from Yahoo Finance: {e}")
            return pd.DataFrame()
            
            if not options_data:
                logger.warning("No options data from Yahoo Finance")
                return self._generate_mock_options_data()
            
            df = pd.DataFrame(options_data)
            logger.info(f"Fetched {len(df)} REAL option contracts from Yahoo Finance ({len(df[df['type']=='call'])} calls, {len(df[df['type']=='put'])} puts)")
            
            return df
            
        except Exception as e:
            logger.error(f"Yahoo Finance options fetch failed: {e}")
            logger.warning("Falling back to mock data")
            return self._generate_mock_options_data()
    
    def _estimate_delta(self, strike: float, spot: float, option_type: str) -> float:
        """Estimate delta based on moneyness.
        
        Args:
            strike: Strike price
            spot: Current spot price
            option_type: 'call' or 'put'
            
        Returns:
            Estimated delta
        """
        moneyness = strike / spot
        
        if option_type == 'call':
            if moneyness < 0.95:  # Deep ITM
                return 0.95
            elif moneyness < 0.98:
                return 0.75
            elif moneyness < 1.02:  # ATM
                return 0.50
            elif moneyness < 1.05:
                return 0.25
            else:  # OTM
                return 0.05
        else:  # put
            if moneyness > 1.05:  # Deep ITM
                return -0.95
            elif moneyness > 1.02:
                return -0.75
            elif moneyness > 0.98:  # ATM
                return -0.50
            elif moneyness > 0.95:
                return -0.25
            else:  # OTM
                return -0.05
    
    def _estimate_gamma(self, strike: float, spot: float, iv: float, option_type: str) -> float:
        """Estimate gamma - highest at ATM, decreases with distance.
        
        Args:
            strike: Strike price
            spot: Current spot price
            iv: Implied volatility
            option_type: 'call' or 'put'
            
        Returns:
            Estimated gamma
        """
        distance = abs(strike - spot)
        # Gamma peaks at ATM and decays exponentially
        gamma = 0.002 * np.exp(-distance / 40) * (1 + iv)
        return gamma
    
    def _generate_mock_options_data(self) -> pd.DataFrame:
        """Generate realistic mock options data for testing.
        
        Returns:
            DataFrame with mock options data
        """
        logger.info("Generating mock options data for testing...")
        
        # Get current SPX price (or use default)
        spx_price = self.get_spx_price()
        if spx_price is None:
            spx_price = 5850.0  # Default value
            logger.info(f"Using default SPX price: {spx_price}")
        
        # Generate strikes around current price
        strikes = np.arange(
            spx_price - 100,
            spx_price + 100,
            5
        )
        
        options_data = []
        
        for strike in strikes:
            # Distance from current price affects volume and OI
            distance = abs(strike - spx_price)
            
            # Calls
            call_volume = int(max(100, 1000 * np.exp(-distance / 50)))
            call_oi = int(call_volume * np.random.uniform(2, 5))
            call_gamma = 0.001 * np.exp(-distance / 30)
            
            options_data.append({
                'ticker': f'SPX{int(strike)}C',
                'strike': strike,
                'type': 'call',
                'expiration': date.today().isoformat(),
                'volume': call_volume,
                'open_interest': call_oi,
                'implied_volatility': 0.15 + distance / 1000,
                'delta': max(0.01, 1 - distance / 200) if strike > spx_price else max(0.5, 0.99 - distance / 100),
                'gamma': call_gamma,
                'theta': -0.5,
                'vega': 0.3,
            })
            
            # Puts
            put_volume = int(max(100, 1200 * np.exp(-distance / 50)))
            put_oi = int(put_volume * np.random.uniform(2, 5))
            put_gamma = 0.001 * np.exp(-distance / 30)
            
            options_data.append({
                'ticker': f'SPX{int(strike)}P',
                'strike': strike,
                'type': 'put',
                'expiration': date.today().isoformat(),
                'volume': put_volume,
                'open_interest': put_oi,
                'implied_volatility': 0.16 + distance / 1000,
                'delta': -max(0.01, 1 - distance / 200) if strike < spx_price else -max(0.5, 0.99 - distance / 100),
                'gamma': put_gamma,
                'theta': -0.5,
                'vega': 0.3,
            })
        
        df = pd.DataFrame(options_data)
        logger.info(f"Generated {len(df)} mock option contracts (TESTING MODE)")
        
        return df
    
    def filter_options_by_range(self, df: pd.DataFrame, current_price: float) -> pd.DataFrame:
        """Filter options to strikes within specified range of current price.
        
        Args:
            df: Options DataFrame
            current_price: Current SPX price
            
        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df
        
        range_pct = config.strike_range_percent / 100
        lower_bound = current_price * (1 - range_pct)
        upper_bound = current_price * (1 + range_pct)
        
        filtered = df[
            (df['strike'] >= lower_bound) & 
            (df['strike'] <= upper_bound) &
            (df['volume'] >= config.min_volume_threshold)
        ].copy()
        
        logger.info(f"Filtered to {len(filtered)} contracts within ±{config.strike_range_percent}% (${lower_bound:.2f} - ${upper_bound:.2f})")
        
        return filtered
    
    def get_spread(self) -> Optional[float]:
        """Calculate ES-SPX spread.
        
        Returns:
            Spread value (ES - SPX) or None if calculation fails
        """
        spx_price = self.get_spx_price()
        es_price = self.get_es_price()
        
        if spx_price is None or es_price is None:
            logger.error("Could not calculate spread - missing price data")
            return None
        
        spread = es_price - spx_price
        logger.info(f"ES-SPX spread: {spread:.2f} (ES: {es_price:.2f}, SPX: {spx_price:.2f})")
        
        return spread
    
    def save_data(self, df: pd.DataFrame, filename: str):
        """Save options data to CSV.
        
        Args:
            df: DataFrame to save
            filename: Output filename
        """
        filepath = config.data_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"Data saved to {filepath}")
