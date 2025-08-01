import re
from typing import Optional
from datetime import datetime, timedelta

def parse_time_string(time_str: str) -> Optional[timedelta]:
    """
    Parse time string into timedelta
    Supports formats like: 1d, 2h, 30m, 1d2h30m, etc.
    """
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    
    # Regular expression to match time components
    pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.match(pattern, time_str)
    
    if not match:
        return None
    
    days, hours, minutes, seconds = match.groups()
    
    total_seconds = 0
    if days:
        total_seconds += int(days) * 24 * 60 * 60
    if hours:
        total_seconds += int(hours) * 60 * 60
    if minutes:
        total_seconds += int(minutes) * 60
    if seconds:
        total_seconds += int(seconds)
    
    if total_seconds == 0:
        return None
    
    return timedelta(seconds=total_seconds)

def format_timedelta(td: timedelta) -> str:
    """Format timedelta into human-readable string"""
    if not td:
        return "Permanent"
    
    total_seconds = int(td.total_seconds())
    
    days = total_seconds // (24 * 60 * 60)
    hours = (total_seconds % (24 * 60 * 60)) // (60 * 60)
    minutes = (total_seconds % (60 * 60)) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not parts:  # Only show seconds if no larger units
        parts.append(f"{seconds}s")
    
    return " ".join(parts) if parts else "0s"

def time_until(target_time: datetime) -> str:
    """Get human-readable time until target datetime"""
    now = datetime.now()
    if target_time <= now:
        return "Expired"
    
    delta = target_time - now
    return format_timedelta(delta)