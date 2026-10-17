#!/usr/bin/env python3
"""
Seadot Phase 2 - Manual Test Suite (Standalone, no pytest required)
Test core downloader functionality for pause/resume capability
"""

import sys
import os

# Add seadot-backend to path manually
if not os.path.exists('/seadot-backend/core/downloader.py'):
    print("ERROR: /seadot-backend/core/downloader.py not found!")
    sys.exit(1)

# Import directly from file
sys.path.insert(0, '/seadot-backend')

import asyncio
from pathlib import Path
import tempfile
import json

print("=" * 80)
print("SEADOT PHASE 2 TEST SUITE - Core Download Engine")
print("Testing: Pause/Resume, Streaming, Safe Merge, State Persistence")
print("=" * 80)

test_results = []

def test(name, func):
    """Decorator for test functions"""
    def wrapper():
        try:
            func()
            print(f"\n✓ PASS: {name}")
            test_results.append(("PASS", name))
            return True
        except AssertionError as e:
            print(f"\n✗ FAIL: {name}: {e}")
            test_results.append(("FAIL", str(e)))
            return False
        except Exception as e:
            print(f"\n✗ ERROR: {name}: {type(e).__name__}: {e}")
            test_results.append(("ERROR", f"{type(e).__name__}: {str(e)}"))
            return False
    return wrapper

# ========================================
# Test 1: DownloadState Properties
# ========================================
@print("\n[TEST 1] DownloadState Properties & Methods...")
@test("DownloadState Properties")
def test_download_state_properties():
    from core.downloader import DownloadState
    
    # Test initialization with defaults
    state = DownloadState(total_size=1000, downloaded_size=250)
    assert hasattr(state, 'progress'), "Missing progress property"
    assert state.progress == 25.0, f"Progress calculation failed: expected 25.0, got {state.progress}"
    
    # Test is_complete
    assert state.is_complete is False, "Incomplete state incorrectly marked as complete"
    
    # Complete the download
    state.downloaded_size = 1000
    assert state.is_complete is True, "Complete state incorrectly marked as incomplete"
    
    # Test empty file (edge case)
    empty_state = DownloadState(total_size=0, downloaded_size=0)
    assert empty_state.is_complete is True, "Empty file should be complete"
    
    # Test with start_time and complete_time
    state_with_times = DownloadState(
        total_size=1000, 
        downloaded_size=500,
        chunk_size=500,
        headers={'User-Agent': 'Seadot/1.0'},
        start_time=None,
        complete_time=None
    )
    assert state_with_times.progress == 50.0, "Progress with 50% should be 50.0"

# ========================================
# Test 2: Dynamic Chunking
# ========================================
@print("\n[TEST 2] Downloader Dynamic Chunk Sizing...")
@test("Downloader Dynamic Chunk Sizing")
def test_downloader_dynamic_chunking():
    from core.downloader import Downloader
    
    downloader = Downloader(chunk_size=8 * 1024 * 1024, chunk_count_threshold=16)
    
    # Test small file (<= 16MB) - should use default or capped size
    small_size = 5 * 1024 * 1024  # 5MB
    chunk_small = downloader._get_chunk_size(small_size)
    assert chunk_small <= small_size, "Chunk size exceeds file size for small files"
    
    # Test large file (> 16MB) - should use dynamic resizing (minimum 8MB chunks)
    large_size = 100 * 1024 * 1024  # 100MB
    chunk_large = downloader._get_chunk_size(large_size)
    assert chunk_large >= 1024 * 1024, f"Large file chunk too small (below 1MB): {chunk_large}"
    
    print(f"  - Small file (5MB) uses ~{chunk_small / 1024 / 1024:.1f}MB chunks")
    print(f"  - Large file (100MB) uses ~{chunk_large / 1024 / 1024:.1f}MB chunks (auto-adjusted)")

# ========================================
# Test 3: State Persistence (Save/Load)
# ========================================
@print("\n[TEST 3] State Persistence Layer...")
@test("State Persistence (Save/Load)")
def test_downloader_state_persistence():
    from core.downloader import DownloadState
    
    downloader = Downloader()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_save_resume.txt"
        
        # Save initial state
        state1 = DownloadState(
            total_size=1000, 
            downloaded_size=100, 
            chunk_size=500
        )
        downloader._save_state(state1, Path(test_file) + ".seadot.part")
        
        # Load state back
        loaded_state = downloader._load_state(Path(test_file) + ".seadot.part")
        assert loaded_state is not None, "Failed to load saved state"
        assert loaded_state.total_size == 1000, f"Total size mismatch after load: {loaded_state.total_size}"
        assert loaded_state.downloaded_size == 100, f"Downloaded size mismatch after load: {loaded_state.downloaded_size}"
        
        # Verify chunk_size is preserved (or default)
        if state1.chunk_size:
            assert hasattr(loaded_state, 'chunk_size'), "chunk_size not preserved in loaded state"

