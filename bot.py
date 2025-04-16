# bot.py

import asyncio
import logging
import pandas as pd
from ta.momentum import RSIIndicator
from kraken.spot import SpotClient
from config import (
    API_KEY, API_SECRET,
    TRADING_PAIRS, TRADE_VOLUME,
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KrakenRSIBot:
    def __init__(self, api_key, api_secret):
        self.client = SpotClient(key=api_key, secret=api_secret)

    def get_ohlc_data(self, pair):
        """
        Obtiene datos OHLC del par dado (últimos 100 candles de 1 minuto)
        """
        url_pair = pair.replace('/', '')
        response = self.client.request('GET', f'/0/public/OHLC?pair={url_pair}&interval=1')
        ohlc_raw = response['result'][list(response['result'].keys())[0]]
        df = pd.DataFrame(ohlc_raw, columns=[
            'time', 'open', 'high', 'low', 'close', 'vwap',
            'volume', 'count'
        ])
        df['close'] = pd.to_numeric(df['close'])
        return df

    def calculate_rsi(self, df):
        """
        Calcula el RSI a partir de un DataFrame de precios
        """
        rsi = RSIIndicator(close=df['close'], window=RSI_PERIOD)
        return rsi.rsi().iloc[-1]  # Retorna el valor más reciente

    def place_order(self, pair, side):
        """
        Realiza una orden de compra o venta
        """
        logger.info(f"Ejecutando orden {side.upper()} en {pair}")
        order = self.client.request('POST', '/0/private/AddOrder', data={
            'pair': pair.replace('/', ''),
            'type': side,
            'ordertype': 'market',
            'volume': TRADE_VOLUME
        })
        logger.info(f"Orden ejecutada: {order}")
        return order

    async def run(self):
        """
        Loop principal del bot
        """
        while True:
            for pair in TRADING_PAIRS:
                try:
                    df = self.get_ohlc_data(pair)
                    rsi = self.calculate_rsi(df)
                    logger.info(f"{pair} - RSI: {rsi:.2f}")

                    if rsi < RSI_OVERSOLD:
                        logger.info(f"{pair} - Señal de COMPRA (RSI < {RSI_OVERSOLD})")
                        self.place_order(pair, 'buy')
                    elif rsi > RSI_OVERBOUGHT:
                        logger.info(f"{pair} - Señal de VENTA (RSI > {RSI_OVERBOUGHT})")
                        self.place_order(pair, 'sell')
                    else:
                        logger.info(f"{pair} - RSI neutro, sin operación")

                except Exception as e:
                    logger.error(f"Error con {pair}: {e}")

            await asyncio.sleep(60)  # Esperar 1 minuto antes de volver a analizar

if __name__ == "__main__":
    bot = KrakenRSIBot(API_KEY, API_SECRET)
    asyncio.run(bot.run())