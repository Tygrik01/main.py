from flask import Flask, request, jsonify
import ccxt
import os

app = Flask(__name__)

exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'timeout': 15000,
})

def webhook_logic(data):
    try:
        action = data.get('action', '').lower()
        symbol = data.get('symbol', '').upper()
        quantity = float(data.get('quantity', 0))

        if not action or not symbol or quantity <= 0:
            return {'error': 'Missing required fields'}, 400

        if action == 'buy':
            final_side = 'BUY'
            order = exchange.create_market_order(symbol, final_side, quantity)
            return {'status': 'Futures position opened', 'order': order}, 200

        elif action == 'sell':
            close_side = 'SELL' if quantity > 0 else 'BUY'
            params = {'reduceOnly': True}
            order = exchange.create_market_order(symbol, close_side, abs(quantity), params=params)
            return {'status': 'Futures position closed', 'order': order}, 200

    except ccxt.OrderNotFillable as e:
        if 'reduceOnly' in str(e):
            return {'status': 'No open position to close'}, 200
        return {'error': str(e)}, 500
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    result, status_code = webhook_logic(data)
    return jsonify(result), status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
