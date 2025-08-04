"""
Tariff Calculator Module
Handles tariff calculations based on country of origin
"""

from typing import Dict, Optional

class TariffCalculator:
    """Calculate tariffs based on country of origin"""
    
    def __init__(self):
        # Tariff rates by country (percentage of declared value)
        # These are example rates - in production, these would come from a database or API
        self.tariff_rates = {
            'china': 25.0,  # Section 301 tariffs
            'japan': 0.0,   # Most favored nation
            'germany': 0.0, # Most favored nation
            'mexico': 0.0,  # USMCA
            'canada': 0.0,  # USMCA
            'south_korea': 0.0,  # KORUS
            'vietnam': 0.0,  # Most favored nation
            'taiwan': 0.0,   # Most favored nation
            'india': 0.0,    # Most favored nation
            'thailand': 0.0, # Most favored nation
            'malaysia': 0.0, # Most favored nation
            'singapore': 0.0, # Most favored nation
            'philippines': 0.0, # Most favored nation
            'indonesia': 0.0, # Most favored nation
            'usa': 0.0,      # Domestic
            'united_states': 0.0, # Domestic
        }
        
        # Default tariff rate for unknown countries
        self.default_rate = 3.0
    
    def get_tariff_rate(self, country: Optional[str]) -> float:
        """Get tariff rate for a given country"""
        if not country:
            return 0.0
        
        # Normalize country name
        country_normalized = country.lower().replace(' ', '_').replace('-', '_')
        
        # Check for exact match first
        if country_normalized in self.tariff_rates:
            return self.tariff_rates[country_normalized]
        
        # Check for partial matches
        for known_country, rate in self.tariff_rates.items():
            if known_country in country_normalized or country_normalized in known_country:
                return rate
        
        # Return default rate for unknown countries
        return self.default_rate
    
    def calculate_tariff(self, declared_value: float, country: Optional[str]) -> float:
        """Calculate tariff amount based on declared value and country"""
        tariff_rate = self.get_tariff_rate(country)
        return declared_value * (tariff_rate / 100.0)
    
    def get_total_cost_with_tariffs(self, unit_cost: float, quantity: int, 
                                  country: Optional[str], shipping_cost_per_unit: float = 0.0) -> Dict:
        """Calculate total cost including tariffs and shipping"""
        # Calculate base costs
        base_cost = unit_cost * quantity
        shipping_cost = shipping_cost_per_unit * quantity
        
        # Calculate tariff
        tariff_amount = self.calculate_tariff(base_cost, country)
        
        # Calculate total
        total_cost = base_cost + shipping_cost + tariff_amount
        
        return {
            'base_cost': base_cost,
            'shipping_cost': shipping_cost,
            'tariff_amount': tariff_amount,
            'tariff_rate': self.get_tariff_rate(country),
            'total_cost': total_cost,
            'country': country
        } 