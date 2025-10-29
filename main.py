from flask import Flask, request, jsonify
import ccxt
import os

app = Flask(__name__)

# Настройка CCXT для Binance фьючерсов (USDT-M)
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'timeout': 15000,
})

print("Код загружен успешно. Инициализация сервера...")

# Проверка подключения
try:
    balance = exchange.fetch_balance()
    print(f"✅ Клиент готов! USDT баланс: {balance['USDT']['free'] if 'USDT' in balance else 'N/A'}")
except Exception as e:
    print(f"⚠️ Предупреждение: {e}")

# Функция для получения текущей позиции по символу
def get_position(symbol):
    try:
        positions = exchange.fetch_positions([symbol])
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                return pos
        return None
    except Exception as e:
        print(f"❌ Ошибка получения позиции: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🔧 Получен запрос на /webhook")
    
    try:
        # Пробуем разные форматы данных
        data = request.get_json(force=True, silent=True)
        
        if not data:
            raw_data = request.data.decode('utf-8')
            print(f"⚠️ Сырые данные: {raw_data}")
            # Пробуем парсить как JSON вручную
            try:
                data = json.loads(raw_data)
            except:
                return jsonify({'error': 'No valid JSON data received'}), 400

        print(f"✅ Получены данные: {data}")

        # Извлекаем данные из TradingView алерта
        action = data.get('action', '').lower()  # "buy" или "sell"
        symbol = data.get('symbol', '').upper().replace('PERP', '').replace('BINANCE:', '')  # Очищаем символ
        quantity = data.get('quantity', 0)
        position_size = data.get('position_size', 0)  # Новое поле из алерта

        # Если quantity нет, используем position_size
        if not quantity or quantity == 0:
            quantity = abs(float(position_size))
        
        quantity = float(quantity)

        print(f"📊 Извлечено: action={action}, symbol={symbol}, quantity={quantity}, position_size={position_size}")

        if not action or not symbol or quantity <= 0:
            return jsonify({'error': 'Missing required fields'}), 400

        # Логика для TradingView стратегий
        if action == 'buy':
            # Открываем лонг позицию
            order = exchange.create_market_order(symbol, 'buy', quantity)
            print(f"🟢 Открыта лонг позиция: {order}")
            return jsonify({'status': 'Long position opened', 'order': order}), 200

        elif action == 'sell':
            # Закрываем позицию или открываем шорт
            current_pos = get_position(symbol)
            
            if current_pos and float(current_pos['contracts']) != 0:
                # Закрываем существующую позицию
                contracts = float(current_pos['contracts'])
                close_side = 'sell' if contracts > 0 else 'buy'
                
                params = {'reduceOnly': True}
                order = exchange.create_market_order(symbol, close_side, abs(contracts), params=params)
                print(f"🔴 Закрыта позиция: {order}")
                return jsonify({'status': 'Position closed', 'order': order}), 200
            else:
                # Открываем шорт позицию
                order = exchange.create_market_order(symbol, 'sell', quantity)
                print(f"🟢 Открыта шорт позиция: {order}")
                return jsonify({'status': 'Short position opened', 'order': order}), 200

        else:
            return jsonify({'error': f'Invalid action: {action}'}), 400

    except ccxt.AuthenticationError as e:
        print(f"🔒 Ошибка аутентификации: {e}")
        return jsonify({'error': 'API key error'}), 500
    except ccxt.InsufficientFunds as e:
        print(f"💸 Недостаточно средств: {e}")
        return jsonify({'error': 'Insufficient funds'}), 500
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/nebhook', methods=['POST'])
def nebhook():
    """Альтернативный endpoint для тестирования"""
    return webhook()

@app.route('/', methods=['GET', 'HEAD'])
def health_check():
    return jsonify({'status': 'Webhook server is running'}), 200

@app.route('/position/<symbol>', methods=['GET'])
def get_position_route(symbol):
    """Проверить позицию по символу"""
    try:
        position = get_position(symbol.upper())
        if position:
            return jsonify({'position': position}), 200
        else:
            return jsonify({'status': 'No position found'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
