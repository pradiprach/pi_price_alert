import logging
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from database import init_db, get_cryptos, add_crypto, delete_crypto, update_crypto_prices, update_crypto_status

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
_raw_origins     = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS  = [o.strip() for o in _raw_origins.split(",") if o.strip()]
CORS(app, supports_credentials=True, origins=ALLOWED_ORIGINS)

CRYPTOS = {}
REQUEST_TIMEOUT = 10

def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_crypto_price(crypto_name, exchange):
    base_url = f"https://api.coinmarketcap.com/data-api/v3/cryptocurrency/market-pairs/latest?slug={crypto_name.lower()}&start=1&limit=10&category=spot&centerType=all&sort=cmc_rank_advanced&direction=desc&spotUntracked=true"
    try:
        session = get_session()
        response = session.get(url=base_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        for market in response.json()['data']['marketPairs']:
            if market['exchangeName'].lower() == exchange.lower():
                return float(market['price'])
        return 0
    except requests.RequestException as e:
        logger.error(f"Failed to fetch price for {crypto_name}: {e}")
        raise
    except (ValueError, KeyError) as e:
        logger.error(f"Invalid data for {crypto_name}: {e}")
        raise

def load_cryptos():
    global CRYPTOS
    CRYPTOS = get_cryptos()


def send_telegram_msg(crypto_name, curr_price, action):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.warning("Telegram credentials not configured")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    message = f"{action} {crypto_name} with current price: {curr_price}"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        session = get_session()
        response = session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info(f"Telegram alert sent: {action} {crypto_name}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def fetch_with_price(crypto):
    crypto_copy = crypto.copy()
    try:
        crypto_copy["current_price"] = get_crypto_price(crypto["name"])
    except Exception:
        crypto_copy["current_price"] = None
    return crypto_copy


def check_crypto():
    logger.info("Started Running scheduled task")
    for crypto in CRYPTOS:
        if crypto["status"] == 0:
            continue
        try:
            current_price = get_crypto_price(crypto["name"])
            if current_price >= crypto["sell_price"]:
                send_telegram_msg(crypto["name"], current_price, "SELL")
            elif crypto["buy_price"] <= current_price:
                send_telegram_msg(crypto["name"], current_price, "BUY")
        except Exception as e:
            logger.error(f"Error processing {crypto['name']}: {e}")
            continue
    logger.info("Finished Running scheduled task")


def create_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=check_crypto,
        trigger=CronTrigger(minute="*/5"),
        id="movie_job",
        replace_existing=True
    )

    scheduler.start()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status"    : "ok"
    })


@app.route('/crypto', methods=['POST'])
def add_crypto_entry():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
        
    name = data.get('name')
    buy_price = data.get('buy_price')
    sell_price = data.get('sell_price')
    exchange = data.get('exchange')

    if not name or buy_price is None or sell_price is None or exchange is None:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        buy_price = float(buy_price)
        sell_price = float(sell_price)
        if buy_price < 0 or sell_price < 0:
            return jsonify({'error': 'Prices must be positive'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid price format'}), 400

    try:
        add_crypto(name, sell_price, buy_price, exchange)
        load_cryptos()
        return jsonify({'message': 'Crypto added successfully'}), 201
    except Exception as e:
        logger.error(f"Add crypto error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/crypto/prices/<int:id>', methods=['PUT'])
def update_crypto_entry_values(id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    name = data.get('name')
    buy_price = float(data.get('buy_price'))
    sell_price = float(data.get('sell_price'))
    exchange = data.get('exchange')

    if buy_price is None or sell_price is None or exchange is None:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        update_crypto_prices(id, name, buy_price, sell_price, exchange)
        load_cryptos()
        return jsonify({'message': 'Crypto updated successfully'}), 200
    except Exception as e:
        logger.error(f"Update crypto error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/crypto/<int:id>', methods=['PUT'])
def update_crypto_entry_status(id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
        
    status = data.get('status')

    if status is not None:
        if isinstance(status, str) and status.isdigit():
            status = int(status)
        if status not in [0, 1]:
            return jsonify({'error': 'Status must be 0 or 1'}), 400
    else:
        return jsonify({'error': 'Status must be 0 or 1'}), 400

    try:
        update_crypto_status(id, status)
        load_cryptos()
        return jsonify({'message': 'Crypto updated successfully'}), 200
    except Exception as e:
        logger.error(f"Update crypto error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/crypto/<int:id>', methods=['DELETE'])
def remove_crypto(id):
    try:
        delete_crypto(id)
        return jsonify({'message': 'Crypto deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Delete crypto error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/cryptos', methods=['GET'])
def get_all_cryptos():
    try:
        if request.args.get("refresh"):
            load_cryptos()
        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(fetch_with_price, CRYPTOS))
        return jsonify(results), 200
    except Exception as e:
        logger.error(f"Get cryptos error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500


init_db()
load_cryptos()
create_scheduler()

if __name__ == '__main__':
    try:
        logger.info("Application started successfully")
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5002)), debug=False)
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        raise
