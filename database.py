from datetime import datetime
import logging
import pytz
from supabase import create_client, Client
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    """
    Supabase does not support schema creation via SDK.
    This function is kept only for compatibility.
    """
    pass

def add_crypto(name: str, sell_price: float, buy_price: float, exchange: str):
    """Add a new crypto to the database."""
    try:
        response = supabase.table("cryptos").insert({
            "name": name,
            "sell_price": sell_price,
            "buy_price": buy_price,
            "exchange": exchange,
            "status": 1
        }).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error adding crypto: {e}")
        raise


def update_crypto_status(id: int, status: int):
    """Update crypto status."""
    try:
        supabase.table("cryptos").update({
            "status": status
        }).eq("id", id).execute()
    except Exception as e:
        logger.error(f"Error updating crypto status: {e}")
        raise


def update_crypto_prices(id: int, name: str, buy_price: float, sell_price: float, exchange: str):
    """Update cryptos status."""
    try:
        supabase.table("cryptos").update({
            "name": name,
            "exchange": exchange,
            "buy_price": buy_price,
            "sell_price": sell_price
        }).eq("id", id).execute()
    except Exception as e:
        logger.error(f"Error updating crypto status: {e}")
        raise


def get_cryptos():
    """Get all cryptos from the database."""
    try:
        response = supabase.table("cryptos").select("*").order("name", desc=False).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching cryptos: {e}")
        raise

def delete_crypto(id: int) -> bool:
    """
    Delete a crypto record by id.
    """
    supabase.table("cryptos").delete().eq("id", id).execute()
    return True