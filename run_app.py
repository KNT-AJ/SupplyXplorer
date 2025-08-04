import subprocess
import sys
import time
import threading
import os
from pathlib import Path

def run_backend():
    """Run the FastAPI backend server"""
    print("Starting FastAPI backend server on http://localhost:8000")
    subprocess.run([sys.executable, "main.py"])

def run_frontend():
    """Run the Dash frontend server"""
    print("Starting Dash frontend server on http://localhost:8050")
    subprocess.run([sys.executable, "app/dashboard.py"])

def main():
    print("SupplyXplorer - Starting both backend and frontend servers...")
    print("Backend will be available at: http://localhost:8000")
    print("Frontend will be available at: http://localhost:8050")
    print("Press Ctrl+C to stop both servers")
    print("-" * 60)
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Wait a moment for backend to start
    time.sleep(3)
    
    # Start frontend in main thread
    run_frontend()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        sys.exit(0)