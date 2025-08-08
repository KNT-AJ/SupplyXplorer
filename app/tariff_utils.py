#!/usr/bin/env python3
"""
Utility functions and defaults for tariff-related operations.

This module centralizes lightweight rules used throughout the app to infer
whether a supplier is subject to tariffs and which defaults should be applied
when data is missing.
"""

# Opinionated defaults used when data is absent
DEFAULT_IMPORTING_COUNTRY = "USA"
DEFAULT_COUNTRY_OF_ORIGIN_TARIFFED = "China"
# Stainless steel tube/pipe fittings catch‑all
DEFAULT_HTS_CODE = "7307.29.0090"

def is_supplier_subject_to_tariffs(supplier_name):
    """
    Determine if a supplier is subject to tariffs based on supplier name.
    
    Args:
        supplier_name (str): Name of the supplier
        
    Returns:
        str: "Yes" if subject to tariffs, "No" otherwise
    """
    if not supplier_name:
        return "No"
    
    # International suppliers typically subject to U.S. Section 301 tariffs
    # Extend this list as new suppliers are added.
    international_suppliers = [
        'Sansun',
        'Oak Stills',
        'P&E',
        'QILI',
        'SAI Filters',
    ]
    
    # Check if supplier name matches any international supplier
    supplier_name_clean = supplier_name.strip()
    for intl_supplier in international_suppliers:
        if intl_supplier.lower() == supplier_name_clean.lower():
            return "Yes"
    
    return "No"

def update_tariff_status_for_supplier_name(supplier_name):
    """
    Get the tariff status for a supplier name.
    This function can be used when updating records.
    
    Args:
        supplier_name (str): Name of the supplier
        
    Returns:
        str: "Yes" if subject to tariffs, "No" otherwise
    """
    return is_supplier_subject_to_tariffs(supplier_name)
