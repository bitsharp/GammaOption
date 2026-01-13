"""Vercel Serverless Function - Get SPX and ES prices."""
from http.server import BaseHTTPRequestHandler
import json
import yfinance as yf
from datetime import datetime


def get_spx_price():
    """Get current SPX price from yfinance."""
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return None


def get_es_price():
    """Get current ES price from yfinance."""
    try:
        es = yf.Ticker("ES=F")
        data = es.history(period="1d", interval="1m")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return None


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_GET(self):
        """Handle GET request."""
        try:
            spx_price = get_spx_price()
            es_price = get_es_price()
            
            spread = None
            if spx_price and es_price:
                spread = es_price - spx_price
            
            response = {
                'success': True,
                'data': {
                    'spx': spx_price,
                    'es': es_price,
                    'spread': spread,
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
