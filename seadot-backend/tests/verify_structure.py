"""
Seadot Backend Package Structure Verification Script
Mengecek apakah semua imports dan dependencies siap untuk dijalankan.
"""

import sys
import os
from pathlib import Path


def verify_package_structure():
    """Verifikasi struktur package Seadot Backend"""
    
    backend_folder = Path(__file__).parent
    print("="*60)
    print("  Seadot Backend - Package Structure Verification")
    print("="*60)
    
    # Add parent to sys.path
    sys.path.insert(0, str(backend_folder.parent))
    
    checks_passed = []
    checks_failed = []
    
    # 1. Check if seadot_backend package is importable
    try:
        import seadot_backend
        print("✅ Package 'seadot_backend' is importable")
        checks_passed.append("Package import")
    except ImportError as e:
        print(f"❌ Package 'seadot_backend' not found: {e}")
        checks_failed.append("Package import")
    
    # 2. Check api module
    try:
        from seadot_backend import api
        print("✅ Module 'api' is accessible")
        checks_passed.append("API module")
    except ImportError as e:
        print(f"❌ API module not found: {e}")
        checks_failed.append("API module")
    
    # 3. Check core.downloader
    try:
        from seadot_backend.core import downloader
        print("✅ Core 'downloader' is accessible")
        checks_passed.append("Core downloader")
    except ImportError as e:
        print(f"❌ Core downloader not found: {e}")
        checks_failed.append("Core downloader")
    
    # 4. Check db module
    try:
        from seadot_backend.db import models, service
        print("✅ DB module 'models' and 'service' are accessible")
        checks_passed.append("DB module")
    except ImportError as e:
        print(f"❌ DB module not found: {e}")
        checks_failed.append("DB module")
    
    # 5. Check app.py imports
    try:
        from seadot_backend.api.app import app, DownloadManager
        print("✅ FastAPI app imported successfully")
        checks_passed.append("App initialization")
    except ImportError as e:
        print(f"❌ App initialization failed: {e}")
        checks_failed.append("App initialization")
    
    # 6. Check middleware module
    try:
        from seadot_backend.middleware import auth_middleware
        print("✅ Middleware 'auth_middleware' is accessible")
        checks_passed.append("Middleware")
    except ImportError as e:
        print(f"⚠️  Middleware not found (optional for MVP)")
    
    # Print results
    print("\n" + "="*60)
    print("  Verification Results")
    print("="*60)
    print(f"\n✅ Passed: {len(checks_passed)}")
    for check in checks_passed:
        print(f"   • {check}")
    
    if checks_failed:
        print(f"\n❌ Failed: {len(checks_failed)}")
        for check in checks_failed:
            print(f"   • {check}")
    
    # Final status
    all_passed = len(checks_failed) == 0
    
    print("="*60)
    if all_passed:
        print("\n🎉 ALL CHECKS PASSED - Ready to start server!")
        print("Run: python run_dev.py")
    else:
        print("\n⚠️  SOME CHECKS FAILED - Fix issues before starting server")
    
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = verify_package_structure()
    sys.exit(0 if success else 1)
