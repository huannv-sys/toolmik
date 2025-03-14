"""
Authentication and authorization utilities
"""
import os
import logging
import hashlib
import base64

# Configure logging
logger = logging.getLogger("utils.auth")

# In a real application, this would be stored in a database
# For demo purposes, we'll use an in-memory dictionary
users = {
    'admin': {
        'password': 'f2d81a260dea8a100dd517984e53c56a7523d96942a834b9cdc249bd4e8c7aa9',  # hash of "admin"
        'salt': 'a1b2c3d4',
        'role': 'admin'
    },
    'operator': {
        'password': '4cc57a6e6fb1bc62d5768099d264d2082de2a2c4033badfe4f58ca5c11afbeab',  # hash of "operator"
        'salt': 'e5f6g7h8',
        'role': 'operator'
    },
    'viewer': {
        'password': '2a26169ed90912a54c398d9f246703c2e31c0f394aa4d39cc78e02c2be14a9ab',  # hash of "viewer"
        'salt': 'i9j0k1l2',
        'role': 'viewer'
    }
}

def authenticate_user(username, password):
    """
    Authenticate a user with username and password
    
    Args:
        username: Username to authenticate
        password: Password to verify
        
    Returns:
        True if authentication is successful, False otherwise
    """
    if username not in users:
        logger.warning(f"Authentication failed: user {username} not found")
        return False
    
    user = users[username]
    salt = user['salt']
    stored_hash = user['password']
    
    # Hash the provided password with salt
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    
    if password_hash == stored_hash:
        logger.info(f"User {username} authenticated successfully")
        return True
    else:
        logger.warning(f"Authentication failed for user {username}: invalid password")
        return False

def get_user_role(username):
    """
    Get the role of a user
    
    Args:
        username: Username to look up
        
    Returns:
        Role of the user or 'viewer' if not found
    """
    if username in users:
        return users[username]['role']
    else:
        return 'viewer'  # Default to lowest privilege

def has_permission(username, required_role):
    """
    Check if a user has a required role or higher
    
    Args:
        username: Username to check
        required_role: Required role
        
    Returns:
        True if the user has the required role or higher, False otherwise
    """
    user_role = get_user_role(username)
    
    # Define role hierarchy
    role_hierarchy = ['viewer', 'operator', 'admin']
    
    # Get indices in the hierarchy
    try:
        user_index = role_hierarchy.index(user_role)
        required_index = role_hierarchy.index(required_role)
    except ValueError:
        return False
    
    # Check if user's role is equal or higher in the hierarchy
    return user_index >= required_index

def create_user(username, password, role):
    """
    Create a new user
    
    Args:
        username: Username to create
        password: Password for the user
        role: Role to assign
        
    Returns:
        True if successful, False otherwise
    """
    if username in users:
        logger.warning(f"Cannot create user {username}: already exists")
        return False
    
    # Generate salt
    salt = base64.b64encode(os.urandom(6)).decode('utf-8')[:8]
    
    # Hash password with salt
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    
    # Store user
    users[username] = {
        'password': password_hash,
        'salt': salt,
        'role': role
    }
    
    logger.info(f"Created user {username} with role {role}")
    return True

def update_user_password(username, new_password):
    """
    Update a user's password
    
    Args:
        username: Username to update
        new_password: New password
        
    Returns:
        True if successful, False otherwise
    """
    if username not in users:
        logger.warning(f"Cannot update password for {username}: user not found")
        return False
    
    user = users[username]
    salt = user['salt']
    
    # Hash new password with existing salt
    password_hash = hashlib.sha256((new_password + salt).encode()).hexdigest()
    
    # Update stored hash
    users[username]['password'] = password_hash
    
    logger.info(f"Updated password for user {username}")
    return True

def update_user_role(username, new_role):
    """
    Update a user's role
    
    Args:
        username: Username to update
        new_role: New role
        
    Returns:
        True if successful, False otherwise
    """
    if username not in users:
        logger.warning(f"Cannot update role for {username}: user not found")
        return False
    
    # Update role
    users[username]['role'] = new_role
    
    logger.info(f"Updated role for user {username} to {new_role}")
    return True

def delete_user(username):
    """
    Delete a user
    
    Args:
        username: Username to delete
        
    Returns:
        True if successful, False otherwise
    """
    if username not in users:
        logger.warning(f"Cannot delete user {username}: user not found")
        return False
    
    # Delete user
    del users[username]
    
    logger.info(f"Deleted user {username}")
    return True
