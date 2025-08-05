#!/usr/bin/env python3
"""
Before/After Performance Testing Script
Automatically tests performance before and after optimizations by checking out different commits
"""

import subprocess
import sys
import time
import json
import os
from datetime import datetime

class BeforeAfterTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.before_commit = "23e9ccb"  # Last commit before optimizations
        self.after_commit = "feature/remote-performance-optimizations"  # Current optimized branch
        
    def run_git_command(self, command):
        """Run a git command and return output"""
        try:
            result = subprocess.run(
                command.split(), 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip(), result.stderr.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ Git command failed: {e}")
            return None, e.stderr

    def checkout_commit(self, commit):
        """Checkout a specific commit"""
        print(f"🔄 Checking out commit: {commit}")
        stdout, stderr = self.run_git_command(f"git checkout {commit}")
        if stderr and "error" in stderr.lower():
            print(f"❌ Checkout failed: {stderr}")
            return False
        print(f"✅ Successfully checked out: {commit}")
        return True

    def wait_for_server(self, timeout=30):
        """Wait for Flask server to be ready"""
        import requests
        
        print(f"⏳ Waiting for server at {self.base_url}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/api/projects", timeout=5)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        
        print("❌ Server not responding after timeout")
        return False

    def run_benchmark(self, label="test"):
        """Run the performance benchmark"""
        print(f"📊 Running benchmark: {label}")
        
        try:
            # Run the benchmark script
            result = subprocess.run([
                sys.executable, 
                "performance_benchmark.py", 
                "--url", self.base_url
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✅ Benchmark completed: {label}")
                return True
            else:
                print(f"❌ Benchmark failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Benchmark timed out")
            return False
        except Exception as e:
            print(f"❌ Benchmark error: {e}")
            return False

    def run_compression_test(self, label="test"):
        """Run the compression test"""
        print(f"🗜️ Running compression test: {label}")
        
        try:
            result = subprocess.run([
                sys.executable, 
                "test_compression.py"
            ], capture_output=True, text=True, timeout=30)
            
            print(f"Compression test output ({label}):")
            print(result.stdout)
            
            if result.stderr:
                print(f"Compression test errors: {result.stderr}")
            
            return "gzip" in result.stdout.lower()
            
        except Exception as e:
            print(f"❌ Compression test error: {e}")
            return False

    def prompt_server_restart(self, version):
        """Prompt user to restart the server"""
        print(f"\n🔄 Please restart your Flask server for the {version} version:")
        print(f"   flask run --port 5001")
        print(f"   Then press Enter when the server is running...")
        input()

    def run_full_comparison(self):
        """Run complete before/after comparison"""
        print("🚀 Starting Before/After Performance Comparison")
        print("=" * 60)
        
        # Save current state
        stdout, _ = self.run_git_command("git rev-parse HEAD")
        original_commit = stdout
        
        print(f"📝 Original commit: {original_commit}")
        print(f"📝 Before commit: {self.before_commit}")
        print(f"📝 After commit: {self.after_commit}")
        print()
        
        # Test BEFORE optimizations
        print("🏁 PHASE 1: Testing BEFORE optimizations")
        print("-" * 40)
        
        if not self.checkout_commit(self.before_commit):
            return False
        
        self.prompt_server_restart("BEFORE")
        
        if not self.wait_for_server():
            print("❌ Server not ready for BEFORE test")
            return False
        
        print("📊 Running BEFORE benchmark...")
        before_success = self.run_benchmark("before")
        
        print("🗜️ Testing compression (should show NO compression)...")
        before_compression = self.run_compression_test("before")
        
        # Test AFTER optimizations  
        print("\n🎯 PHASE 2: Testing AFTER optimizations")
        print("-" * 40)
        
        if not self.checkout_commit(self.after_commit):
            return False
        
        self.prompt_server_restart("AFTER")
        
        if not self.wait_for_server():
            print("❌ Server not ready for AFTER test")
            return False
        
        print("📊 Running AFTER benchmark...")
        after_success = self.run_benchmark("after")
        
        print("🗜️ Testing compression (should show gzip compression)...")
        after_compression = self.run_compression_test("after")
        
        # Restore original state
        print(f"\n🔄 Restoring original commit: {original_commit}")
        self.checkout_commit(original_commit)
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        print(f"BEFORE optimizations:")
        print(f"  ✅ Benchmark: {'PASS' if before_success else 'FAIL'}")
        print(f"  🗜️ Compression: {'NONE' if not before_compression else 'ENABLED'}")
        
        print(f"\nAFTER optimizations:")
        print(f"  ✅ Benchmark: {'PASS' if after_success else 'FAIL'}")  
        print(f"  🗜️ Compression: {'ENABLED' if after_compression else 'NONE'}")
        
        print(f"\n💡 Expected improvements:")
        print(f"  • ~80% bandwidth reduction from gzip compression")
        print(f"  • 5-10x faster repeat loading from caching")
        print(f"  • Paginated loading for large datasets")
        print(f"  • Progressive loading with lazy loading")
        
        print(f"\n📊 Check benchmark_results_*.json files for detailed metrics")
        
        return True

def main():
    print("🧪 Before/After Performance Testing Tool")
    print("This will test performance before and after optimizations")
    print("Make sure you have NO uncommitted changes before running!")
    print()
    
    # Check for uncommitted changes
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  WARNING: You have uncommitted changes!")
        print("Commit or stash your changes before running this test.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    base_url = input("Enter base URL (default: http://localhost:5001): ").strip()
    if not base_url:
        base_url = "http://localhost:5001"
    
    tester = BeforeAfterTester(base_url)
    
    print("\n🚨 IMPORTANT:")
    print("1. This script will checkout different commits")
    print("2. You'll need to restart your Flask server between tests")
    print("3. The server must be running for benchmarks to work")
    print("4. Results will be saved to benchmark_results_*.json files")
    
    response = input("\nReady to start? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    success = tester.run_full_comparison()
    
    if success:
        print("\n🎉 Before/After testing completed successfully!")
        print("Check the benchmark result files for detailed performance metrics.")
    else:
        print("\n❌ Testing failed. Check the output above for errors.")

if __name__ == '__main__':
    main()