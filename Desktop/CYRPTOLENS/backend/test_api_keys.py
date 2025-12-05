"""
Test script to check API key requirements and data fetching.
"""
import asyncio
import httpx
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from shared.data_providers.interfaces import Timeframe


async def test_coingecko():
    """Test CoinGecko API without API key."""
    print("=" * 60)
    print("TEST 1: CoinGecko API (Market Data)")
    print("=" * 60)
    
    provider = CoinGeckoMarketDataProvider()
    
    try:
        # Test market overview
        print("\n[TEST] Market Overview...")
        overview = await provider.get_market_overview()
        print(f"[OK] Total Market Cap: ${overview.total_market_cap:,.0f} USD")
        print(f"[OK] Total Volume 24h: ${overview.total_volume_24h:,.0f} USD")
        print(f"[OK] BTC Dominance: {overview.btc_dominance:.2f}%")
        print(f"[OK] ETH Dominance: {overview.eth_dominance:.2f}%")
        
        # Test coin list
        print("\n[TEST] Coin List (first 5 coins)...")
        coins = await provider.get_coin_list(limit=5)
        for coin in coins:
            print(f"  [OK] {coin.symbol}: {coin.name} (Gecko ID: {coin.gecko_id})")
        
        # Test prices
        print("\n[TEST] Price Test (BTC, ETH, BNB)...")
        prices = await provider.get_prices_for_symbols(["bitcoin", "ethereum", "binancecoin"])
        for symbol, price_data in prices.items():
            print(f"  [OK] {symbol}: ${price_data.price:,.2f} USD (24h: {price_data.change_24h:+.2f}%)")
        
        # Test trending
        print("\n[TEST] Trending Coins...")
        trending = await provider.get_trending_coins()
        for coin in trending[:3]:
            print(f"  [OK] {coin.symbol}: {coin.name}")
        
        print("\n[SUCCESS] CoinGecko API calisiyor! API key GEREKMIYOR (opsiyonel)")
        
    except Exception as e:
        print(f"\n[ERROR] CoinGecko API hatasi: {e}")
    
    finally:
        await provider.close()


async def test_binance():
    """Test Binance API without API key."""
    print("\n" + "=" * 60)
    print("TEST 2: Binance API (OHLC Data)")
    print("=" * 60)
    
    provider = BinanceOhlcDataProvider()
    
    try:
        # Test OHLC for BTC
        print("\n[TEST] BTC OHLC (1 day timeframe, last 5 candles)...")
        candles = await provider.get_ohlc_for_symbol("BTC", Timeframe.DAY_1, limit=5)
        
        if candles:
            print(f"[OK] {len(candles)} mum verisi alindi")
            for i, candle in enumerate(candles[-3:], 1):  # Son 3 mum
                print(f"  {i}. Tarih: {candle.timestamp.strftime('%Y-%m-%d %H:%M')}")
                print(f"     Open: ${candle.open:,.2f} | High: ${candle.high:,.2f} | Low: ${candle.low:,.2f} | Close: ${candle.close:,.2f}")
        else:
            print("[WARNING] Veri alinamadi")
        
        # Test symbol support
        print("\n[TEST] Symbol Support...")
        is_btc_supported = await provider.is_symbol_supported("BTC")
        is_eth_supported = await provider.is_symbol_supported("ETH")
        print(f"  [OK] BTC destekleniyor: {is_btc_supported}")
        print(f"  [OK] ETH destekleniyor: {is_eth_supported}")
        
        print("\n[SUCCESS] Binance API calisiyor! API key GEREKMIYOR (public endpoints)")
        
    except Exception as e:
        print(f"\n[ERROR] Binance API hatasi: {e}")
    
    finally:
        await provider.close()


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CRYPTO LENS - API KEY VE VERİ ÇEKİM TESTİ")
    print("=" * 60)
    print("\nBu test, API key olmadan veri çekimini test eder.")
    print("CoinGecko ve Binance public API'lerini kullanır.\n")
    
    await test_coingecko()
    await test_binance()
    
    print("\n" + "=" * 60)
    print("SONUC")
    print("=" * 60)
    print("""
[OK] CoinGecko API Key: OPSIYONEL
   - API key olmadan calisir (free tier)
   - API key varsa rate limit artar
   - .env dosyasinda COINGECKO_API_KEY bos birakilabilir

[OK] Binance API Key: GEREKMIYOR
   - Public endpoints kullaniliyor (/klines, /exchangeInfo)
   - API key ve secret hic kullanilmiyor
   - .env dosyasinda BINANCE_API_KEY ve BINANCE_API_SECRET bos birakilabilir

[NOTE] ONERI:
   - Su anda API key'ler OPSIYONEL
   - Eger rate limit sorunu yasarsaniz CoinGecko API key alabilirsiniz
   - Binance icin API key gerekmez (public endpoints)
    """)


if __name__ == "__main__":
    asyncio.run(main())

