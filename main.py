from flask import Flask, request, jsonify
import ccxt
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Инициализация биржи
exchange = ccxt.binance({
    'apiKey': "DPyTFfPEY6SPfOcmjfMy935MPPZ4m8FFDWvqAZKWwzmcb0Ie1enbbdELv3FT996L",
    'secret': "cY6e7HOG8L10J7QhfjAWk3VVXK05lI6jj3CY5LdxBHFfD4BDpBnxzNQzeiReR5jm",
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

def get_position(symbol):
    """Получить текущую позицию"""
    try:
        positions = exchange.fetch_positions([symbol])
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                return pos
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения позиции: {e}")
        return None

@app.route('/webhook', methods=['POST'])
@app.route('/mebhook', methods=['POST'])
@app.route('/nebhook', methods=['POST'])
def webhook():
    logger.info("🔧 Получен вебхук запрос")
    
    try:
        data = request.get_json(force=True)
        logger.info(f"📨 Данные: {data}")

        if not data:
            return jsonify({'error': 'No data received'}), 400

        # Исправляем опечатку: 'syntax' → 'symbol'
        action = data.get('action', '').lower()
        symbol = data.get('symbol') or data.get('syntax', '').upper()  # Исправление здесь!
        quantity = data.get('quantity', 0)
        position_size = data.get('position_size', 0)

        logger.info(f"🔍 Action: {action}, Symbol: {symbol}, Quantity: {quantity}, Position_size: {position_size}")

        # Валидация
        if not action:
            return jsonify({'error': 'Missing action field'}), 400
        if not symbol:
            return jsonify({'error': 'Missing symbol field'}), 400
        
        # Определяем количество для ордера
        if position_size and float(position_size) != 0:
            order_quantity = abs(float(position_size))
        else:
            order_quantity = float(quantity)

        if order_quantity <= 0:
            return jsonify({'error': 'Invalid quantity'}), 400

        # Логика торговли
        if action == 'buy':
            # Открываем лонг позицию
            order = exchange.create_market_order(symbol, 'buy', order_quantity)
            logger.info(f"🟢 Открыта лонг позиция: {order}")
            return jsonify({
                'status': 'success',
                'message': 'Long position opened',
                'order_id': order['id']
            }), 200

        elif action == 'sell':
            # Сначала проверяем есть ли открытая позиция
            current_position = get_position(symbol)
            
            if current_position and float(current_position['contracts']) != 0:
                # Закрываем позицию
                contracts = float(current_position['contracts'])
                close_side = 'sell' if contracts > 0 else 'buy'
                
                params = {'reduceOnly': True}
                order = exchange.create_market_order(symbol, close_side, abs(contracts), params=params)
                logger.info(f"🔴 Закрыта позиция: {order}")
                return jsonify({
                    'status': 'success', 
                    'message': 'Position closed',
                    'order_id': order['id']
                }), 200
            else:
                # Открываем шорт позицию
                order = exchange.create_market_order(symbol, 'sell', order_quantity)
                logger.info(f"🟢 Открыта шорт позиция: {order}")
                return jsonify({
                    'status': 'success',
                    'message': 'Short position opened', 
                    'order_id': order['id']
                }), 200

        else:
            return jsonify({'error': f'Invalid action: {action}'}), 400

    except ccxt.InsufficientFunds as e:
        logger.error(f"💸 Недостаточно средств: {e}")
        return jsonify({'error': 'Insufficient funds'}), 400
    except ccxt.ExchangeError as e:
        logger.error(f"🏦 Ошибка биржи: {e}")
        return jsonify({'error': f'Exchange error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"💥 Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'status': 'running'}), 200

@app.route('/position/<symbol>', methods=['GET'])
def check_position(symbol):
    """Проверить позицию"""
    try:
        position = get_position(symbol.upper())
        if position:
            return jsonify({'position': position}), 200
        else:
            return jsonify({'status': 'No position found'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
