"""Vercel Serverless Function - Calculate gamma levels."""
from http.server import BaseHTTPRequestHandler
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime


def get_spx_price():
    """Get current SPX price."""
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return 5850.0


def generate_mock_options(spx_price):
    """Generate mock options data."""
    strikes = np.arange(spx_price - 100, spx_price + 100, 5)
    options_data = []
    
    for strike in strikes:
        distance = abs(strike - spx_price)
        
        # Calls
        call_volume = int(max(100, 1000 * np.exp(-distance / 50)))
        call_oi = int(call_volume * np.random.uniform(2, 5))
        call_gamma = 0.001 * np.exp(-distance / 30)
        
        options_data.append({
            'strike': strike,
            'type': 'call',
            'volume': call_volume,
            'open_interest': call_oi,
            'gamma': call_gamma,
        })
        
        # Puts
        put_volume = int(max(100, 1200 * np.exp(-distance / 50)))
        put_oi = int(put_volume * np.random.uniform(2, 5))
        put_gamma = 0.001 * np.exp(-distance / 30)
        
        options_data.append({
            'strike': strike,
            'type': 'put',
            'volume': put_volume,
            'open_interest': put_oi,
            'gamma': put_gamma,
        })
    
    return pd.DataFrame(options_data)


def calculate_gamma_levels(df, spx_price):
    """Calculate gamma levels."""
    # Calculate dealer gamma
    df['dealer_gamma'] = -df['open_interest'] * df['gamma'] * 100
    df['call_gamma'] = df.apply(lambda r: r['dealer_gamma'] if r['type'] == 'call' else 0, axis=1)
    df['put_gamma'] = df.apply(lambda r: r['dealer_gamma'] if r['type'] == 'put' else 0, axis=1)
    
    # Aggregate by strike
    agg_df = df.groupby('strike').agg({
        'dealer_gamma': 'sum',
        'call_gamma': 'sum',
        'put_gamma': 'sum',
        'volume': 'sum',
        'open_interest': 'sum'
    }).reset_index()
    
    agg_df['net_gamma'] = agg_df['call_gamma'] + agg_df['put_gamma']
    
    # Find key levels
    levels = {}
    
    # Put Wall
    put_strikes = agg_df[agg_df['strike'] <= spx_price]
    if not put_strikes.empty:
        put_wall_idx = put_strikes['put_gamma'].abs().idxmax()
        levels['put_wall'] = float(put_strikes.loc[put_wall_idx, 'strike'])
    
    # Call Wall
    call_strikes = agg_df[agg_df['strike'] >= spx_price]
    if not call_strikes.empty:
        call_wall_idx = call_strikes['call_gamma'].abs().idxmax()
        levels['call_wall'] = float(call_strikes.loc[call_wall_idx, 'strike'])
    
    # Gamma Flip
    near_price = agg_df[(agg_df['strike'] >= spx_price * 0.99) & (agg_df['strike'] <= spx_price * 1.01)]
    if not near_price.empty:
        gamma_flip_idx = near_price['net_gamma'].abs().idxmin()
        levels['gamma_flip'] = float(near_price.loc[gamma_flip_idx, 'strike'])
    
    # Determine regime
    regime = "short_gamma" if spx_price > levels.get('gamma_flip', spx_price) else "long_gamma"
    
    return levels, regime, agg_df


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_GET(self):
        """Handle GET request."""
        try:
            # Get SPX price
            spx_price = get_spx_price()
            
            # Get ES price for spread
            es = yf.Ticker("ES=F")
            es_data = es.history(period="1d", interval="1m")
            es_price = float(es_data['Close'].iloc[-1]) if not es_data.empty else spx_price + 2
            spread = es_price - spx_price
            
            # Generate options and calculate levels
            options_df = generate_mock_options(spx_price)
            levels, regime, agg_df = calculate_gamma_levels(options_df, spx_price)
            
            # Convert to ES
            es_levels = {k: v + spread for k, v in levels.items()}
            
            # Get gamma profile for chart
            chart_data = agg_df.sort_values('strike').to_dict('records')
            
            response = {
                'success': True,
                'data': {
                    'spx_price': spx_price,
                    'es_price': es_price,
                    'spread': spread,
                    'regime': regime,
                    'levels_spx': levels,
                    'levels_es': es_levels,
                    'gamma_profile': chart_data[:50],  # Limit data
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            error_response = {
                'success': False,
                'error': str(e)
            }
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())
