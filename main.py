import uvicorn
from app.database import engine, run_schema_upgrades
from app.models import Base
from app.api import app

# Create database tables
Base.metadata.create_all(bind=engine)
run_schema_upgrades()

if __name__ == "__main__":
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )