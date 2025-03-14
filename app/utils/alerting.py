"""
Alerting system for the Network Monitoring System
"""
import os
import uuid
import logging
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.influx import InfluxClient

# Configure logging
logger = logging.getLogger("utils.alerting")

# Global state to track active alerts
active_alerts = {}

def send_alert(alert_type, message, device_id, value, threshold, resource=None):
    """
    Send an alert and store in InfluxDB
    
    Args:
        alert_type: Type of alert (cpu, memory, disk, interface, etc.)
        message: Alert message
        device_id: ID of the device
        value: Current value that triggered the alert
        threshold: Threshold value that was exceeded
        resource: Optional resource name (e.g., interface name, disk partition)
    """
    # Generate alert ID
    alert_id = f"{alert_type}_{device_id}"
    if resource:
        alert_id += f"_{resource}"
    
    # Check if this alert is already active
    if alert_id in active_alerts:
        # Update existing alert if needed
        active_alerts[alert_id]['count'] += 1
        active_alerts[alert_id]['last_time'] = datetime.datetime.utcnow()
        active_alerts[alert_id]['value'] = value
        
        # Don't send repeated alerts too frequently
        time_diff = (active_alerts[alert_id]['last_time'] - active_alerts[alert_id]['first_time']).total_seconds()
        if time_diff < 300:  # 5 minutes
            logger.debug(f"Suppressing repeated alert {alert_id}: {message}")
            return
    else:
        # New alert
        active_alerts[alert_id] = {
            'id': alert_id,
            'type': alert_type,
            'device_id': device_id,
            'message': message,
            'value': value,
            'threshold': threshold,
            'resource': resource,
            'count': 1,
            'first_time': datetime.datetime.utcnow(),
            'last_time': datetime.datetime.utcnow()
        }
    
    # Log the alert
    logger.warning(f"ALERT: {message}")
    
    # Store in InfluxDB
    store_alert(alert_id, alert_type, device_id, message, value, threshold, resource)
    
    # Send email notification
    send_email_alert(alert_id, alert_type, device_id, message, value, threshold, resource)

def clear_alert(alert_id):
    """
    Clear an active alert
    
    Args:
        alert_id: ID of the alert to clear
    """
    if alert_id in active_alerts:
        # Update InfluxDB to mark alert as inactive
        store_alert_clear(alert_id)
        
        # Remove from active alerts
        del active_alerts[alert_id]
        logger.info(f"Cleared alert {alert_id}")

def store_alert(alert_id, alert_type, device_id, message, value, threshold, resource=None):
    """
    Store alert in InfluxDB
    
    Args:
        alert_id: ID of the alert
        alert_type: Type of alert
        device_id: ID of the device
        message: Alert message
        value: Current value that triggered the alert
        threshold: Threshold value that was exceeded
        resource: Optional resource name
    """
    try:
        # Get device name if possible
        device_name = device_id  # Default to ID if name not available
        
        # Create InfluxDB client
        influx = InfluxClient()
        
        # Prepare data point
        data = [
            {
                "measurement": "alerts",
                "tags": {
                    "alert_id": alert_id,
                    "type": alert_type,
                    "device_id": device_id,
                    "device_name": device_name,
                    "resource": resource if resource else "none"
                },
                "fields": {
                    "message": message,
                    "value": float(value),
                    "threshold": float(threshold),
                    "active": True
                }
            }
        ]
        
        # Write to InfluxDB
        influx.write_data(data)
        logger.debug(f"Stored alert in InfluxDB: {alert_id}")
        
    except Exception as e:
        logger.error(f"Error storing alert in InfluxDB: {str(e)}")

def store_alert_clear(alert_id):
    """
    Update InfluxDB to mark an alert as inactive
    
    Args:
        alert_id: ID of the alert to clear
    """
    try:
        # Create InfluxDB client
        influx = InfluxClient()
        
        # Get the alert from our active alerts
        if alert_id not in active_alerts:
            logger.warning(f"Cannot clear non-existent alert: {alert_id}")
            return
            
        alert = active_alerts[alert_id]
        
        # Prepare data point
        data = [
            {
                "measurement": "alerts",
                "tags": {
                    "alert_id": alert_id,
                    "type": alert['type'],
                    "device_id": alert['device_id'],
                    "device_name": alert['device_id'],  # Default to ID if name not available
                    "resource": alert['resource'] if alert['resource'] else "none"
                },
                "fields": {
                    "message": f"CLEARED: {alert['message']}",
                    "value": float(alert['value']),
                    "threshold": float(alert['threshold']),
                    "active": False
                }
            }
        ]
        
        # Write to InfluxDB
        influx.write_data(data)
        logger.debug(f"Marked alert as inactive in InfluxDB: {alert_id}")
        
    except Exception as e:
        logger.error(f"Error updating alert in InfluxDB: {str(e)}")

def send_email_alert(alert_id, alert_type, device_id, message, value, threshold, resource=None):
    """
    Send email notification for an alert
    
    Args:
        alert_id: ID of the alert
        alert_type: Type of alert
        device_id: ID of the device
        message: Alert message
        value: Current value that triggered the alert
        threshold: Threshold value that was exceeded
        resource: Optional resource name
    """
    # This is a placeholder function - in a real implementation,
    # you would configure SMTP settings and send actual emails
    
    # For demo purposes, just log that we would send an email
    logger.info(f"Would send email alert: {message}")
    
    # Example of how email sending would be implemented:
    '''
    try:
        # Email configuration
        smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "alerts@example.com")
        smtp_password = os.getenv("SMTP_PASSWORD", "password")
        
        # Recipient email from config
        recipient = os.getenv("ALERT_EMAIL", "admin@example.com")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient
        msg['Subject'] = f"[ALERT] {alert_type.upper()}: {device_id}"
        
        # Build message body
        body = f"""
        Alert: {message}
        
        Device: {device_id}
        Type: {alert_type}
        Value: {value}
        Threshold: {threshold}
        """
        
        if resource:
            body += f"Resource: {resource}\n"
            
        body += f"\nTime: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            
        logger.info(f"Sent email alert to {recipient}: {message}")
        
    except Exception as e:
        logger.error(f"Error sending email alert: {str(e)}")
    '''
