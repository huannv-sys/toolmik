#!/usr/bin/env python3
"""
Installation script for Network Monitoring System without Docker
"""
import os
import subprocess
import sys
import yaml
import secrets
import time

# Basic configuration
ADMIN_EMAIL = "admin@example.com"
JWT_SECRET = secrets.token_hex(24)

def print_header(message):
    """Print a formatted header message"""
    print("\n" + "=" * 80)
    print(f" {message}")
    print("=" * 80)

def check_dependencies():
    """Check if required dependencies are installed"""
    print_header("Checking Dependencies")
    
    required_packages = [
        "python3", "pip", "influxdb2", "grafana"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            subprocess.run(['which', package], check=True, capture_output=True)
            print(f"✓ {package} is installed")
        except subprocess.CalledProcessError:
            missing_packages.append(package)
            print(f"✗ {package} is not installed")
    
    if missing_packages:
        print(f"\nMissing dependencies: {', '.join(missing_packages)}")
        print("Please install them first.")
        return False
    
    return True

def setup_directories():
    """Create necessary directories"""
    print_header("Setting Up Directories")
    
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/influxdb", exist_ok=True)
    os.makedirs("data/grafana", exist_ok=True)
    os.makedirs("dashboards", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    os.makedirs("config/influxdb", exist_ok=True)
    os.makedirs("config/grafana", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("✓ Directories created")

def setup_configuration():
    """Set up configuration files"""
    print_header("Setting Up Configuration")
    
    # Create main config.yaml if it doesn't exist
    if not os.path.exists("config.yaml"):
        config = {
            "modules": ["mikrotik", "system", "wireless", "wan", "qos"],
            "influxdb": {
                "host": "localhost",
                "port": 8086,
                "org": "my-org",
                "bucket": "my-bucket",
                "token": "ChangeThisPassword"
            },
            "alerting": {
                "email": ADMIN_EMAIL,
                "threshold": {
                    "cpu": 80,
                    "memory": 85,
                    "disk": 90
                }
            },
            "api": {
                "port": 8000,
                "host": "0.0.0.0",
                "auth": {
                    "enabled": True,
                    "jwt_secret": JWT_SECRET
                }
            },
            "rbac": {
                "roles": ["admin", "operator", "viewer"]
            }
        }
        
        with open("config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print("✓ Created config.yaml")
    else:
        print("✓ config.yaml already exists")

def start_influxdb():
    """Start InfluxDB service"""
    print_header("Starting InfluxDB")
    
    try:
        # Check if influxdb is running
        result = subprocess.run(
            ["pgrep", "-f", "influxd"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print("✓ InfluxDB is already running")
        else:
            # Start influxd in the background
            print("Starting InfluxDB...")
            with open("logs/influxdb.log", "w") as log_file:
                subprocess.Popen(
                    ["influxd", 
                     "--reporting-disabled",
                     "--bolt-path=./data/influxdb/influxd.bolt",
                     "--engine-path=./data/influxdb/engine"],
                    stdout=log_file,
                    stderr=log_file
                )
            
            # Wait for InfluxDB to start
            time.sleep(5)
            print("✓ InfluxDB started")
            
            # Initialize InfluxDB (first-time setup)
            print("Initializing InfluxDB...")
            setup_cmd = [
                "influx", "setup",
                "--username", "admin",
                "--password", "ChangeThisPassword",
                "--org", "my-org",
                "--bucket", "my-bucket",
                "--retention", "0",
                "--force"
            ]
            
            try:
                subprocess.run(setup_cmd, check=True)
                print("✓ InfluxDB initialized")
            except subprocess.CalledProcessError as e:
                print(f"! Warning: InfluxDB initialization failed: {e}")
                print("  This might be normal if InfluxDB was already initialized")
        
        # Get the auth token
        print("Retrieving InfluxDB token...")
        token_cmd = [
            "influx", "auth", "list",
            "--user", "admin",
            "--hide-headers"
        ]
        
        try:
            token_result = subprocess.run(
                token_cmd, 
                capture_output=True,
                text=True
            )
            if token_result.returncode == 0 and token_result.stdout.strip():
                # Extract token from output
                token = token_result.stdout.strip().split()[0]
                print(f"✓ Retrieved InfluxDB token: {token[:5]}...")
                
                # Update config with token
                with open("config.yaml", "r") as f:
                    config = yaml.safe_load(f)
                
                config["influxdb"]["token"] = token
                
                with open("config.yaml", "w") as f:
                    yaml.dump(config, f, default_flow_style=False)
            else:
                print("! Could not retrieve InfluxDB token")
        except subprocess.CalledProcessError as e:
            print(f"! Error retrieving InfluxDB token: {e}")
            
    except Exception as e:
        print(f"! Error starting InfluxDB: {e}")
        return False
    
    return True

def start_grafana():
    """Start Grafana service"""
    print_header("Starting Grafana")
    
    try:
        # Check if Grafana is running
        result = subprocess.run(
            ["pgrep", "-f", "grafana-server"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print("✓ Grafana is already running")
        else:
            # Create grafana config
            os.makedirs("config/grafana", exist_ok=True)
            
            with open("config/grafana/grafana.ini", "w") as f:
                f.write("[server]\n")
                f.write("http_port = 5000\n")
                f.write("domain = localhost\n")
                f.write("\n[security]\n")
                f.write("admin_user = admin\n")
                f.write("admin_password = ChangeThisPassword\n")
                f.write("\n[database]\n")
                f.write("path = ./data/grafana/grafana.db\n")
            
            # Start grafana-server in the background
            print("Starting Grafana...")
            with open("logs/grafana.log", "w") as log_file:
                subprocess.Popen(
                    ["grafana-server", 
                     "--config=./config/grafana/grafana.ini",
                     "--homepath=/usr/share/grafana"],
                    stdout=log_file,
                    stderr=log_file
                )
            
            # Wait for Grafana to start
            time.sleep(5)
            print("✓ Grafana started")
    
    except Exception as e:
        print(f"! Error starting Grafana: {e}")
        return False
    
    return True

def create_workflow_config():
    """Create workflow configuration for Replit"""
    print_header("Creating Workflow Configuration")
    
    # Create a simple script to start all services
    with open("start.sh", "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write("# Start services\n")
        f.write("echo 'Starting Network Monitoring System...'\n\n")
        f.write("# Start InfluxDB\n")
        f.write("influxd --reporting-disabled --bolt-path=./data/influxdb/influxd.bolt --engine-path=./data/influxdb/engine > logs/influxdb.log 2>&1 &\n")
        f.write("INFLUXDB_PID=$!\n")
        f.write("echo \"InfluxDB started with PID $INFLUXDB_PID\"\n\n")
        f.write("# Wait for InfluxDB to start\n")
        f.write("sleep 5\n\n")
        f.write("# Start Grafana\n")
        f.write("grafana-server --config=./config/grafana/grafana.ini --homepath=/usr/share/grafana > logs/grafana.log 2>&1 &\n")
        f.write("GRAFANA_PID=$!\n")
        f.write("echo \"Grafana started with PID $GRAFANA_PID\"\n\n")
        f.write("# Wait for Grafana to start\n")
        f.write("sleep 5\n\n")
        f.write("# Start the Python application\n")
        f.write("cd app\n")
        f.write("python3 main.py\n\n")
    
    os.chmod("start.sh", 0o755)
    print("✓ Created start.sh script")

def main():
    """Main installation function"""
    print_header("Network Monitoring System Installer")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Setup configuration
    setup_configuration()
    
    # Start services
    if not start_influxdb():
        print("Error starting InfluxDB. Installation aborted.")
        sys.exit(1)
    
    if not start_grafana():
        print("Error starting Grafana. Installation aborted.")
        sys.exit(1)
    
    # Create workflow config
    create_workflow_config()
    
    print_header("Installation Complete")
    print("Your Network Monitoring System is now installed!")
    print("\nAccess the services at:")
    print("- Grafana: http://localhost:5000")
    print("- InfluxDB: http://localhost:8086")
    print("- API: http://localhost:8000 (when started)")
    print("\nDefault credentials:")
    print("- Username: admin")
    print("- Password: ChangeThisPassword")
    print("\nTo start the services, run:")
    print("  ./start.sh")

if __name__ == "__main__":
    main()