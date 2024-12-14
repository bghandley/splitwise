from datetime import datetime
from flask import request, current_app
from pythonjsonlogger import jsonlogger
import logging
import os
from functools import wraps
from flask_login import current_user

class ActivityLogger:
    def __init__(self, app):
        self.app = app
        self.setup_logger()

    def setup_logger(self):
        """Setup JSON logger for activity tracking"""
        log_handler = logging.FileHandler('activity.log')
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(user)s %(ip)s %(action)s %(resource)s %(details)s'
        )
        log_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger('activity')
        self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)

    def log_activity(self, action, resource, details=None):
        """Log an activity"""
        try:
            self.logger.info('', extra={
                'timestamp': datetime.utcnow().isoformat(),
                'user': current_user.username if current_user.is_authenticated else 'anonymous',
                'ip': request.remote_addr,
                'action': action,
                'resource': resource,
                'details': details or {}
            })
        except Exception as e:
            current_app.logger.error(f"Failed to log activity: {str(e)}")

    def track_activity(self, action):
        """Decorator to track function calls"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                resource = request.path
                
                try:
                    result = f(*args, **kwargs)
                    
                    # Log successful activity
                    self.log_activity(
                        action=action,
                        resource=resource,
                        details={'status': 'success', 'args': kwargs}
                    )
                    
                    return result
                except Exception as e:
                    # Log failed activity
                    self.log_activity(
                        action=action,
                        resource=resource,
                        details={'status': 'error', 'error': str(e)}
                    )
                    raise
            return decorated_function
        return decorator

    def get_user_activity(self, username=None, start_date=None, end_date=None, limit=50):
        """Get user activity logs"""
        try:
            logs = []
            with open('activity.log', 'r') as f:
                for line in f:
                    try:
                        log = json.loads(line)
                        
                        # Apply filters
                        if username and log['user'] != username:
                            continue
                            
                        log_date = datetime.fromisoformat(log['timestamp'])
                        if start_date and log_date < start_date:
                            continue
                        if end_date and log_date > end_date:
                            continue
                            
                        logs.append(log)
                        
                        if len(logs) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
                        
            return logs
        except Exception as e:
            current_app.logger.error(f"Failed to get activity logs: {str(e)}")
            return []

    def get_resource_activity(self, resource_type, resource_id, limit=50):
        """Get activity logs for a specific resource"""
        try:
            logs = []
            with open('activity.log', 'r') as f:
                for line in f:
                    try:
                        log = json.loads(line)
                        
                        # Check if log is for the specified resource
                        if (f'/{resource_type}/{resource_id}' in log['resource'] or
                            (log['details'] and 
                             log['details'].get('resource_type') == resource_type and
                             log['details'].get('resource_id') == resource_id)):
                            logs.append(log)
                            
                            if len(logs) >= limit:
                                break
                    except json.JSONDecodeError:
                        continue
                        
            return logs
        except Exception as e:
            current_app.logger.error(f"Failed to get resource activity: {str(e)}")
            return []

# Initialize activity logger
activity_logger = ActivityLogger(current_app)

# Example usage:
"""
@activity_logger.track_activity('create_post')
def create_post():
    # Create post logic here
    pass

@activity_logger.track_activity('edit_post')
def edit_post(post_id):
    # Edit post logic here
    pass

# Manual logging
activity_logger.log_activity(
    action='view_post',
    resource=f'/posts/{post_id}',
    details={'post_id': post_id}
)
"""
