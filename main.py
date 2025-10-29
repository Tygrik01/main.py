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
    print("🔹 Начало обработки запроса")
    try:
        # Проверяем, что data — это словарь
        if not isinstance(data, dict):
            print(f"❌ Ошибка: data не словарь, тип: {type(data)}")
            return {'error': 'Invalid data format'}, 400

        action = data.get('action', '').lower()
        symbol = data.get('symbol', '').upper()
        quantity = data.get('quantity')

        # Проверяем, что quantity — число
        if quantity is None:
            print("❌ Ошибка: quantity отсутствует")
            return {'error': 'Missing quantity'}, 400

        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            print(f"❌ Ошибка: quantity не число: {quantity}")
            return {'error': 'Quantity must be a number'}, 400

        if not action or not symbol or quantity <= 0:
            print("❌ Ошибка: отсутствуют обязательные поля")
            return {'error': 'Missing required fields (action, symbol, quantity)'}, 400

        # Маппинг: buy → open, sell → close
        if action == 'buy':
            final_action = 'open'
            final_side = 'BUY'
        elif action == 'sell':
            final_action = 'close'
        else:
            print(f"❌ Ошибка: неверное действие: {action}")
            return {'error': f'Invalid action: {action}. Expect buy/sell'}, 400

        print(f"🔹 Действие: {final_action}, сторона: {final_side}")

        # Ордер для фьючерсов через CCXT
        if final_action == 'open':
            print("🔹 Открываем позицию...")
            try:
                order = exchange.create_market_order(symbol, final_side, quantity)
                print(f"🟢 Успешно открыта позиция: {order}")
                return {'status': 'Futures position opened', 'order': order}, 200
            except Exception as e:
                print(f"❌ Ошибка при открытии позиции: {e}")
                return {'error': f'Failed to open position: {str(e)}'}, 500

        elif final_action == 'close':
            print("🔹 Пытаемся закрыть позицию без проверки...")
            close_side = 'SELL' if quantity > 0 else 'BUY'
            params = {'reduceOnly': True}
            try:
                order = exchange.create_market_order(symbol, close_side, abs(quantity), params=params)
                print(f"✅ Успешно закрыта позиция: {order}")
                return {'status': 'Futures position closed', 'order': order}, 200
            except Exception as e:
                print(f"❌ Ошибка при закрытии: {e}")
                if 'reduceOnly' in str(e):
                    print("🟡 Позиция не найдена — пропускаем")
                    return {'status': 'No open position to close'}, 200
                return {'error': f'Failed to close position: {str(e)}'}, 500

    except Exception as e:
        print(f"💥 Неожиданная ошибка: {e}")
        return {'error': str(e)}, 500

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    result, status_code = webhook_logic(data)
    return jsonify(result), status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
