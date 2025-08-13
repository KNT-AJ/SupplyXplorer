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
    # Resolve project_dir dynamically and choose best available Python
    project_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(project_dir, 'partxplorer_env', 'bin', 'python'),
        os.path.join(project_dir, 'supplyxplorer_env', 'bin', 'python'),
        sys.executable,
    ]
    python_executable = next((p for p in candidates if os.path.exists(p)), sys.executable)

    backend_command = [python_executable, 'main.py']
    # Run dashboard as a module so "from app..." imports work when executed from project root
    frontend_command = [python_executable, '-m', 'app.dashboard']

    print("PartXplorer - Starting both backend and frontend servers...")
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