#!/usr/bin/env python3
"""
Test script to verify bot configuration and modules.
Run this to check if everything is set up correctly.
"""
import sys
import os
import asyncio

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import aiogram
        import aiosqlite
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def check_config():
    """Check if configuration is valid."""
    try:
        from config import BOT_TOKEN, DATABASE_PATH
        
        if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("⚠️  Warning: BOT_TOKEN is not configured")
            return False
        
        print("✅ Configuration is valid")
        return True
    except ImportError as e:
        print(f"❌ Configuration error: {e}")
        return False

def check_modules():
    """Check if all modules can be imported."""
    try:
        sys.path.append('.')
        
        from database.database import init_db, Database
        from middleware.auth import AuthMiddleware
        from utils.experience import ExperienceHandler
        from handlers import (
            common, moderation, tickets, profile, admin,
            top, roles, artpoints, badwords
        )
        
        print("✅ All modules can be imported")
        return True
    except ImportError as e:
        print(f"❌ Module import error: {e}")
        return False

async def test_database():
    """Test database initialization."""
    try:
        from database.database import init_db
        await init_db()
        print("✅ Database initialization successful")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Testing Telegram Moderation Bot...")
    print()
    
    tests = [
        ("Dependencies", check_dependencies),
        ("Configuration", check_config),
        ("Modules", check_modules),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"Testing {name}...")
        result = test_func()
        results.append(result)
        print()
    
    # Test database asynchronously
    print("Testing Database...")
    db_result = asyncio.run(test_database())
    results.append(db_result)
    print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Bot is ready to use.")
        print()
        print("Next steps:")
        print("1. Set your BOT_TOKEN in config.py")
        print("2. Configure MAIN_GROUP_ID and MODERATOR_GROUP_ID")
        print("3. Add admin/moderator user IDs")
        print("4. Run: python bot.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)