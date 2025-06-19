import plotly.express as px
import pandas as pd
import os
import numpy as np

class VirtualSplitter:
    def __init__(self, file_path):
        self.file_path = file_path
        self._total_rows = None
        self._headers = None
        
    def get_headers(self):
        """Get the column headers from the file"""
        if self._headers is None:
            # Read just the header row
            self._headers = pd.read_csv(self.file_path, nrows=0).columns.tolist()
        return self._headers
        
    def get_total_rows(self):
        """Get total number of rows in the file (excluding header)"""
        if self._total_rows is None:
            # Fast way to count rows
            with open(self.file_path, 'r') as f:
                self._total_rows = sum(1 for line in f) - 1  # -1 for header
        return self._total_rows
    
    def load_left_chunk(self, split_index, sample_rate=1):
        """Load data before split_index (rows 0 to split_index-1)"""
        if split_index <= 0:
            return pd.DataFrame()  # Empty dataframe
        
        df = pd.read_csv(self.file_path, nrows=split_index)
        
        if sample_rate > 1:
            df = df.iloc[::sample_rate]
        
        return df
    
    def load_right_chunk(self, split_index, sample_rate=1):
        """Load data from split_index onwards"""
        total_rows = self.get_total_rows()
        
        if split_index >= total_rows:
            return pd.DataFrame()  # Empty dataframe
        
        # Load data without header, then assign column names
        df = pd.read_csv(self.file_path, skiprows=split_index+1, header=None)
        df.columns = self.get_headers()  # Assign proper column names
        
        if sample_rate > 1:
            df = df.iloc[::sample_rate]
        
        return df
    
    def load_chunk_by_range(self, start_index, end_index, sample_rate=1):
        """Load data between start_index (inclusive) and end_index (exclusive)"""
        if start_index >= end_index or start_index < 0:
            return pd.DataFrame()
        
        nrows = end_index - start_index
        
        if start_index == 0:
            # First chunk includes header
            df = pd.read_csv(self.file_path, nrows=nrows)
        else:
            # Other chunks need header assigned
            df = pd.read_csv(self.file_path, skiprows=start_index+1, nrows=nrows, header=None)
            df.columns = self.get_headers()
        
        if sample_rate > 1:
            df = df.iloc[::sample_rate]
        
        return df
    
    def load_chunk_by_index(self, chunk_index, split_indices, sample_rate=1):
        """Load a specific chunk based on split indices"""
        sorted_splits = sorted(split_indices)
        
        if chunk_index == 0:
            # First chunk: from start to first split
            if not sorted_splits:
                df = pd.read_csv(self.file_path)
            else:
                df = self.load_left_chunk(sorted_splits[0], sample_rate)
            return df
        
        elif chunk_index <= len(sorted_splits):
            # Middle chunks: between splits
            if chunk_index == len(sorted_splits):
                # Last chunk: from last split to end
                return self.load_right_chunk(sorted_splits[-1], sample_rate)
            else:
                # Between two splits
                start_idx = sorted_splits[chunk_index - 1]
                end_idx = sorted_splits[chunk_index]
                return self.load_chunk_by_range(start_idx, end_idx, sample_rate)
        
        else:
            return pd.DataFrame()  # Invalid chunk index
    
    def get_chunk_info(self, split_indices):
        """Get information about all chunks without loading them"""
        total_rows = self.get_total_rows()
        sorted_splits = sorted(split_indices)
        
        chunks_info = []
        
        # First chunk
        first_chunk_size = sorted_splits[0] if sorted_splits else total_rows
        chunks_info.append({
            'chunk_index': 0,
            'start_row': 0,
            'end_row': first_chunk_size,
            'num_rows': first_chunk_size
        })
        
        # Middle chunks
        for i in range(len(sorted_splits) - 1):
            start_row = sorted_splits[i]
            end_row = sorted_splits[i + 1]
            chunks_info.append({
                'chunk_index': i + 1,
                'start_row': start_row,
                'end_row': end_row,
                'num_rows': end_row - start_row
            })
        
        # Last chunk (if there are splits)
        if sorted_splits:
            last_start = sorted_splits[-1]
            chunks_info.append({
                'chunk_index': len(sorted_splits),
                'start_row': last_start,
                'end_row': total_rows,
                'num_rows': total_rows - last_start
            })
        
        return {
            'total_rows': total_rows,
            'num_chunks': len(chunks_info),
            'chunks': chunks_info,
            'headers': self.get_headers()
        }
    
    def load_multiple_chunks(self, split_indices, sample_rate=1, chunk_indices=None):
        """Load multiple chunks efficiently"""
        info = self.get_chunk_info(split_indices)
        
        if chunk_indices is None:
            chunk_indices = range(info['num_chunks'])
        
        chunks = {}
        for chunk_idx in chunk_indices:
            chunk_data = self.load_chunk_by_index(chunk_idx, split_indices, sample_rate)
            if not chunk_data.empty:
                chunks[f'chunk_{chunk_idx}'] = chunk_data
        
        return chunks

# Usage example with your data
dir = 'mariah_phase1'
recordings = os.listdir(dir)
file_path = f'{dir}/{recordings[1]}/accelerometer_data.csv'

# Create virtual splitter
splitter = VirtualSplitter(file_path)

# Your split points (now as row indices instead of timestamps)
split_indices = [100000, 200000, 300000]  # Example row indices

# Get information about chunks
info = splitter.get_chunk_info(split_indices)
print("Chunk Information:")
print(f"Headers: {info['headers']}")
for chunk_info in info['chunks']:
    print(f"Chunk {chunk_info['chunk_index']}: rows {chunk_info['start_row']}-{chunk_info['end_row']} ({chunk_info['num_rows']} rows)")

# Load multiple chunks at once - now with proper headers!
chunks = splitter.load_multiple_chunks(split_indices, sample_rate=50, chunk_indices=[0, 1, 2, 3])

for chunk_name, chunk_data in chunks.items():
    print(f"{chunk_name} shape: {chunk_data.shape}")
    print(f"{chunk_name} columns: {list(chunk_data.columns)}")
    
    if not chunk_data.empty:
        fig = px.line(chunk_data, x='ns_since_reboot', y='x', 
                      title=f'{chunk_name}: Accelerometer Data')
        fig.show(renderer='browser')