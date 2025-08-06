import subprocess
import sys
import time
import threading
import os

def run_server(command, name, cwd):
    """Generic function to run a server command."""
    print(f"Starting {name} server...")
    try:
        # Ensure the python executable from the venv is used
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(f"[{name}] {line.strip()}")
        process.stdout.close()
        return_code = process.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, command)
    except Exception as e:
        print(f"An error occurred while running {name}: {e}")

def main():
    # Hardcode the project directory and python executable for reliability
    project_dir = '/Users/ajdavis/GitHub/SupplyXplorer'
    python_executable = '/Users/ajdavis/GitHub/SupplyXplorer/supplyxplorer_env/bin/python'  # Use virtual environment python
    
    backend_command = [python_executable, 'main.py']
    frontend_command = [python_executable, 'app/dashboard.py']

    print("SupplyXplorer - Starting both backend and frontend servers...")
    print(f"Using Python from: {python_executable}")
    print("Backend will be available at: http://localhost:8000")
    print("Frontend will be available at: http://localhost:8050")
    print("Press Ctrl+C to stop both servers.")
    print("-" * 60)

    # Run both servers in daemon threads
    backend_thread = threading.Thread(target=run_server, args=(backend_command, "Backend", project_dir), daemon=True)
    frontend_thread = threading.Thread(target=run_server, args=(frontend_command, "Frontend", project_dir), daemon=True)

    backend_thread.start()
    print("Waiting for backend to initialize...")
    time.sleep(5)  # Give backend a moment to start up before starting frontend

    frontend_thread.start()

    # Keep the main thread alive to monitor the server threads
    try:
        # We join the threads to keep the script running
        backend_thread.join()
        frontend_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        # Daemon threads will exit automatically when the main program exits
        sys.exit(0)

if __name__ == "__main__":
    main()