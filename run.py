import subprocess
import time
import webbrowser
import os
import signal
import sys
import socket
import requests
import threading
from requests.exceptions import RequestException

def is_port_open(port, host='localhost', timeout=1):
    """Check if a port is open on the given host."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def check_backend_health(url, max_retries=10, retry_delay=2):
    """Check if the backend API is healthy and responsive."""
    print(f"Checking backend health at {url}...")
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Backend is healthy after {attempt+1} attempts!")
                return True
        except RequestException:
            if attempt < max_retries - 1:
                print(f"Backend not ready, retrying in {retry_delay}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
    
    print("Failed to connect to backend after maximum retries.")
    return False

def read_process_output(process, prefix):
    """Read process output and print with prefix."""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(f"{prefix}: {output.strip()}")
    
    # Also check for errors
    for line in process.stderr.readlines():
        if line:
            print(f"{prefix} ERROR: {line.strip()}")

def start_backend():
    """Start the FastAPI backend server."""
    print("Starting FastAPI backend server...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000",
         "--timeout-keep-alive", "120", "--timeout-graceful-shutdown", "120", "--workers", "4"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )
    
    # Start reading output in a separate thread
    output_thread = threading.Thread(
        target=read_process_output, 
        args=(backend_process, "BACKEND"),
        daemon=True
    )
    output_thread.start()
    
    # Wait for backend to start
    for i in range(10):
        if is_port_open(8000):
            print(f"Backend service detected on port 8000 after {i+1} attempts")
            time.sleep(2)  # Give it a moment to fully initialize
            # Try to access the API docs to confirm it's fully up
            if check_backend_health("http://localhost:8000/docs"):
                return backend_process
            break
        print(f"Waiting for backend to start (attempt {i+1}/10)...")
        time.sleep(2)
    
    # Check if process is still running
    if backend_process.poll() is not None:
        # Process has terminated, get error message
        error_output = backend_process.stderr.read()
        print(f"Backend process terminated with error:\n{error_output}")
    
    # Return the process even if health check failed so we can terminate it properly later
    return backend_process

def start_admin_panel():
    """Start the admin panel Streamlit app."""
    print("Starting admin panel...")
    admin_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/admin/admin_panel.py", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Start reading output in a separate thread
    output_thread = threading.Thread(
        target=read_process_output, 
        args=(admin_process, "ADMIN"),
        daemon=True
    )
    output_thread.start()
    
    # Wait for the admin panel to start
    for i in range(5):
        if is_port_open(8501):
            print(f"Admin panel detected on port 8501")
            time.sleep(2)  # Give it a moment to fully initialize
            break
        print(f"Waiting for admin panel to start (attempt {i+1}/5)...")
        time.sleep(2)
    
    return admin_process

def start_frontend():
    """Start the frontend Streamlit app."""
    print("Starting frontend application...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/frontend/app.py", "--server.port", "8502"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Start reading output in a separate thread
    output_thread = threading.Thread(
        target=read_process_output, 
        args=(frontend_process, "FRONTEND"),
        daemon=True
    )
    output_thread.start()
    
    # Wait for the frontend to start
    for i in range(5):
        if is_port_open(8502):
            print(f"Frontend detected on port 8502")
            time.sleep(2)  # Give it a moment to fully initialize
            break
        print(f"Waiting for frontend to start (attempt {i+1}/5)...")
        time.sleep(2)
    
    return frontend_process

def open_apps_in_browser():
    """Open applications in the web browser."""
    # By default, don't automatically open any browsers
    # Just print instructions on how to access
    print("\nAccess CARA ComplianceBot at the following URLs:")
    print("Backend API:     http://localhost:8000")
    print("API Docs:        http://localhost:8000/docs")
    print("Admin Panel:     http://localhost:8501")
    print("Frontend App:    http://localhost:8502")
    
    # Ask user if they want to open any browser tabs
    user_input = input("\nDo you want to open any of these in your browser? (y/n): ").lower().strip()
    if user_input == 'y' or user_input == 'yes':
        which_app = input("Which app? (1=API Docs, 2=Admin Panel, 3=Frontend, all=All): ").lower().strip()
        
        if which_app == '1' or which_app == 'all':
            webbrowser.open("http://localhost:8000/docs")
            time.sleep(1)
        
        if which_app == '2' or which_app == 'all':
            webbrowser.open("http://localhost:8501")
            time.sleep(1)
        
        if which_app == '3' or which_app == 'all':
            webbrowser.open("http://localhost:8502")

def main():
    """Run the full application stack."""
    processes = []
    
    try:
        # Start backend
        backend_process = start_backend()
        processes.append(backend_process)
        
        # Only start other components if backend is running
        if is_port_open(8000):
            # Start admin panel
            admin_process = start_admin_panel()
            processes.append(admin_process)
            
            # Start frontend
            frontend_process = start_frontend()
            processes.append(frontend_process)
            
            # Open applications in browser with user consent
            open_apps_in_browser()
            
            print("\nCARA ComplianceBot is running!")
            print("\nPress Ctrl+C to stop all servers.")
        else:
            print("\nFailed to start backend server. Check logs for errors.")
            return
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down all servers...")
        for process in processes:
            process.terminate()
        
        # Wait for all processes to terminate
        for process in processes:
            process.wait()
        
        print("All servers stopped.")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        for process in processes:
            process.terminate()

if __name__ == "__main__":
    main() 