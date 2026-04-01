# GUI utility functions for KYC system

def format_timestamp(timestamp):
    """Format timestamp for display."""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def validate_image(image_path):
    """Validate if image path is valid."""
    import os
    return os.path.exists(image_path) and os.path.isfile(image_path)
