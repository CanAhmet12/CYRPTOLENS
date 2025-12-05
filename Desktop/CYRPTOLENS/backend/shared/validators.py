"""
Shared validation utilities for Pydantic models.
Provides reusable validators and custom validation functions.
"""
import re
from typing import Any
from pydantic import field_validator, ValidationError


# Common regex patterns
COIN_SYMBOL_PATTERN = re.compile(r'^[A-Z0-9]{1,10}$')
PHONE_NUMBER_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')  # E.164 format
HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')


def validate_password_strength(password: str) -> str:
    """
    Validate password strength.
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")
    
    return password


def validate_coin_symbol(symbol: str) -> str:
    """
    Validate cryptocurrency symbol format.
    Requirements:
    - 1-10 characters
    - Uppercase letters and numbers only
    - No special characters or spaces
    """
    if not COIN_SYMBOL_PATTERN.match(symbol):
        raise ValueError(
            "Coin symbol must be 1-10 uppercase letters and numbers only (e.g., BTC, ETH)"
        )
    return symbol.upper()


def validate_phone_number(phone: str) -> str:
    """
    Validate phone number format (E.164).
    Requirements:
    - Optional + prefix
    - Country code (1-3 digits)
    - National number (up to 14 digits total)
    """
    if not PHONE_NUMBER_PATTERN.match(phone):
        raise ValueError(
            "Phone number must be in E.164 format (e.g., +1234567890 or 1234567890)"
        )
    return phone


def validate_hex_color(color: str) -> str:
    """Validate hex color code format (#RRGGBB)."""
    if not HEX_COLOR_PATTERN.match(color):
        raise ValueError("Color must be a valid hex code (e.g., #FF5733)")
    return color.upper()


def validate_percentage(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Validate percentage value."""
    if not (min_val <= value <= max_val):
        raise ValueError(f"Percentage must be between {min_val} and {max_val}")
    return value


def validate_transaction_type(transaction_type: str) -> str:
    """Validate transaction type."""
    valid_types = ['buy', 'sell', 'transfer', 'staking', 'airdrop', 'swap']
    if transaction_type.lower() not in valid_types:
        raise ValueError(
            f"Transaction type must be one of: {', '.join(valid_types)}"
        )
    return transaction_type.lower()


def validate_period_type(period_type: str) -> str:
    """Validate period type for DCA plans."""
    valid_types = ['daily', 'weekly', 'monthly']
    if period_type.lower() not in valid_types:
        raise ValueError(
            f"Period type must be one of: {', '.join(valid_types)}"
        )
    return period_type.lower()


def validate_export_format(format: str) -> str:
    """Validate export format."""
    valid_formats = ['pdf', 'csv', 'excel']
    if format.lower() not in valid_formats:
        raise ValueError(
            f"Export format must be one of: {', '.join(valid_formats)}"
        )
    return format.lower()


def validate_alert_type(alert_type: str) -> str:
    """Validate alert type."""
    valid_types = ['price_above', 'price_below', 'change_24h', 'portfolio_value']
    if alert_type.lower() not in valid_types:
        raise ValueError(
            f"Alert type must be one of: {', '.join(valid_types)}"
        )
    return alert_type.lower()


def validate_cost_basis_method(method: str) -> str:
    """Validate cost basis method."""
    valid_methods = ['FIFO', 'LIFO', 'AVG']
    if method.upper() not in valid_methods:
        raise ValueError(
            f"Cost basis method must be one of: {', '.join(valid_methods)}"
        )
    return method.upper()

