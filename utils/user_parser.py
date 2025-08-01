def parse_username(username: str) -> str:
    """Parse a username in the format @username."""
    if username.startswith('@'):
        return username[1:]  # Remove the '@' character
    return username

def parse_user_id(user_id: int) -> int:
    """Return the user ID directly."""
    return user_id

def parse_reply_message(reply_message) -> str:
    """Parse user from a reply to a message."""
    return reply_message.from_user.username if reply_message.from_user else None

def parse_forwarded_message(forwarded_message) -> str:
    """Parse user from a forwarded message."""
    return forwarded_message.from_user.username if forwarded_message.from_user else None
