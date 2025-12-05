"""
Safety and Compliance Filters
Following AI Specification safety rules exactly.
"""
from typing import List, Tuple


class SafetyFilters:
    """Filters AI outputs to ensure compliance with safety rules."""
    
    FORBIDDEN_WORDS = [
        "buy", "sell", "hold", "should", "must", "recommend",
        "investment advice", "financial advice", "trading advice",
        "you should", "you must", "I recommend", "I suggest"
    ]
    
    FORBIDDEN_PATTERNS = [
        "should buy", "should sell", "should hold",
        "must buy", "must sell", "must hold",
        "recommend buying", "recommend selling",
        "advise buying", "advise selling"
    ]
    
    @staticmethod
    def check_compliance(text: str) -> Tuple[bool, List[str]]:
        """
        Check if text complies with safety rules.
        Returns: (is_compliant, violations)
        """
        violations = []
        text_lower = text.lower()
        
        # Check for forbidden words
        for word in SafetyFilters.FORBIDDEN_WORDS:
            if word in text_lower:
                violations.append(f"Contains forbidden word: '{word}'")
        
        # Check for forbidden patterns
        for pattern in SafetyFilters.FORBIDDEN_PATTERNS:
            if pattern in text_lower:
                violations.append(f"Contains forbidden pattern: '{pattern}'")
        
        is_compliant = len(violations) == 0
        return is_compliant, violations
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Sanitize text to remove any non-compliant content.
        Replaces forbidden phrases with neutral alternatives.
        """
        sanitized = text
        
        # Replace forbidden patterns
        replacements = {
            "should buy": "shows buying signals",
            "should sell": "shows selling signals",
            "should hold": "shows holding patterns",
            "must buy": "indicates buying pressure",
            "must sell": "indicates selling pressure",
            "I recommend": "analysis suggests",
            "I suggest": "data indicates",
            "you should": "the data suggests",
            "investment advice": "market analysis",
            "financial advice": "technical analysis",
            "trading advice": "market interpretation"
        }
        
        text_lower = sanitized.lower()
        for forbidden, replacement in replacements.items():
            if forbidden in text_lower:
                # Case-insensitive replacement
                import re
                sanitized = re.sub(
                    re.escape(forbidden),
                    replacement,
                    sanitized,
                    flags=re.IGNORECASE
                )
        
        return sanitized
    
    @staticmethod
    def validate_insight(insight_text: str) -> Tuple[bool, str]:
        """
        Validate insight text for compliance.
        Returns: (is_valid, error_message)
        """
        is_compliant, violations = SafetyFilters.check_compliance(insight_text)
        
        if not is_compliant:
            error_msg = f"Insight violates safety rules: {', '.join(violations)}"
            return False, error_msg
        
        # Additional validation: ensure neutral language
        if any(word in insight_text.lower() for word in ["guarantee", "certain", "definitely"]):
            return False, "Insight contains absolute statements (not allowed)"
        
        return True, ""

