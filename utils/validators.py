import re
from typing import List, Optional

def validate_username(username: str) -> bool:
    """Validate Telegram username format"""
    if not username:
        return False
    
    # Remove @ if present
    username = username.lstrip('@')
    
    # Telegram username rules: 5-32 characters, alphanumeric and underscores only
    if len(username) < 5 or len(username) > 32:
        return False
    
    return re.match(r'^[a-zA-Z0-9_]+$', username) is not None

def validate_user_id(user_id_str: str) -> Optional[int]:
    """Validate and convert user ID string to integer"""
    try:
        user_id = int(user_id_str)
        # Telegram user IDs are positive integers
        if user_id > 0:
            return user_id
    except ValueError:
        pass
    return None

def extract_user_id(text: str) -> Optional[int]:
    """Extract user ID from text (reply, mention, or plain ID)"""
    # Try to extract from @username or user ID
    if text.startswith('@'):
        return None  # We'll need to resolve username to ID elsewhere
    
    # Try to parse as direct user ID
    return validate_user_id(text)

def sanitize_text(text: str) -> str:
    """Sanitize text for safe database storage"""
    if not text:
        return ""
    
    # Remove or escape potentially dangerous characters
    text = text.strip()
    text = re.sub(r'[<>\"\'\\]', '', text)
    return text[:1000]  # Limit length

def validate_role_name(role_name: str) -> bool:
    """Validate custom role name"""
    if not role_name:
        return False
    
    # Role name should be 3-50 characters, alphanumeric and spaces
    role_name = role_name.strip()
    if len(role_name) < 3 or len(role_name) > 50:
        return False
    
    return re.match(r'^[a-zA-Z0-9\s]+$', role_name) is not None

def contains_bad_words(text: str, bad_words: List[str]) -> List[str]:
    """Check if text contains any bad words"""
    if not text or not bad_words:
        return []
    
    text_lower = text.lower()
    found_words = []
    
    for word in bad_words:
        if word.lower() in text_lower:
            found_words.append(word)
    
    return found_words

def format_user_display_name(username: str = None, first_name: str = None, last_name: str = None, user_id: int = None) -> str:
    """Format user display name from available information"""
    if first_name and last_name:
        return f"{first_name} {last_name}"
    elif first_name:
        return first_name
    elif username:
        return f"@{username}"
    elif user_id:
        return f"User {user_id}"
    else:
        return "Unknown User"