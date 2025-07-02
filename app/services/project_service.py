from app.exceptions import DatabaseError
from app.repositories.project_repository import ProjectRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.session_repository import SessionRepository
import os
import shutil
from datetime import datetime

class ProjectService:
    def __init__(self, project_repository=None, session_repository=None, participant_repository=None):
        self.project_repo: ProjectRepository = project_repository
        self.participant_repo: ParticipantRepository = participant_repository
        self.session_repo: SessionRepository = session_repository
    
    def list_projects(self):
        """Get all projects"""
        return self.project_repo.get_all()
    
    def get_participant_by_code(self, participant_code):
        """Find participant by code"""
        return self.participant_repo.find_by_code(participant_code)

    def insert_project(self, project_name, participant_id, path):
        """Create a new project"""
        return self.project_repo.create(project_name, participant_id, path)

    def create_participant(self, participant_code):
        """Create a new participant, handling race conditions if it already exists"""
        return self.participant_repo.create(participant_code)

    def create_participant_with_details(self, participant_code, first_name, last_name, email, notes):
        """Create a new participant with detailed information"""
        result = self.participant_repo.create_with_details(participant_code, first_name, last_name, email, notes)
        return {
            'participant_id': result['participant_id'],
            'participant_code': result['participant_code']
        }

    def get_project_with_participant(self, project_id):
        """Get detailed project information including participant data"""
        return self.project_repo.find_with_participant(project_id)

    def cleanup_participant_if_needed(self, participant_id):
        """Check if participant has any remaining projects and delete if none exist"""
        remaining_projects = self.participant_repo.count_projects(participant_id)
        if remaining_projects == 0:
            self.participant_repo.delete(participant_id)
            return True
        return False

    def delete_project(self, project_id):
        """Delete a project by ID"""
        return self.project_repo.delete(project_id)

    def get_all_participants_with_stats(self):
        """Get all participants with their project and session statistics"""
        return self.participant_repo.get_all_with_stats()

    def update_participant(self, participant_id, participant_code, first_name, last_name, email, notes):
        """Update an existing participant's information"""
        result = self.participant_repo.update(participant_id, participant_code, first_name, last_name, email, notes)
        return {
            'participant_id': result['participant_id'],
            'participant_code': result['participant_code']
        }

    def get_participant_info(self, participant_id):
        """Get basic participant information"""
        return self.participant_repo.find_by_id(participant_id)

    def get_participant_projects(self, participant_id):
        """Get all projects for a participant"""
        return self.project_repo.find_by_participant(participant_id)

    def count_participant_sessions(self, participant_id):
        """Count total sessions for a participant across all their projects"""
        return self.participant_repo.count_sessions(participant_id)

    def delete_participant_cascade(self, participant_id):
        """Delete participant and all associated data (projects, sessions, lineage)"""
        return self.participant_repo.delete_cascade(participant_id)

    def create_project_with_files(self, project_name, participant_code, uploaded_files, data_dir):
        """
        Create a new project with uploaded files, handling participant creation and file storage
        
        Args:
            project_name: Name of the project
            participant_code: Code for the participant
            uploaded_files: List of uploaded file objects
            data_dir: Base directory for storing project data
            
        Returns:
            dict: Project creation result with project_id, participant_id, and project_path
        """
        # Get or create participant
        participant = self.get_participant_by_code(participant_code)
        if participant:
            participant_id = participant['participant_id']
        else:
            created_participant = self.create_participant(participant_code)
            participant_id = created_participant['participant_id']

        # Create project directory
        central_data_dir = os.path.expanduser(data_dir)
        os.makedirs(central_data_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_dir_name = f"{project_name}_{participant_code}_{timestamp}"
        new_project_path = os.path.join(central_data_dir, project_dir_name)
        
        try:
            # Create project directory and save files
            os.makedirs(new_project_path, exist_ok=True)
            
            # Process uploaded files and recreate directory structure
            for file in uploaded_files:
                if file.filename and file.filename != '':
                    # Get relative path within the selected folder
                    relative_path = file.filename
                    if '/' in relative_path:
                        # Remove the root folder name from the path since we're creating our own structure
                        path_parts = relative_path.split('/')
                        if len(path_parts) > 1:
                            relative_path = '/'.join(path_parts[1:])  # Remove the first part (root folder name)
                    
                    # Create full file path
                    file_path = os.path.join(new_project_path, relative_path)
                    
                    # Create directories if they don't exist
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    # Save the file
                    file.save(file_path)
            
            # Create project record in database
            created_project = self.insert_project(project_name, participant_id, new_project_path)
            
            return {
                'project_id': created_project['project_id'],
                'participant_id': participant_id,
                'project_path': new_project_path,
                'files_processed': len([f for f in uploaded_files if f.filename and f.filename != ''])
            }
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(new_project_path):
                shutil.rmtree(new_project_path)
            raise DatabaseError(f'Failed to create project with files: {str(e)}')

    def get_labelings(self, project_id=None):
        return self.project_repo.get_labelings(project_id)

    def update_labelings(self, project_id, label):
        """Update labelings for a specific project by appending a new label"""
        print(f'Updating labelings for project {project_id} with label: {label}')
        return self.project_repo.update_labelings(project_id, label)
        
    def update_labeling_color(self, project_id, labeling_name, color):
        """Update the color of an existing labeling in a project
        
        Args:
            project_id: ID of the project containing the labeling
            labeling_name: Name of the labeling to update
            color: New color value in hex format (e.g., '#FF0000')
            
        Returns:
            dict: Status and message indicating success or failure
        """
        print(f'Updating color for labeling "{labeling_name}" to {color} in project {project_id}')
        return self.project_repo.update_labeling_color(project_id, labeling_name, color)

    def discover_project_sessions(self, project_path):
        """
        Discover session directories within a project path
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            list: List of session dictionaries with name and file information, sorted by date
        """
        sessions = []
        if os.path.exists(project_path):
            for item in os.listdir(project_path):
                item_path = os.path.join(project_path, item)
                if os.path.isdir(item_path):
                    accel_file = os.path.join(item_path, 'accelerometer_data.csv')
                    if os.path.exists(accel_file):
                        sessions.append({'name': item, 'file': 'accelerometer_data.csv'})
                    elif os.path.exists(os.path.join(item_path, 'accelerometer_data.gz')):
                        # Unzip
                        gz_file = os.path.join(item_path, 'accelerometer_data.gz')
                        csv_file = os.path.join(item_path, 'accelerometer_data.csv')
                        os.system(f'gunzip -c "{gz_file}" | head -n -1 > "{csv_file}"')
                        sessions.append({'name': item, 'file': 'accelerometer_data.csv'})
                        os.remove(gz_file)
                    
                    # TODO: Handle gyroscope data similarly
                    gyro_data = os.path.join(item_path, 'gyroscope_data.csv')
                    gz_file = os.path.join(item_path, 'gyroscope_data.gz')
                    if os.path.exists(gyro_data):
                        os.remove(gyro_data)
                    if os.path.exists(gz_file):
                        os.remove(gz_file)
                        

            
            # Sort sessions by date/time in the name
            try:
                from datetime import datetime
                sessions.sort(key=lambda s: datetime.strptime('_'.join(s['name'].split('_')[:4]), '%Y-%m-%d_%H_%M_%S'))
            except:
                # If sorting fails, keep original order
                pass
        
        return sessions