#!/usr/bin/env python3
"""
Utility functions for System SN generation and forecast data handling.
"""

from collections import defaultdict
from datetime import datetime

# Year code mapping based on the provided table
YEAR_CODES = {
    2025: "JT", 2026: "JW", 2027: "JX", 2028: "JY", 2029: "JZ",
    2030: "KB", 2031: "KH", 2032: "KJ", 2033: "KK", 2034: "KS",
    2035: "KT", 2036: "KW", 2037: "KX", 2038: "KY", 2039: "KZ",
    2040: "SB", 2041: "SH", 2042: "SJ", 2043: "SK", 2044: "SS",
    2045: "ST", 2046: "SW", 2047: "SX", 2048: "SY", 2049: "SZ",
    2050: "TB", 2051: "TH", 2052: "TJ", 2053: "TK", 2054: "TS",
    2055: "TT", 2056: "TW", 2057: "TX", 2058: "TY", 2059: "TZ",
    2060: "WB", 2061: "WH", 2062: "WJ", 2063: "WK", 2064: "WS",
    2065: "WT", 2066: "WW", 2067: "WX", 2068: "WY", 2069: "WZ",
    2070: "XB", 2071: "XH", 2072: "XJ", 2073: "XK", 2074: "XS",
    2075: "XT", 2076: "XW", 2077: "XX", 2078: "XY", 2079: "XZ",
    2080: "YB", 2081: "YH"
}

def get_year_code(year):
    """Get the year code for a given year."""
    return YEAR_CODES.get(year, "JT")  # Default to JT if year not found

def generate_system_sn_for_new_entry(installation_date, db):
    """
    Generate System SN for a new forecast entry, ensuring uniqueness.
    Format: [YearCode][MM][####] where #### is sequential within the month
    
    Args:
        installation_date: datetime object for the installation date
        db: SQLAlchemy database session
    
    Returns:
        str: Generated unique System SN
    """
    from app.models import Forecast
    
    # Get year code and month
    year = installation_date.year
    year_code = get_year_code(year)
    month = f"{installation_date.month:02d}"
    
    # Create month prefix for this year/month combination
    month_prefix = f"{year_code}{month}"
    
    # Find existing System SNs with the same year/month prefix
    existing_sns = db.query(Forecast.system_sn).filter(
        Forecast.system_sn.like(f"{month_prefix}%")
    ).all()
    
    # Extract sequence numbers from existing SNs for this month
    sequence_numbers = []
    for (sn,) in existing_sns:
        if len(sn) == 8 and sn.startswith(month_prefix):  # YearCode + MM + #### = 8 chars
            try:
                seq_num = int(sn[-4:])  # Last 4 digits
                sequence_numbers.append(seq_num)
            except ValueError:
                continue
    
    # Find next available sequence number within the month
    if sequence_numbers:
        next_sequence = max(sequence_numbers) + 1
    else:
        next_sequence = 1
    
    # Format sequence with zero padding (4 digits)
    sequence = f"{next_sequence:04d}"
    
    # Generate System SN: YearCode + MM + ####
    system_sn = f"{month_prefix}{sequence}"
    
    return system_sn

def validate_system_sn_format(system_sn):
    """
    Validate that a System SN follows the correct format: [YearCode][MM][####]
    
    Args:
        system_sn: String to validate
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not isinstance(system_sn, str):
        return False, "System SN must be a string"
    
    if len(system_sn) != 8:
        return False, "System SN must be exactly 8 characters ([YearCode][MM][####])"
    
    # Check if first 2 characters are a valid year code
    year_code = system_sn[:2]
    valid_year_codes = set(YEAR_CODES.values())
    if year_code not in valid_year_codes:
        return False, f"Invalid year code '{year_code}'. Must be one of: {sorted(valid_year_codes)}"
    
    try:
        # Extract and validate month
        month = int(system_sn[2:4])
        if month < 1 or month > 12:
            return False, "Month must be between 01 and 12"
        
        # Extract and validate sequence
        sequence = int(system_sn[4:8])
        if sequence < 1 or sequence > 9999:
            return False, "Sequence must be between 0001 and 9999"
            
    except ValueError:
        return False, "Invalid characters in System SN. Format: [YearCode][MM][####]"
    
    return True, ""

def extract_date_from_system_sn(system_sn, default_day=1):
    """
    Extract installation date from System SN.
    
    Args:
        system_sn: System SN in format [YearCode][MM][####]
        default_day: Day to use since day is not encoded (defaults to 1st of month)
    
    Returns:
        datetime or None: Extracted date or None if invalid
    """
    is_valid, error = validate_system_sn_format(system_sn)
    if not is_valid:
        return None
    
    try:
        # Find year from year code
        year_code = system_sn[:2]
        year = None
        for y, code in YEAR_CODES.items():
            if code == year_code:
                year = y
                break
        
        if year is None:
            return None
            
        month = int(system_sn[2:4])
        
        return datetime(year, month, default_day)
        
    except ValueError:
        return None

if __name__ == "__main__":
    # Test the functions
    test_date_2025 = datetime(2025, 8, 6)
    test_date_2026 = datetime(2026, 8, 19)
    print(f"Test date 2025: {test_date_2025} -> Year code: {get_year_code(2025)}")
    print(f"Test date 2026: {test_date_2026} -> Year code: {get_year_code(2026)}")
    
    # Test System SN validation
    test_sns = [
        "JT080001",  # Valid for 2025 August, 1st install
        "JW080002",  # Valid for 2026 August, 2nd install  
        "JT130001",  # Invalid month
        "JT080000",  # Invalid sequence (0)
        "XX080001",  # Invalid year code
        "JT08001",   # Too short
        "JT0800001", # Too long
    ]
    
    print("\nTesting System SN validation:")
    for sn in test_sns:
        is_valid, error = validate_system_sn_format(sn)
        print(f"SN: {sn} - Valid: {is_valid}, Error: {error}")
    
    # Test date extraction
    print(f"\nDate from JT080001: {extract_date_from_system_sn('JT080001')}")
    print(f"Date from JW080002: {extract_date_from_system_sn('JW080002')}")
