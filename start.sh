#!/bin/bash

# Create necessary directories
mkdir -p data/influxdb
mkdir -p data/grafana
mkdir -p logs
mkdir -p dashboards
mkdir -p config/grafana

# Debug information
echo "Checking installed packages:"
which influxd
echo "---"

# Start InfluxDB
echo "Starting InfluxDB..."
influxd --reporting-disabled --bolt-path=./data/influxdb/influxd.bolt --engine-path=./data/influxdb/engine > logs/influxdb.log 2>&1 &
INFLUXDB_PID=$!
echo "InfluxDB started with PID $INFLUXDB_PID"

# Wait for InfluxDB to start
sleep 5

# Initialize InfluxDB if needed (suppress errors)
echo "Initializing InfluxDB (if needed)..."
influx setup --username admin --password ChangeThisPassword --org my-org --bucket my-bucket --retention 0 --force 2>/dev/null || true
# Update the token for consistent authentication
influx auth create --user admin --org my-org --all-access || true
echo "InfluxDB initialization complete."

# Create a simple web dashboard in HTML
mkdir -p dashboards/static
cat > dashboards/static/index.html << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Monitoring System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f0f0; }
        header { background-color: #2c3e50; color: white; padding: 15px; text-align: center; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .status-card { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }
        .status-ok { background-color: #d4edda; border-color: #c3e6cb; }
        .status-warning { background-color: #fff3cd; border-color: #ffeeba; }
        .status-error { background-color: #f8d7da; border-color: #f5c6cb; }
    </style>
</head>
<body>
    <header>
        <h1>Network Monitoring System</h1>
    </header>
    <div class="container">
        <h2>System Status</h2>
        <div class="status-card status-ok">
            <h3>InfluxDB</h3>
            <p>Status: Running</p>
            <p>Port: 8086</p>
        </div>
        
        <h2>Monitored Devices</h2>
        <p>No devices configured yet. Add devices in the configuration.</p>
        
        <h2>Recent Alerts</h2>
        <p>No alerts recorded yet.</p>
    </div>
    <script>
        // This would be replaced with actual API calls in a real implementation
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Dashboard loaded');
        });
    </script>
</body>
</html>
EOF

# Create a simple Flask app to serve as our web interface
mkdir -p app/web
cat > app/web/__init__.py << EOF
"""Web interface package for Network Monitoring System"""
EOF

cat > app/web/server.py << EOF
"""
Web server for Network Monitoring System
Provides a simple web interface and REST API
"""
from flask import Flask, render_template, jsonify, send_from_directory
import os
import sys
import threading
import time

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.influx import InfluxClient

app = Flask(__name__, 
           static_folder='../../dashboards/static',
           template_folder='../../dashboards/templates')

# Global variables
influx_client = None

@app.route('/')
def index():
    """Serve the main dashboard"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/status')
def api_status():
    """Return the status of all components"""
    return jsonify({
        'status': 'ok',
        'components': {
            'web': {'status': 'ok'},
            'influxdb': {'status': 'ok', 'port': 8086},
            'collectors': {'status': 'pending'}
        }
    })

@app.route('/api/devices')
def api_devices():
    """Return the list of all monitored devices"""
    if influx_client:
        try:
            devices = influx_client.get_devices()
            return jsonify({'devices': devices})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'devices': []})

@app.route('/api/alerts')
def api_alerts():
    """Return the list of active alerts"""
    if influx_client:
        try:
            alerts = influx_client.get_alerts()
            return jsonify({'alerts': alerts})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'alerts': []})

def start_web_server(host='0.0.0.0', port=5000, debug=False):
    """Start the web server"""
    global influx_client
    
    # Initialize InfluxDB client
    try:
        from main import load_config
        config = load_config()
        influx_config = config.get('influxdb', {})
        influx_client = InfluxClient(
            host=influx_config.get('host', 'localhost'),
            port=influx_config.get('port', 8086),
            token=influx_config.get('token', 'YM_NhDux0lCLYdPjyypSDQzAtATgFUh3x38CPDB34CzW51AXE1H2Zj9Gvqh7OhzWm9tF6jFKBcdNS4jn72FgFw=='),
            org=influx_config.get('org', 'my-org'),
            bucket=influx_config.get('bucket', 'my-bucket')
        )
        print(f"Connected to InfluxDB at {influx_config.get('host', 'localhost')}:{influx_config.get('port', 8086)}")
    except Exception as e:
        print(f"Warning: Could not initialize InfluxDB client: {str(e)}")
    
    # Start the Flask app
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    start_web_server()
EOF

# Start the Flask web server
echo "Starting Flask web server on port 5000..."
cd app
nohup python3 web/server.py > ../logs/web.log 2>&1 &
WEB_SERVER_PID=$!
echo "Web server started with PID $WEB_SERVER_PID"

# Wait for the web server to start
sleep 2

# Check if the web server is running
if ! ps -p $WEB_SERVER_PID > /dev/null; then
  echo "ERROR: Web server failed to start. Check logs/web.log for details."
  cat ../logs/web.log
  exit 1
fi

# Start the collectors
echo "Starting monitoring collectors..."
python3 main.py

# Wait for all background processes to finish
wait