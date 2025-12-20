import os
import subprocess
import time
import requests
import sys

def run_command(command, cwd):
    print(f"Running command: {' '.join(command)}")
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error running command: {' '.join(command)}")
        print(f"Stdout: {stdout.decode('utf-8')}")
        print(f"Stderr: {stderr.decode('utf-8')}")
        sys.exit(1)
    return stdout.decode('utf-8')

def main():
    print("=== AUS-Lab Integration Test ===")
    
    # Start simulation in background
    print("\n1. Starting simulation in background...")
    sim_process = subprocess.Popen([sys.executable, "main.py", "--headless"], cwd="simulation", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)

    # Test API
    print("\n2. Testing API...")
    try:
        response = requests.get("http://localhost:8000/")
        response.raise_for_status()
        if "AUS-Lab" in response.text:
            print("   ✓ API is responding")
        else:
            print("   ✗ API not responding")
            sim_process.kill()
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"   ✗ API not responding: {e}")
        sim_process.kill()
        sys.exit(1)

    # Test drone commands
    print("\n3. Testing drone commands...")
    try:
        response = requests.post("http://localhost:8000/takeoff", json={"ids": ["all"], "altitude": 1.5})
        response.raise_for_status()
        if response.json().get("success"):
            print("   ✓ Takeoff command accepted")
        else:
            print("   ✗ Takeoff command failed")
            sim_process.kill()
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Takeoff command failed: {e}")
        sim_process.kill()
        sys.exit(1)

    # Cleanup
    print("\n4. Cleaning up...")
    sim_process.kill()
    time.sleep(2)

    print("\n===================================")
    print("✓ All tests passed!")
    print("===================================\n")

if __name__ == "__main__":
    main()
