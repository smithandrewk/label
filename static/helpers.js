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
