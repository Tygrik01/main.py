from flask import Flask, request, jsonify
import ccxt
import os
import time

app = Flask(__name__)

# Настройка CCXT для Binance фьючерсов
def init_exchange():
    try:
        exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET'),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
            },
            'sandbox': False,  # Режим реальной торговли
        })
        
        # Тестируем подключение
        exchange.fetch_balance()
        print("✅ Binance подключение успешно")
        return exchange
    except Exception as e:
        print(f"❌ Ошибка подключения к Binance: {e}")
        return None

exchange = init_exchange()

@app.route('/webhook', methods=['POST'])
def webhook():
    if exchange is None:
        return jsonify({'error': 'Exchange not initialized'}), 500
        
    print("🔧 Получен вебхук")
    
    try:
        data = request.get_json(force=True)
        print(f"📨 Данные: {data}")

        if not data:
            return jsonify({'error': 'No data received'}), 400

        # Извлекаем данные
        action = data.get('action', '').lower()
        symbol = data.get('symbol', '').upper().replace('PERP', '').replace(':', '')
        quantity = float(data.get('quantity', 0))

        print(f"🔍 Action: {action}, Symbol: {symbol}, Quantity: {quantity}")

        if not action or not symbol or quantity <= 0:
            return jsonify({'error': 'Invalid parameters'}), 400

        # Простая логика: buy = открыть лонг, sell = открыть шорт
        if action in ['buy', 'sell']:
            side = 'buy' if action == 'buy' else 'sell'
            
            # Создаем рыночный ордер
            order = exchange.create_market_order(symbol, side, quantity)
            print(f"✅ Ордер исполнен: {order}")
            
            return jsonify({
                'status': 'success', 
                'message': f'{side.upper()} order executed',
                'order_id': order['id']
            }), 200
        else:
            return jsonify({'error': 'Invalid action'}), 400

    except ccxt.InsufficientFunds as e:
        print(f"💸 Недостаточно средств: {e}")
        return jsonify({'error': 'Insufficient funds'}), 400
    except ccxt.NetworkError as e:
        print(f"🌐 Ошибка сети: {e}")
        return jsonify({'error': 'Network error'}), 500
    except ccxt.ExchangeError as e:
        print(f"🏦 Ошибка биржи: {e}")
        return jsonify({'error': f'Exchange error: {str(e)}'}), 500
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/nebhook', methods=['POST'])
def nebhook():
    """Альтернативный endpoint"""
    return webhook()

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'running', 
        'exchange': 'initialized' if exchange else 'not initialized'
    }), 200

@app.route('/balance', methods=['GET'])
def get_balance():
    """Проверить баланс"""
    if exchange is None:
        return jsonify({'error': 'Exchange not initialized'}), 500
        
    try:
        balance = exchange.fetch_balance()
        return jsonify({
            'usdt': balance['USDT'] if 'USDT' in balance else 'N/A',
            'total': balance['total']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
