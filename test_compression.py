#!/usr/bin/env python3
"""
Simple test script to verify gzip compression is working
"""

import requests

def test_compression(url="http://localhost:5001/api/projects"):
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
        # The response.content is already decompressed by requests
        # The Content-Length header shows the compressed size
        compressed_size = int(response.headers.get('Content-Length', 0))
        decompressed_size = len(response.content)
        
        print(f"Compressed size: {compressed_size} bytes")
        print(f"Decompressed size: {decompressed_size} bytes")
        
        if compressed_size > 0:
            compression_ratio = compressed_size / decompressed_size * 100
            savings = (1 - compressed_size / decompressed_size) * 100
            print(f"Compression ratio: {compression_ratio:.1f}% of original")
            print(f"Bandwidth savings: {savings:.1f}%")
        else:
            print("Could not determine compression ratio")
    
    return is_compressed

if __name__ == '__main__':
    test_compression()