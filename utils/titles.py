"""Title system utilities."""

from config import TITLES


def get_title_by_level(level: int) -> str:
    """Get title based on user level."""
    # Find the highest title that the user qualifies for
    title = "Землянин"  # Default title
    
    for required_level, level_title in TITLES.items():
        if level >= required_level:
            title = level_title
        else:
            break
    
    return title


def get_next_title_info(level: int) -> tuple[str, int]:
    """Get information about the next title and required level."""
    current_title = get_title_by_level(level)
    
    # Find next title
    for required_level, title in TITLES.items():
        if required_level > level:
            levels_needed = required_level - level
            return title, levels_needed
    
    # If already at max title
    return current_title, 0


def get_all_titles() -> dict[int, str]:
    """Get all available titles."""
    return TITLES.copy()


def format_title_progress(level: int) -> str:
    """Format title progress string for display."""
    current_title = get_title_by_level(level)
    next_title, levels_needed = get_next_title_info(level)
    
    if levels_needed == 0:
        return f"🏆 {current_title} (максимальный титул)"
    else:
        return f"🏆 {current_title} → {next_title} (через {levels_needed} ур.)"