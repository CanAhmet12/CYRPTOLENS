"""
Symbol Mapping Service.
Maps internal coin symbols to CoinGecko IDs and Binance trading pairs.
Following CryptoLens Data Architecture Specification.
"""
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SymbolMapping:
    """Symbol mapping data."""
    symbol: str  # Internal symbol (e.g., "BTC")
    gecko_id: str  # CoinGecko ID (e.g., "bitcoin")
    binance_pair: Optional[str]  # Binance pair (e.g., "BTCUSDT") or None if not available


class SymbolResolver:
    """
    Symbol Mapping Service.
    Maps internal coin symbols to provider-specific identifiers.
    """
    
    def __init__(self):
        # Common coin mappings
        # Format: "SYMBOL": ("gecko_id", "BINANCE_PAIR")
        self._mappings: Dict[str, Tuple[str, Optional[str]]] = {
            "BTC": ("bitcoin", "BTCUSDT"),
            "ETH": ("ethereum", "ETHUSDT"),
            "SOL": ("solana", "SOLUSDT"),
            "BNB": ("binancecoin", "BNBUSDT"),
            "ADA": ("cardano", "ADAUSDT"),
            "XRP": ("ripple", "XRPUSDT"),
            "DOT": ("polkadot", "DOTUSDT"),
            "DOGE": ("dogecoin", "DOGEUSDT"),
            "MATIC": ("matic-network", "MATICUSDT"),
            "AVAX": ("avalanche-2", "AVAXUSDT"),
            "LINK": ("chainlink", "LINKUSDT"),
            "UNI": ("uniswap", "UNIUSDT"),
            "ATOM": ("cosmos", "ATOMUSDT"),
            "LTC": ("litecoin", "LTCUSDT"),
            "ETC": ("ethereum-classic", "ETCUSDT"),
            "XLM": ("stellar", "XLMUSDT"),
            "ALGO": ("algorand", "ALGOUSDT"),
            "VET": ("vechain", "VETUSDT"),
            "FIL": ("filecoin", "FILUSDT"),
            "TRX": ("tron", "TRXUSDT"),
            "EOS": ("eos", "EOSUSDT"),
            "AAVE": ("aave", "AAVEUSDT"),
            "MKR": ("maker", "MKRUSDT"),
            "COMP": ("compound-governance-token", "COMPUSDT"),
            "SUSHI": ("sushi", "SUSHIUSDT"),
            "YFI": ("yearn-finance", "YFIUSDT"),
            "SNX": ("havven", "SNXUSDT"),
            "CRV": ("curve-dao-token", "CRVUSDT"),
            "1INCH": ("1inch", "1INCHUSDT"),
            "ENJ": ("enjincoin", "ENJUSDT"),
            "MANA": ("decentraland", "MANAUSDT"),
            "SAND": ("the-sandbox", "SANDUSDT"),
            "AXS": ("axie-infinity", "AXSUSDT"),
            "GALA": ("gala", "GALAUSDT"),
            "CHZ": ("chiliz", "CHZUSDT"),
            "FLOW": ("flow", "FLOWUSDT"),
            "NEAR": ("near", "NEARUSDT"),
            "FTM": ("fantom", "FTMUSDT"),
            "ICP": ("internet-computer", "ICPUSDT"),
            "APT": ("aptos", "APTUSDT"),
            "ARB": ("arbitrum", "ARBUSDT"),
            "OP": ("optimism", "OPUSDT"),
            "SUI": ("sui", "SUIUSDT"),
        }
    
    def get_gecko_id(self, symbol: str) -> Optional[str]:
        """Get CoinGecko ID for a symbol."""
        mapping = self._mappings.get(symbol.upper())
        if mapping:
            return mapping[0]
        # Fallback: try lowercase symbol as gecko_id
        return symbol.lower()
    
    def get_binance_pair(self, symbol: str) -> Optional[str]:
        """Get Binance trading pair for a symbol."""
        mapping = self._mappings.get(symbol.upper())
        if mapping:
            return mapping[1]
        # Fallback: try SYMBOLUSDT format
        return f"{symbol.upper()}USDT"
    
    def get_mapping(self, symbol: str) -> SymbolMapping:
        """Get full symbol mapping."""
        gecko_id = self.get_gecko_id(symbol)
        binance_pair = self.get_binance_pair(symbol)
        
        return SymbolMapping(
            symbol=symbol.upper(),
            gecko_id=gecko_id or symbol.lower(),
            binance_pair=binance_pair
        )
    
    def is_binance_supported(self, symbol: str) -> bool:
        """Check if symbol is likely supported on Binance."""
        mapping = self._mappings.get(symbol.upper())
        return mapping is not None and mapping[1] is not None
    
    def add_mapping(self, symbol: str, gecko_id: str, binance_pair: Optional[str] = None):
        """Add or update a symbol mapping."""
        self._mappings[symbol.upper()] = (gecko_id, binance_pair)

