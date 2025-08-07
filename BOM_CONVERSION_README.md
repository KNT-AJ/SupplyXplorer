# BOM Conversion Process

## Overview
This document describes how the Excel BOM file (`bom20250806.xlsx`) was converted to the standard SupplyXplorer CSV format.

## Original Excel File Structure
The Excel file contained the following columns:
- `Supplier`: Supplier name (with grouped/merged cells)
- `Column 1`: Part names/descriptions
- `MEDIAN of Unit Price ($)`: Unit pricing information
- `MAX of Unit Mass (g)`: Mass data
- Various `SUM of X Pack` columns: Quantity information for different pack sizes

## Conversion Process

### 1. Data Extraction
- **Part Names**: Extracted from `Column 1`
- **Supplier**: Used `Supplier` column with forward-fill for grouped data
- **Manufacturer**: Set to same as supplier (can be updated manually if needed)
- **Quantities**: Extracted from `SUM of X Pack` columns, taking the first reasonable non-zero value
- **Pricing**: Used `MEDIAN of Unit Price ($)` as the cost per unit

### 2. Default Values Applied
- `beginning_inventory`: 0
- `ap_term`: "Net 30"
- `ap_month_lag_days`: 30
- `manufacturing_days_lead`: 30
- `shipping_days_lead`: 15

### 3. Calculated Fields
- `cost_per_product`: `cost_per_unit × units_needed`

## Result
The conversion process created a BOM with:
- **55 parts** (down from 70 rows due to filtering empty entries)
- **Realistic quantities** extracted from pack size data
- **Proper supplier groupings** (Amazon, Argco, EMI, etc.)
- **Accurate pricing** based on median unit prices

## Files Created
- `sample_data/bom_current.csv`: The converted BOM file
- `sample_data/bom_sample_with_suppliers_backup.csv`: Backup of original sample
- `sample_data/bom_sample_with_suppliers.csv`: Updated to use new BOM data

## Usage
The new BOM is now the default that loads when running:
```bash
python load_sample_data.py
```

## Customization
To update the BOM:
1. Edit the Excel file or CSV directly
2. Run the conversion script: `python convert_bom.py`
3. Reload the sample data: `python load_sample_data.py`

## Notes
- The conversion script (`convert_bom.py`) can be reused for future BOM updates
- Supplier and manufacturer fields can be differentiated if needed
- Lead times and AP terms can be customized per supplier/part
