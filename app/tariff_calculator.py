"""
Tariff Calculator Module
Handles tariff calculations based on country of origin
"""

from typing import Dict, Optional, List, Tuple
import json
import os
from dataclasses import dataclass


@dataclass
class TariffInputs:
    hts_code: Optional[str]
    country_of_origin: Optional[str]
    importing_country: str
    invoice_value: float
    currency_code: str
    fx_rate: float
    freight_to_border: float
    insurance_cost: float
    assists_tooling: float
    royalties_fees: float
    other_dutiable: float
    incoterm: Optional[str]
    quantity: Optional[float]
    quantity_uom: Optional[str]
    net_weight_kg: Optional[float]
    volume_liters: Optional[float]
    unit_of_measure_hts: Optional[str]
    fta_eligible: bool
    fta_program: Optional[str]
    add_cvd_rate_pct: float
    special_duty_surcharge_pct: float
    entry_date: Optional[str]
    de_minimis: bool
    port_of_entry: Optional[str]
    transport_mode: Optional[str]

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

        # Try to load overrides from project-level configuration file
        self._load_overrides_from_file()

    def _config_file_path(self) -> str:
        # Project root is parent of the app directory
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        return os.path.join(project_root, 'tariff_rates.json')

    def _load_overrides_from_file(self) -> None:
        try:
            path = self._config_file_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    if 'default_rate' in data and isinstance(data['default_rate'], (int, float)):
                        self.default_rate = float(data['default_rate'])
                    if 'rates' in data and isinstance(data['rates'], dict):
                        # Normalize keys to our lowercase underscore format
                        normalized = {}
                        for k, v in data['rates'].items():
                            if isinstance(v, (int, float)):
                                key = str(k).lower().replace(' ', '_').replace('-', '_')
                                normalized[key] = float(v)
                        if normalized:
                            self.tariff_rates.update(normalized)
        except Exception:
            # Fail silently; use defaults
            pass
    
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
        """Calculate tariff amount based on declared value and country (legacy helper)."""
        tariff_rate = self.get_tariff_rate(country)
        return declared_value * (tariff_rate / 100.0)
    
    def get_effective_tariff_rate(self, country: Optional[str], hts_code: Optional[str], importing_country: Optional[str] = "USA", entry_date: Optional[str] = None) -> float:
        """Return the effective ad-valorem rate given origin and HTS.

        Rules implemented (August 2025):
        - HTS 7307.29.0090 of China into USA: 5% MFN + 25% Section 301 List 3 = 30%
        - Otherwise: use country-derived rate map.
        """
        # Normalize
        normalized_hts = (hts_code or "").replace(".", "").strip()
        normalized_origin = (country or "").lower().replace(" ", "_").replace("-", "_")
        normalized_import = (importing_country or "USA").upper()

        if normalized_import in ["USA", "US", "UNITED STATES"]:
            if normalized_origin in ["china", "prc", "people\'s_republic_of_china", "peoples_republic_of_china"]:
                # Match 7307.29.0090 allowing dot/no-dot formatting
                if normalized_hts in ["7307290090"]:
                    return 30.0  # 5% MFN + 25% 301 List 3

        # Fallback to country-based proxy
        return self.get_tariff_rate(country)

    def get_total_cost_with_tariffs(self, unit_cost: float, quantity: int,
                                    country: Optional[str], shipping_cost_per_unit: float = 0.0,
                                    hts_code: Optional[str] = None, importing_country: Optional[str] = "USA",
                                    entry_date: Optional[str] = None) -> Dict:
        """Calculate total cost including tariffs and shipping (HTS-aware)."""
        # Calculate base costs
        base_cost = unit_cost * quantity
        shipping_cost = shipping_cost_per_unit * quantity
        
        # Calculate tariff using HTS-aware rate if provided
        effective_rate = self.get_effective_tariff_rate(country, hts_code, importing_country, entry_date)
        tariff_amount = base_cost * (effective_rate / 100.0)
        
        # Calculate total
        total_cost = base_cost + shipping_cost + tariff_amount
        
        return {
            'base_cost': base_cost,
            'shipping_cost': shipping_cost,
            'tariff_amount': tariff_amount,
            'tariff_rate': effective_rate,
            'total_cost': total_cost,
            'country': country,
            'hts_code': hts_code,
            'importing_country': importing_country,
        } 

    # Enhanced valuation engine based on provided menu
    def compute_dutiable_value(self, inputs: TariffInputs) -> Tuple[float, float, float, List[str]]:
        """Compute dutiable value according to valuation rules (simplified for MVP).
        Returns (invoice_value_usd, dutiable_additions, dutiable_value, notes)
        """
        notes: List[str] = []

        # Convert invoice value to USD using fx_rate (assuming importing country is USA)
        invoice_value_usd = inputs.invoice_value * (inputs.fx_rate or 1.0)
        notes.append(f"Converted invoice value using FX {inputs.fx_rate or 1.0} from {inputs.currency_code} to USD.")

        # Determine which additions apply based on incoterm (simplified)
        additions = 0.0
        if inputs.incoterm:
            inc = inputs.incoterm.upper()
            # If FOB origin, freight/insurance to border are dutiable additions
            if inc.startswith('FOB'):
                additions += inputs.freight_to_border + inputs.insurance_cost
                notes.append("FOB: added freight to border and insurance to dutiable value.")
            # If CIF, assume freight and insurance already included in invoice; skip
            elif inc.startswith('CIF'):
                notes.append("CIF: freight and insurance assumed included in invoice value.")
            else:
                # Default: add if provided
                additions += inputs.freight_to_border + inputs.insurance_cost
                notes.append("Incoterm not FOB/CIF: added provided freight/insurance to dutiable value.")
        else:
            additions += inputs.freight_to_border + inputs.insurance_cost
            notes.append("No incoterm: added provided freight/insurance to dutiable value by default.")

        # Add statutory additions
        additions += inputs.assists_tooling + inputs.royalties_fees + inputs.other_dutiable
        if any(x > 0 for x in [inputs.assists_tooling, inputs.royalties_fees, inputs.other_dutiable]):
            notes.append("Added assists, royalties/license fees, and other dutiable additions.")

        dutiable_value = invoice_value_usd + additions
        return invoice_value_usd, additions, dutiable_value, notes

    def quote_duties(self, inputs: TariffInputs) -> Dict:
        """Compute duty/fees for a line using simplified US logic (ad-valorem, ADD/CVD, 301/232, MPF/HMF)."""
        # Valuation
        invoice_value_usd, dutiable_additions, dutiable_value, notes = self.compute_dutiable_value(inputs)

        # Base ad-valorem rate: derive from country map as a proxy; 0 for USA or FTA if eligible
        base_rate = self.get_tariff_rate(inputs.country_of_origin)
        if inputs.fta_eligible:
            notes.append("FTA eligible: base ad-valorem rate reduced to 0%.")
            base_rate = 0.0

        # Effective ad-valorem may include special surcharges (e.g., Section 301/232)
        effective_ad_valorem_rate = base_rate
        special_rate = max(0.0, float(inputs.special_duty_surcharge_pct or 0.0))
        add_cvd_rate = max(0.0, float(inputs.add_cvd_rate_pct or 0.0))

        # Duty computations
        ad_valorem_duty = dutiable_value * (effective_ad_valorem_rate / 100.0)
        special_amount = dutiable_value * (special_rate / 100.0)
        add_cvd_amount = dutiable_value * (add_cvd_rate / 100.0)

        # US fees (MPF/HMF) simplified
        mpf_amount = 0.0
        hmf_amount = 0.0
        if (inputs.importing_country or "USA").upper() in ["USA", "US", "UNITED STATES"]:
            # MPF: 0.3464% of value with min $31.67 and max $614.35 (FY25 indicative) for formal entries
            mpf_rate = 0.003464
            mpf_amount = dutiable_value * mpf_rate
            mpf_amount = min(max(mpf_amount, 31.67), 614.35)
            # HMF: 0.125% if by vessel (sea)
            if (inputs.transport_mode or "").lower() in ["sea", "ocean", "vessel"]:
                hmf_amount = dutiable_value * 0.00125
        
        total = ad_valorem_duty + special_amount + add_cvd_amount + mpf_amount + hmf_amount
        effective_total_rate_pct = (total / dutiable_value * 100.0) if dutiable_value > 0 else 0.0

        return {
            "inputs": {
                "hts_code": inputs.hts_code,
                "country_of_origin": inputs.country_of_origin,
                "importing_country": inputs.importing_country,
                "incoterm": inputs.incoterm,
                "fta_program": inputs.fta_program,
                "transport_mode": inputs.transport_mode,
            },
            "invoice_value_usd": invoice_value_usd,
            "dutiable_additions": dutiable_additions,
            "dutiable_value": dutiable_value,
            "base_ad_valorem_rate_pct": base_rate,
            "effective_ad_valorem_rate_pct": effective_ad_valorem_rate,
            "add_cvd_rate_pct": add_cvd_rate,
            "special_surcharge_rate_pct": special_rate,
            "ad_valorem_duty": ad_valorem_duty,
            "add_cvd_amount": add_cvd_amount,
            "special_surcharge_amount": special_amount,
            "mpf_amount": mpf_amount,
            "hmf_amount": hmf_amount,
            "total_duties_and_fees": total,
            "effective_total_rate_pct": effective_total_rate_pct,
            "notes": notes,
        }