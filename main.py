from flask import Flask, request, jsonify
import os
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
@app.route('/mebhook', methods=['POST'])
def webhook():
    logger.info("🔧 Получен вебхук запрос")
    
    try:
        # Логируем заголовки
        logger.info(f"📨 Headers: {dict(request.headers)}")
        logger.info(f"📨 Content-Type: {request.content_type}")
        
        # Получаем сырые данные
        raw_data = request.get_data(as_text=True)
        logger.info(f"📨 Raw data: {raw_data}")
        
        # Пробуем распарсить JSON
        try:
            data = request.get_json(force=True)
            logger.info(f"✅ JSON данные: {data}")
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
            return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
        
        if not data:
            logger.error("❌ Пустые данные")
            return jsonify({'error': 'No data received'}), 400

        # Простая проверка полей
        action = data.get('action')
        symbol = data.get('symbol')
        quantity = data.get('quantity')
        
        logger.info(f"🔍 Action: {action}, Symbol: {symbol}, Quantity: {quantity}")

        # Валидация
        if not action:
            return jsonify({'error': 'Missing action field'}), 400
        if not symbol:
            return jsonify({'error': 'Missing symbol field'}), 400
        if not quantity:
            return jsonify({'error': 'Missing quantity field'}), 400

        # Преобразуем quantity в число
        try:
            quantity = float(quantity)
        except (TypeError, ValueError) as e:
            return jsonify({'error': f'Invalid quantity: {quantity}'}), 400

        # Возвращаем успешный ответ
        response = {
            'status': 'success',
            'message': f'Received {action} order for {symbol}',
            'quantity': quantity,
            'action': action
        }
        
        logger.info(f"✅ Успешный ответ: {response}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'status': 'running', 'message': 'Webhook server is working!'}), 200

@app.route('/test', methods=['POST'])
def test_webhook():
    """Endpoint для тестирования"""
    test_data = {
        'action': 'buy',
        'symbol': 'BTCUSDT',
        'quantity': 0.001
    }
    return jsonify({'test_data': test_data, 'message': 'Use this format for webhook'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
