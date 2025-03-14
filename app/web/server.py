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