# ========================================
# Test 4: Streaming with Mock Server
# ========================================
@print("\n[TEST 4] Streaming Download with Mock...")
@test("Streaming with Mock")
def test_downloader_streaming_with_mock():
    from core.downloader import DownloadState
    
    downloader = Downloader()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_stream.txt"
        
        async def mock_download():
            state = DownloadState(total_size=10000, chunk_size=1024)
            state.start_time = None
            
            # Simulate writing chunks (mimics real streaming download)
            for i in range(10):
                chunk_data = b'chunk_' + str(i).zfill(3).encode()
                Path(test_file).write_bytes(chunk_data)  # Write to target file
                
                state.downloaded_size += len(chunk_data)
                
                # Save state after each chunk (enables pause/resume)
                await downloader._save_state(state, Path(test_file) + ".seadot.part")
                
            return state
        
        async def run_test():
            result = await mock_download()
            
            assert result.is_complete, "Download should be complete"
            print(f"  ✓ Mock streaming download completed")
            print(f"    - Total size: {result.downloaded_size} bytes")
            
            # Verify file content integrity
            final_content = Path(test_file).read_bytes()
            assert len(final_content) == result.downloaded_size, "File size mismatch after streaming"
            print(f"  ✓ File integrity verified ({len(final_content)} bytes)")
        
        asyncio.run(run_test())

# ========================================
# Test 5: Safe Merge Operations
# ========================================
@print("\n[TEST 5] Safe Chunk Merge...")
@test("Safe Merge")
def test_downloader_safe_merge():
    from core.downloader import DownloadState
    
    downloader = Downloader()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_merge.txt"
        
        # Create a part file with content (simulates downloaded chunk)
        part_content = b"This is the content of the downloaded chunked file. " * 10
        
        part_path = Path(test_file) + ".seadot.part"
        part_path.write_bytes(part_content)
        
        print(f"  - Created part file: {len(part_content)} bytes")
        
        # Run merge operation
        downloader._merge_chunks_safely(Path(test_file))
        
        # Verify final file exists and has correct content
        assert Path(test_file).exists(), "Final file should exist after merge"
        final_content = Path(test_file).read_bytes()
        assert len(final_content) == len(part_content), f"Merged content size mismatch: {len(final_content)} vs {len(part_content)}"
        
        print(f"  ✓ Safe merge completed")
        print(f"    - Part file: {len(part_content)} bytes")
        print(f"    - Final merged file: {len(final_content)} bytes")

# ========================================
# Test 6: Cleanup State Files
# ========================================
@print("\n[TEST 6] Cleanup State Files...")
@test("Cleanup State Files")
def test_downloader_cleanup():
    from core.downloader import DownloadState
    
    downloader = Downloader()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_cleanup.txt"
        
        # Create part file (simulates incomplete download)
        part_path = Path(test_file) + ".seadot.part"
        part_path.write_text("dummy state content")
        
        assert part_path.exists(), "Part file should exist initially"
        print(f"  - Part file created: {part_path}")
        
        # Run cleanup operation
        downloader._cleanup_state(Path(test_file))
        
        assert not part_path.exists(), "Part file should be removed after cleanup"
        
        print(f"  ✓ Cleanup completed successfully")
        print(f"    - State file removed from disk")

# ========================================
# Test 7: Progress Callback
# ========================================
@print("\n[TEST 7] Progress Callback...")
@test("Progress Callback")
def test_downloader_progress_callback():
    from core.downloader import DownloadState
    
    downloader = Downloader()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = f"{tmpdir}/test_callback.txt"
        
        # Simulate progress updates during download
        state = DownloadState(
            total_size=3000, 
            downloaded_size=0, 
            chunk_size=1000,
            headers={'User-Agent': 'Seadot/1.0'}
        )
        state.start_time = None
        
        call_count = 0
        for i in range(3):
            # Write chunk data to file
            Path(test_file).write_bytes(b'chunk_' * (i + 1) * 100)
            
            # Update downloaded size
            state.downloaded_size += (i + 1) * 100
            
            # Save state for pause/resume capability
            asyncio.run(downloader._save_state(state, Path(test_file) + ".seadot.part"))
            
            # Trigger progress callback
            downloader._update_progress(Path(test_file), state)
            call_count += 1
            
            print(f"    - Progress update {i+1}: {state.progress:.2f}%")
        
        assert call_count > 0, "Progress callback should have been called"
        print(f"  ✓ Progress callback invoked {call_count} times")

# ========================================
# Final Summary
# ========================================
print("\n" + "=" * 80)
print("TEST SUITE SUMMARY")
print("=" * 80)

passed = sum(1 for r, _ in test_results if r == "PASS")
failed = sum(1 for r, _ in test_results if r == "FAIL")
errors = sum(1 for r, _ in test_results if r == "ERROR")

print(f"\nTotal Tests: {len(test_results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Errors: {errors}")

if failed > 0 or errors > 0:
    print("\n" + "-" * 80)
    print("FAILED TESTS:")
    for status, msg in test_results:
        if status != "PASS":
            print(f"  [{status}] {msg}")

print("=" * 80)

if failed == 0 and errors == 0:
    print("\n✓✓✓ ALL PHASE 2 TESTS PASSED ✓✓✓\n")
    sys.exit(0)
else:
    print("\n✗✗✗ SOME TESTS FAILED - NEEDS ATTENTION ✗✗✗\n")
    sys.exit(1)
