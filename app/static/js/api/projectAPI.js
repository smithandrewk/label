export class ProjectAPI {
    static async fetchProjects() {
        try {
            const response = await fetch('/api/projects');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching projects:', error);
            throw error;
        }
    }

    static async fetchProjectSessions(projectId) {
        try {
            // Build URL with query parameter
            const url = `/api/sessions?project_id=${projectId}`;
            
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch sessions');
            
            const sessions = await response.json();
            
            console.log('Fetched sessions for project:', projectId, sessions);
            
            // Debug: Log keep values for each session to understand the data structure
            sessions.forEach(session => {
                console.log(`Session ${session.session_id} (${session.session_name}): keep=${session.keep}, type=${typeof session.keep}`);
            });
            
            return sessions;
        } catch (error) {
            console.error('Error fetching project sessions:', error);
            throw error;
        }
    }
}

export default ProjectAPI;