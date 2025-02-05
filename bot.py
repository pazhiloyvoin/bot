import ccxt
import telebot
import pandas as pd
import numpy as np
import time
import schedule

# === Настройки ===
TELEGRAM_TOKEN = "7732667394:AAHHy5hBFwPrpM5bZC0V_Y6ueEZ0EyxkaWk"
CHAT_ID = "6803518891"
SYMBOLS = ["BTC/USDT", "ETH/USDT", "ARB/USDT", "MANTA/USDT", "SUI/USDT", "APT/USDT"]
TIMEFRAMES = ["15m", "30m", "1h", "4h", "1d"]

# === Подключение к Telegram ===
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# === Подключение к бирже BingX ===
exchange = ccxt.bingx({"rateLimit": 1000})

# === Функция расчёта индикаторов ===
def calculate_indicators(data):
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["close"] = df["close"].astype(float)

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    df["EMA_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["EMA_26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # Bollinger Bands
    df["SMA_20"] = df["close"].rolling(window=20).mean()
    df["STD_20"] = df["close"].rolling(window=20).std()
    df["BB_upper"] = df["SMA_20"] + (df["STD_20"] * 2)
    df["BB_lower"] = df["SMA_20"] - (df["STD_20"] * 2)

    return df.iloc[-1]  # Возвращаем последнюю строку с индикаторами

# === Функция проверки условий для входа в сделку ===
def check_trade_signals():
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=30)
                indicators = calculate_indicators(ohlcv)

                # Условия входа в сделку
                if indicators["RSI"] < 30 and indicators["MACD"] > indicators["MACD_signal"] and indicators["close"] < indicators["BB_lower"]:
                    message = f"📢 Возможность купить {symbol} на {timeframe}!\n💹 RSI: {indicators['RSI']:.2f}\n📈 MACD: {indicators['MACD']:.4f}\n📉 Bollinger Lower: {indicators['BB_lower']:.2f}"
                    bot.send_message(CHAT_ID, message)

                elif indicators["RSI"] > 70 and indicators["MACD"] < indicators["MACD_signal"] and indicators["close"] > indicators["BB_upper"]:
                    message = f"📢 Возможность продать {symbol} на {timeframe}!\n💹 RSI: {indicators['RSI']:.2f}\n📉 MACD: {indicators['MACD']:.4f}\n📈 Bollinger Upper: {indicators['BB_upper']:.2f}"
                    bot.send_message(CHAT_ID, message)

            except Exception as e:
                print(f"Ошибка для {symbol} ({timeframe}): {e}")

# === Запуск цикла с проверкой раз в 10 минут ===
schedule.every(10).minutes.do(check_trade_signals)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту, запуская задачу по расписани