#!/usr/bin/env python3
"""
Performance Benchmark Script for Issue #78 - Remote Speed Enhancements

This script measures baseline performance metrics before optimizations
and compares them after implementing improvements.

Usage: python performance_benchmark.py [--after]
"""

import time
import requests
import json
import statistics
import argparse
import sys
from datetime import datetime


class PerformanceBenchmark:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = {}
        
    def test_session_data_loading(self, session_id=1, iterations=5):
        """Test session data API loading times"""
        print(f"🔄 Testing session data loading (session_id={session_id}, {iterations} iterations)...")
        
        times = []
        response_sizes = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}/api/session/{session_id}")
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    response_size = len(response.content) / 1024  # KB
                    data_points = len(data.get('data', []))
                    pagination = data.get('pagination', {})
                    
                    times.append(elapsed)
                    response_sizes.append(response_size)
                    
                    print(f"  Iteration {i+1}: {elapsed:.3f}s, {response_size:.1f}KB, {data_points} data points, pagination: {pagination.get('has_more', 'N/A')}")
                else:
                    print(f"  Iteration {i+1}: Failed - HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  Iteration {i+1}: Error - {e}")
                
            time.sleep(0.5)  # Brief pause between requests
            
        if times:
            avg_time = statistics.mean(times)
            avg_size = statistics.mean(response_sizes)
            min_time = min(times)
            max_time = max(times)
            
            self.results['session_data_loading'] = {
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'avg_response_size_kb': avg_size,
                'total_iterations': len(times),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"📊 Session Data Loading Results:")
            print(f"   Average: {avg_time:.3f}s")
            print(f"   Range: {min_time:.3f}s - {max_time:.3f}s") 
            print(f"   Avg Response Size: {avg_size:.1f}KB")
        else:
            print("❌ No successful requests completed")
            
    def test_paginated_session_loading(self, session_id=1, limit=1000, iterations=3):
        """Test paginated session data loading"""
        print(f"🔄 Testing paginated session data loading (limit={limit}, {iterations} iterations)...")
        
        times = []
        response_sizes = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}/api/session/{session_id}?offset=0&limit={limit}")
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    response_size = len(response.content) / 1024  # KB
                    data_points = len(data.get('data', []))
                    pagination = data.get('pagination', {})
                    
                    times.append(elapsed)
                    response_sizes.append(response_size)
                    
                    print(f"  Iteration {i+1}: {elapsed:.3f}s, {response_size:.1f}KB, {data_points} points, has_more: {pagination.get('has_more')}")
                else:
                    print(f"  Iteration {i+1}: Failed - HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  Iteration {i+1}: Error - {e}")
                
            time.sleep(0.2)
            
        if times:
            avg_time = statistics.mean(times)
            avg_size = statistics.mean(response_sizes)
            
            self.results['paginated_session_loading'] = {
                'avg_response_time': avg_time,
                'avg_response_size_kb': avg_size,
                'limit_used': limit,
                'total_iterations': len(times),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"📊 Paginated Session Loading Results (limit={limit}):")
            print(f"   Average: {avg_time:.3f}s")
            print(f"   Avg Response Size: {avg_size:.1f}KB")
        else:
            print("❌ No successful requests completed")
            
    def test_sessions_list_loading(self, project_id=None, iterations=3):
        """Test sessions list API loading times"""
        url = f"{self.base_url}/api/sessions"
        if project_id:
            url += f"?project_id={project_id}"
            
        print(f"🔄 Testing sessions list loading ({iterations} iterations)...")
        
        times = []
        session_counts = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = requests.get(url)
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    sessions = response.json()
                    session_count = len(sessions)
                    
                    times.append(elapsed)
                    session_counts.append(session_count)
                    
                    print(f"  Iteration {i+1}: {elapsed:.3f}s, {session_count} sessions")
                else:
                    print(f"  Iteration {i+1}: Failed - HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  Iteration {i+1}: Error - {e}")
                
            time.sleep(0.2)
            
        if times:
            avg_time = statistics.mean(times)
            avg_count = statistics.mean(session_counts) if session_counts else 0
            
            self.results['sessions_list_loading'] = {
                'avg_response_time': avg_time,
                'avg_session_count': avg_count,
                'total_iterations': len(times),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"📊 Sessions List Loading Results:")
            print(f"   Average: {avg_time:.3f}s")
            print(f"   Avg Sessions: {avg_count:.0f}")
        else:
            print("❌ No successful requests completed")
            
    def test_projects_list_loading(self, iterations=3):
        """Test projects list API loading times"""
        print(f"🔄 Testing projects list loading ({iterations} iterations)...")
        
        times = []
        project_counts = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}/api/projects")
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    projects = response.json()
                    project_count = len(projects)
                    
                    times.append(elapsed)
                    project_counts.append(project_count)
                    
                    print(f"  Iteration {i+1}: {elapsed:.3f}s, {project_count} projects")
                else:
                    print(f"  Iteration {i+1}: Failed - HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  Iteration {i+1}: Error - {e}")
                
            time.sleep(0.2)
            
        if times:
            avg_time = statistics.mean(times)
            avg_count = statistics.mean(project_counts) if project_counts else 0
            
            self.results['projects_list_loading'] = {
                'avg_response_time': avg_time,
                'avg_project_count': avg_count,
                'total_iterations': len(times),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"📊 Projects List Loading Results:")
            print(f"   Average: {avg_time:.3f}s")
            print(f"   Avg Projects: {avg_count:.0f}")
        else:
            print("❌ No successful requests completed")
            
    def save_results(self, filename):
        """Save benchmark results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"💾 Results saved to {filename}")
        
    def compare_results(self, before_file, after_file):
        """Compare before and after benchmark results"""
        try:
            with open(before_file, 'r') as f:
                before = json.load(f)
            with open(after_file, 'r') as f:  
                after = json.load(f)
                
            print(f"\n📈 PERFORMANCE COMPARISON")
            print(f"=" * 50)
            
            for test_name in before.keys():
                if test_name in after:
                    before_time = before[test_name]['avg_response_time']
                    after_time = after[test_name]['avg_response_time']
                    improvement = (before_time - after_time) / before_time * 100
                    
                    print(f"\n{test_name.replace('_', ' ').title()}:")
                    print(f"  Before: {before_time:.3f}s")
                    print(f"  After:  {after_time:.3f}s")
                    print(f"  Improvement: {improvement:+.1f}%")
                    
                    if 'avg_response_size_kb' in before[test_name] and 'avg_response_size_kb' in after[test_name]:
                        before_size = before[test_name]['avg_response_size_kb']
                        after_size = after[test_name]['avg_response_size_kb']
                        size_reduction = (before_size - after_size) / before_size * 100
                        print(f"  Size Before: {before_size:.1f}KB")
                        print(f"  Size After:  {after_size:.1f}KB")
                        print(f"  Size Reduction: {size_reduction:+.1f}%")
                        
        except FileNotFoundError as e:
            print(f"❌ Could not load benchmark file: {e}")
        except Exception as e:
            print(f"❌ Error comparing results: {e}")
            
    def run_full_benchmark(self):
        """Run complete benchmark suite"""
        print(f"🚀 Starting Performance Benchmark")
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Test core endpoints
        self.test_projects_list_loading()
        print()
        self.test_sessions_list_loading()
        print()
        self.test_session_data_loading()
        print()
        self.test_paginated_session_loading()
        
        print("\n✅ Benchmark completed!")


def main():
    parser = argparse.ArgumentParser(description='Performance benchmark for Issue #78')
    parser.add_argument('--after', action='store_true', help='Run post-optimization benchmark')
    parser.add_argument('--compare', nargs=2, metavar=('BEFORE', 'AFTER'), 
                       help='Compare two benchmark result files')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL for API tests')
    
    args = parser.parse_args()
    
    if args.compare:
        benchmark = PerformanceBenchmark()
        benchmark.compare_results(args.compare[0], args.compare[1])
        return
        
    benchmark = PerformanceBenchmark(args.url)
    benchmark.run_full_benchmark()
    
    # Save results
    suffix = 'after' if args.after else 'before'
    filename = f'benchmark_results_{suffix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    benchmark.save_results(filename)
    
    print(f"\n💡 Next steps:")
    if not args.after:
        print(f"   1. Implement performance optimizations")
        print(f"   2. Run: python {sys.argv[0]} --after")
        print(f"   3. Compare: python {sys.argv[0]} --compare {filename} <after_file>")
    else:
        print(f"   Run comparison with your 'before' results file")


if __name__ == '__main__':
    main()