#!/usr/bin/env python3
"""
Simple test script to verify gzip compression is working
"""

import requests
import gzip

def test_compression(url="http://localhost:5000/api/projects"):
    """Test if API responses are compressed"""
    print(f"Testing compression at: {url}")
    
    # Request with gzip support
    headers = {'Accept-Encoding': 'gzip, deflate'}
    response = requests.get(url, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Content-Encoding: {response.headers.get('Content-Encoding', 'Not set')}")
    print(f"Content-Length: {response.headers.get('Content-Length', 'Not set')}")
    print(f"Response size: {len(response.content)} bytes")
    
    # Check if compressed
    is_compressed = response.headers.get('Content-Encoding') == 'gzip'
    print(f"Compression applied: {is_compressed}")
    
    if is_compressed:
        # Try to decompress to verify it's valid gzip
        try:
            decompressed = gzip.decompress(response.content)
            print(f"Decompressed size: {len(decompressed)} bytes")
            compression_ratio = len(response.content) / len(decompressed) * 100
            print(f"Compression ratio: {compression_ratio:.1f}% (smaller is better)")
        except Exception as e:
            print(f"Error decompressing: {e}")
    
    return is_compressed

if __name__ == '__main__':
    test_compression()