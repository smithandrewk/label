// Add this helper function if you don't have it already
export function ensureSessionBoutsIsArray(session) {
    if (!session) return;
    
    // If bouts is a string, parse it
    if (typeof session.bouts === 'string') {
        try {
            session.bouts = JSON.parse(session.bouts);
        } catch (e) {
            console.error('Error parsing session.bouts:', e);
            session.bouts = [];
        }
    }
    
    // If bouts is null, undefined, or not an array, initialize it
    if (!session.bouts || !Array.isArray(session.bouts)) {
        session.bouts = [];
    }
}

export function generateDefaultColor(index) {
    const colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
        '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D2B4DE'
    ];
    return colors[index % colors.length];
}

// Convert from pixel positions to data values for Plotly visualizations
export function pixelToData(pixelX, xAxis) {
    return xAxis.range[0] + (pixelX - xAxis._offset) * (xAxis.range[1] - xAxis.range[0]) / xAxis._length;
}

// Plotly layout configurations
export function createDarkLayout(shapes = []) {
    return {
        xaxis: { 
            title: 'Timestamp', 
            rangeslider: { visible: false },
            color: '#ffffff',
            gridcolor: '#444444',
            zerolinecolor: '#666666'
        },
        yaxis: { 
            title: 'Acceleration (m/s²)',
            color: '#ffffff',
            gridcolor: '#444444',
            zerolinecolor: '#666666'
        },
        showlegend: true,
        shapes: shapes,
        paper_bgcolor: '#4a4a4a',
        plot_bgcolor: '#4a4a4a',
        font: {
            color: '#ffffff'
        }
    };
}

export function createLightLayout(shapes = []) {
    return {
        xaxis: { title: 'Timestamp', rangeslider: { visible: false } },
        yaxis: { title: 'Acceleration (m/s²)'},
        showlegend: true,
        shapes: shapes
    };
}
