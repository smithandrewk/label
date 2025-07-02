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

    static async fetchLabelingMetadata(projectId) {
        try {
            const response = await fetch(`/api/labeling_metadata?project_id=${projectId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch labeling metadata');
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching labeling metadata:', error);
            throw error;
        }
    }
    /**
     * Fetch labelings for a given project
     * @param {string|number} projectId
     * @returns {Promise<Object[]>}
     */
    static async fetchLabelings(projectId) {
        const response = await fetch(`/api/labelings/${projectId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // Parse the labelings JSON string
        let labelings = [];
        if (data.length > 0 && data[0].labelings) {
            try {
                labelings = JSON.parse(data[0].labelings);
            } catch (e) {
                console.error('Error parsing labelings JSON:', e);
                labelings = [];
            }
        }

        return labelings;
    }

}

export default ProjectAPI;