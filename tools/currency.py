import os
import requests
from typing import Optional

def convert_currency(amount: float, from_curr: str = "USD", to_curr: str = "INR") -> str:
    """
    Convert a specific amount from one currency to another (e.g. from USD to INR, or EUR to INR).
    Useful for currency planning and budget estimation.
    """
    from_curr = from_curr.upper().strip()
    to_curr = to_curr.upper().strip()
    
    api_key = os.environ.get("EXCHANGE_API_KEY")
    if api_key:
        try:
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_curr}/{to_curr}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                rate = data["conversion_rate"]
                converted = amount * rate
                return f"{amount} {from_curr} is equivalent to {converted:.2f} {to_curr} (Rate: {rate:.4f})"
        except Exception:
            pass
            
    # Mock fallback rates if key is missing or request fails
    rates = {
        ("USD", "INR"): 83.50,
        ("INR", "USD"): 0.012,
        ("EUR", "INR"): 90.20,
        ("INR", "EUR"): 0.011,
        ("GBP", "INR"): 105.80,
        ("INR", "GBP"): 0.0095,
        ("USD", "EUR"): 0.92,
        ("EUR", "USD"): 1.08,
    }
    
    pair = (from_curr, to_curr)
    if pair in rates:
        rate = rates[pair]
        converted = amount * rate
        return f"{amount} {from_curr} is equivalent to {converted:.2f} {to_curr} (Mock Rate: {rate:.2f})"
        
    # Cross conversion using USD as base
    # Simple lookup
    base_to_usd = {"INR": 0.012, "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0064}
    usd_to_target = {"INR": 83.50, "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 156.00}
    
    if from_curr in base_to_usd and to_curr in usd_to_target:
        usd_value = amount * base_to_usd[from_curr]
        converted = usd_value * usd_to_target[to_curr]
        rate = converted / amount if amount > 0 else 1.0
        return f"{amount} {from_curr} is equivalent to {converted:.2f} {to_curr} (Mock Rate: {rate:.4f})"
        
    # Default fall back conversion
    return f"{amount} {from_curr} is converted to {amount * 80:.2f} {to_curr} (Fallback base rate of 80.0)"
