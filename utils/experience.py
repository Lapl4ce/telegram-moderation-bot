import math
from typing import Tuple

def calculate_level_from_exp(experience: int) -> int:
    """Calculate level from experience using the formula: exp = 3 * level² + 50 * level + 100"""
    if experience < 100:
        return 1
    
    # Solve quadratic equation: 3*level² + 50*level + (100 - exp) = 0
    # Using quadratic formula: level = (-b + sqrt(b² - 4ac)) / 2a
    a, b, c = 3, 50, 100 - experience
    discriminant = b * b - 4 * a * c
    
    if discriminant < 0:
        return 1
    
    level = (-b + math.sqrt(discriminant)) / (2 * a)
    return max(1, int(level))

def calculate_exp_for_level(level: int) -> int:
    """Calculate required experience for a specific level"""
    return 3 * level * level + 50 * level + 100

def get_level_progress(experience: int) -> Tuple[int, int, int]:
    """
    Get level progress information
    Returns: (current_level, current_level_exp, next_level_exp)
    """
    current_level = calculate_level_from_exp(experience)
    current_level_exp = calculate_exp_for_level(current_level)
    next_level_exp = calculate_exp_for_level(current_level + 1)
    
    return current_level, current_level_exp, next_level_exp

def format_experience_bar(experience: int, bar_length: int = 10) -> str:
    """Create a visual experience bar"""
    current_level, current_level_exp, next_level_exp = get_level_progress(experience)
    
    if current_level == 1:
        progress = (experience - 100) / (current_level_exp - 100) if current_level_exp > 100 else 0
    else:
        prev_level_exp = calculate_exp_for_level(current_level - 1)
        progress = (experience - prev_level_exp) / (current_level_exp - prev_level_exp)
    
    progress = max(0, min(1, progress))
    filled_length = int(bar_length * progress)
    
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    percentage = int(progress * 100)
    
    return f"{bar} {percentage}%"