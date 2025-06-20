#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add current directory to path to import from para_dashboard
sys.path.append(os.getcwd())

from para_dashboard import PARAOrganizer

def test_vault_detection():
    print("Testing vault detection...")
    
    # Create organizer instance
    organizer = PARAOrganizer()
    
    # Test vault detection
    try:
        vault_path = organizer._detect_vault()
        print(f"\n✅ Vault detected: {vault_path}")
        return True
    except Exception as e:
        print(f"\n❌ Error in vault detection: {e}")
        return False

if __name__ == "__main__":
    test_vault_detection() 