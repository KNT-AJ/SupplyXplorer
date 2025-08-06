# Additional validation and utility endpoints for the API

validation_endpoints = """

# Data validation and summary endpoints
@app.get("/validate/data")
def validate_data_integrity(db: Session = Depends(get_db)):
    \"\"\"Validate data integrity and return issues\"\"\"
    issues = []
    
    # Check if we have forecast data
    forecast_count = db.query(Forecast).count()
    if forecast_count == 0:
        issues.append("No forecast data found")
    
    # Check if we have BOM data
    bom_count = db.query(BOM).count()
    if bom_count == 0:
        issues.append("No BOM data found")
    
    # Check for orphaned BOMs (BOMs without matching forecast SKUs)
    forecast_skus = set(sku[0] for sku in db.query(Forecast.sku_id).distinct().all())
    bom_products = set(product[0] for product in db.query(BOM.product_id).distinct().all())
    orphaned_boms = bom_products - forecast_skus
    if orphaned_boms:
        issues.append(f"BOM products without forecasts: {', '.join(list(orphaned_boms)[:5])}")
    
    # Check for missing parts in BOM
    bom_parts = set(part[0] for part in db.query(BOM.part_id).distinct().all())
    actual_parts = set(part[0] for part in db.query(Part.part_id).distinct().all())
    missing_parts = bom_parts - actual_parts
    if missing_parts:
        issues.append(f"BOM references missing parts: {', '.join(list(missing_parts)[:5])}")
    
    return {
        "valid": len(issues) == 0,
        "forecast_count": forecast_count,
        "bom_count": bom_count,
        "issues": issues
    }

@app.get("/data/summary")
def get_data_summary(db: Session = Depends(get_db)):
    \"\"\"Get summary of all data in the system\"\"\"
    summary = {
        "products": db.query(Product).count(),
        "parts": db.query(Part).count(),
        "suppliers": db.query(Supplier).count(),
        "bom_items": db.query(BOM).count(),
        "forecasts": db.query(Forecast).count(),
        "lead_times": db.query(LeadTime).count()
    }
    
    # Add forecast date range if we have forecasts
    if summary["forecasts"] > 0:
        earliest = db.query(Forecast.period_start).order_by(Forecast.period_start.asc()).first()
        latest = db.query(Forecast.period_start).order_by(Forecast.period_start.desc()).first()
        summary["forecast_date_range"] = {
            "earliest": earliest[0].strftime('%Y-%m-%d') if earliest else None,
            "latest": latest[0].strftime('%Y-%m-%d') if latest else None
        }
    else:
        summary["forecast_date_range"] = None
    
    return summary

@app.delete("/data/clear")
def clear_all_data(db: Session = Depends(get_db)):
    \"\"\"Clear all data from the system (use with caution)\"\"\"
    try:
        # Clear in order to avoid foreign key issues
        db.query(LeadTime).delete()
        db.query(BOM).delete()
        db.query(Forecast).delete()
        db.query(Part).delete()
        db.query(Supplier).delete()
        db.query(Product).delete()
        
        db.commit()
        return {"message": "All data cleared successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")

\"\"\"
