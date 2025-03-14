#!/usr/bin/env python3
"""
API server for the MikroTik Network Monitoring System
Provides endpoints for data access and configuration
"""
import os
import jwt
import json
import yaml
import logging
import datetime
from functools import wraps
from utils.influx import InfluxClient
from utils.auth import authenticate_user, get_user_role
from flask import Flask, request, jsonify, g

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api")

app = Flask(__name__)

# Global configuration and InfluxDB client
config = None
influx_client = None

def create_influx_client(config):
    """Create a connection to InfluxDB"""
    from utils.influx import InfluxClient
    influx_config = config.get('influxdb', {})
    return InfluxClient(
        host=influx_config.get('host', 'influxdb'),
        port=influx_config.get('port', 8086),
        token=influx_config.get('token', 'ChangeThisPassword'),
        org=influx_config.get('org', 'my-org'),
        bucket=influx_config.get('bucket', 'my-bucket')
    )

def token_required(f):
    """Decorator to require a valid JWT token for API access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Extract token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Missing authentication token'}), 401
        
        try:
            # Verify token
            jwt_secret = config['api']['auth']['jwt_secret']
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            g.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated

def role_required(required_roles):
    """Decorator to require specific roles for API access"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in g:
                return jsonify({'message': 'Authentication required'}), 401
                
            user_role = g.user.get('role', 'viewer')
            if user_role not in required_roles:
                return jsonify({'message': 'Insufficient permissions'}), 403
                
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user and issue JWT token"""
    if not request.is_json:
        return jsonify({"message": "Missing JSON request"}), 400
        
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"message": "Missing username or password"}), 400
    
    # Authenticate user (implement your authentication logic)
    authenticated = authenticate_user(username, password)
    if not authenticated:
        return jsonify({"message": "Invalid credentials"}), 401
    
    # Get user role
    role = get_user_role(username)
    
    # Generate JWT token
    token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    token_payload = {
        'username': username,
        'role': role,
        'exp': token_expiry
    }
    
    jwt_secret = config['api']['auth']['jwt_secret']
    token = jwt.encode(token_payload, jwt_secret, algorithm='HS256')
    
    return jsonify({
        'token': token,
        'expires': token_expiry.isoformat(),
        'role': role
    })

@app.route('/api/status', methods=['GET'])
@token_required
def get_status():
    """Get the status of all monitored devices"""
    try:
        # Query InfluxDB for device status
        devices = influx_client.get_device_status()
        return jsonify(devices)
    except Exception as e:
        logger.error(f"Error fetching device status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices', methods=['GET'])
@token_required
def get_devices():
    """Get the list of monitored devices"""
    try:
        # Query InfluxDB for device list
        devices = influx_client.get_devices()
        return jsonify(devices)
    except Exception as e:
        logger.error(f"Error fetching device list: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/<device_id>/metrics', methods=['GET'])
@token_required
def get_device_metrics(device_id):
    """Get metrics for a specific device"""
    try:
        # Parse query parameters
        metric_type = request.args.get('type', 'all')
        start_time = request.args.get('start', '-1h')
        end_time = request.args.get('end', 'now()')
        
        # Query InfluxDB for device metrics
        metrics = influx_client.get_device_metrics(device_id, metric_type, start_time, end_time)
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error fetching metrics for device {device_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/<device_id>/interfaces', methods=['GET'])
@token_required
def get_device_interfaces(device_id):
    """Get interface information for a specific device"""
    try:
        # Query InfluxDB for device interfaces
        interfaces = influx_client.get_device_interfaces(device_id)
        return jsonify(interfaces)
    except Exception as e:
        logger.error(f"Error fetching interfaces for device {device_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/<device_id>/wireless', methods=['GET'])
@token_required
def get_wireless_metrics(device_id):
    """Get wireless metrics for a specific device"""
    try:
        # Parse query parameters
        start_time = request.args.get('start', '-1h')
        end_time = request.args.get('end', 'now()')
        
        # Query InfluxDB for wireless metrics
        metrics = influx_client.get_wireless_metrics(device_id, start_time, end_time)
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error fetching wireless metrics for device {device_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/<device_id>/qos', methods=['GET'])
@token_required
def get_qos_metrics(device_id):
    """Get QoS metrics for a specific device"""
    try:
        # Parse query parameters
        start_time = request.args.get('start', '-1h')
        end_time = request.args.get('end', 'now()')
        
        # Query InfluxDB for QoS metrics
        metrics = influx_client.get_qos_metrics(device_id, start_time, end_time)
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error fetching QoS metrics for device {device_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
@token_required
def get_alerts():
    """Get active alerts"""
    try:
        # Query InfluxDB for active alerts
        alerts = influx_client.get_alerts()
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['GET'])
@token_required
@role_required(['admin'])
def get_config():
    """Get current system configuration (admin only)"""
    # Filter out sensitive information
    safe_config = {
        'modules': config.get('modules', []),
        'alerting': {
            'email': config.get('alerting', {}).get('email'),
            'threshold': config.get('alerting', {}).get('threshold', {})
        },
        'rbac': {
            'roles': config.get('rbac', {}).get('roles', [])
        }
    }
    return jsonify(safe_config)

@app.route('/api/config', methods=['POST'])
@token_required
@role_required(['admin'])
def update_config():
    """Update system configuration (admin only)"""
    if not request.is_json:
        return jsonify({"message": "Missing JSON request"}), 400
        
    new_config = request.get_json()
    
    # Validate configuration (add validation logic here)
    
    try:
        # Merge new configuration with existing one
        # (careful not to overwrite sensitive fields)
        if 'modules' in new_config:
            config['modules'] = new_config['modules']
        
        if 'alerting' in new_config:
            if 'threshold' in new_config['alerting']:
                config['alerting']['threshold'] = new_config['alerting']['threshold']
            if 'email' in new_config['alerting']:
                config['alerting']['email'] = new_config['alerting']['email']
        
        # Save updated configuration
        with open("/app/config.yaml", "w") as f:
            yaml.dump(config, f)
        
        return jsonify({"message": "Configuration updated successfully"})
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        return jsonify({"error": str(e)}), 500

def start_api_server(app_config):
    """Start the API server"""
    global config, influx_client
    
    config = app_config
    influx_client = create_influx_client(config)
    
    api_config = config.get('api', {})
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 8000)
    
    logger.info(f"Starting API server on {host}:{port}")
    app.run(host=host, port=port)

if __name__ == "__main__":
    # For testing purposes only
    with open("/app/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    start_api_server(config)
