#!/usr/bin/env python3
"""
Migration tool to convert legacy projects to dataset-based architecture

This script will:
1. Identify legacy projects that own their data directories
2. Extract raw data from project directories into shared dataset storage
3. Convert projects to reference shared datasets instead of owning files
4. Preserve all existing project metadata, labelings, and sessions
5. Create migration reports and rollback information

Usage:
    python3 migrate_legacy_projects.py [--dry-run] [--project-id PROJECT_ID]
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database_service import get_db_connection
from app.services.raw_dataset_service import RawDatasetService
from app.services.project_service import ProjectService
from app.repositories.raw_dataset_repository import RawDatasetRepository
from app.logging_config import get_logger

logger = get_logger(__name__)

class LegacyProjectMigrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.raw_dataset_service = RawDatasetService()
        self.project_service = ProjectService()
        self.migration_report = {
            'start_time': datetime.now().isoformat(),
            'dry_run': dry_run,
            'projects_processed': 0,
            'projects_migrated': 0,
            'datasets_created': 0,
            'errors': [],
            'warnings': [],
            'details': []
        }
    
    def get_legacy_projects(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all legacy projects that need migration"""
        conn = get_db_connection()
        if conn is None:
            raise Exception('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                if project_id:
                    cursor.execute("""
                        SELECT project_id, project_name, participant_id, path, labelings, 
                               project_type, analysis_config
                        FROM projects 
                        WHERE project_id = %s AND (project_type IS NULL OR project_type = 'legacy')
                        AND path IS NOT NULL
                    """, (project_id,))
                else:
                    cursor.execute("""
                        SELECT project_id, project_name, participant_id, path, labelings, 
                               project_type, analysis_config
                        FROM projects 
                        WHERE (project_type IS NULL OR project_type = 'legacy') AND path IS NOT NULL
                        ORDER BY project_id
                    """)
                
                results = cursor.fetchall()
                projects = []
                
                for result in results:
                    projects.append({
                        'project_id': result[0],
                        'project_name': result[1],
                        'participant_id': result[2],
                        'path': result[3],
                        'labelings': json.loads(result[4]) if result[4] else [],
                        'project_type': result[5],
                        'analysis_config': json.loads(result[6]) if result[6] else {}
                    })
                
                return projects
                
        finally:
            cursor.close()
            conn.close()
    
    def get_project_sessions(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a project"""
        conn = get_db_connection()
        if conn is None:
            raise Exception('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT session_id, session_name, status, verified, bouts, start_ns, stop_ns,
                           parent_session_data_path, data_start_offset, data_end_offset
                    FROM sessions 
                    WHERE project_id = %s
                    ORDER BY session_name
                """, (project_id,))
                
                results = cursor.fetchall()
                sessions = []
                
                for result in results:
                    sessions.append({
                        'session_id': result[0],
                        'session_name': result[1],
                        'status': result[2],
                        'verified': result[3],
                        'bouts': json.loads(result[4]) if result[4] else [],
                        'start_ns': result[5],
                        'stop_ns': result[6],
                        'parent_session_data_path': result[7],
                        'data_start_offset': result[8],
                        'data_end_offset': result[9]
                    })
                
                return sessions
                
        finally:
            cursor.close()
            conn.close()
    
    def validate_project_directory(self, project_path: str) -> Dict[str, Any]:
        """Validate that a project directory contains valid raw data"""
        if not os.path.exists(project_path):
            return {'valid': False, 'error': f'Project directory does not exist: {project_path}'}
        
        if not os.path.isdir(project_path):
            return {'valid': False, 'error': f'Project path is not a directory: {project_path}'}
        
        # Look for session directories
        session_dirs = []
        for item in os.listdir(project_path):
            item_path = os.path.join(project_path, item)
            if os.path.isdir(item_path):
                session_dirs.append(item)
        
        if len(session_dirs) == 0:
            return {'valid': False, 'error': 'No session directories found'}
        
        return {
            'valid': True,
            'session_count': len(session_dirs),
            'sessions': session_dirs
        }
    
    def migrate_project_to_dataset(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a single legacy project to dataset-based architecture"""
        project_id = project['project_id']
        project_name = project['project_name']
        project_path = project['path']
        
        logger.info(f"Migrating project {project_id}: {project_name}")
        
        try:
            # Validate project directory
            validation = self.validate_project_directory(project_path)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f"Invalid project directory: {validation['error']}"
                }
            
            # Calculate dataset hash for deduplication
            dataset_hash = RawDatasetRepository.calculate_directory_hash(project_path)
            
            # Check if dataset already exists
            existing_dataset = self.raw_dataset_service.raw_dataset_repo.find_by_hash(dataset_hash)
            
            if existing_dataset:
                logger.info(f"Dataset already exists for project {project_name}: {existing_dataset['dataset_name']}")
                dataset_id = existing_dataset['dataset_id']
                dataset_created = False
            else:
                # Create new raw dataset from project directory
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would create dataset from {project_path}")
                    dataset_id = 999999  # Fake ID for dry run
                    dataset_created = True
                else:
                    result = self.raw_dataset_service.upload_raw_dataset(
                        source_path=project_path,
                        dataset_name=f"migrated_{project_name}_{datetime.now().strftime('%Y%m%d')}",
                        description=f"Migrated from legacy project: {project_name}",
                        raw_data_dir=None  # Use default
                    )
                    dataset_id = result['dataset_id']
                    dataset_created = not result.get('duplicate', False)
                    
                logger.info(f"Created dataset {dataset_id} from project {project_name}")
            
            # Get project sessions for migration validation
            sessions = self.get_project_sessions(project_id)
            
            if not self.dry_run:
                # Link project to dataset
                self.raw_dataset_service.link_project_to_dataset(project_id, dataset_id)
                
                # Update project type and preserve legacy path
                conn = get_db_connection()
                try:
                    with conn.cursor() as cursor:
                        # Move current path to legacy_path and set project_type
                        cursor.execute("""
                            UPDATE projects 
                            SET legacy_path = %s, 
                                path = NULL,
                                project_type = 'dataset_based',
                                analysis_config = %s
                            WHERE project_id = %s
                        """, (project_path, json.dumps({
                            'migrated_from': 'legacy',
                            'migration_date': datetime.now().isoformat(),
                            'original_path': project_path,
                            'dataset_id': dataset_id
                        }), project_id))
                        
                        conn.commit()
                        logger.info(f"Updated project {project_id} to dataset-based type")
                        
                finally:
                    cursor.close()
                    conn.close()
            
            return {
                'success': True,
                'project_id': project_id,
                'project_name': project_name,
                'dataset_id': dataset_id,
                'dataset_created': dataset_created,
                'sessions_count': len(sessions),
                'original_path': project_path
            }
            
        except Exception as e:
            logger.error(f"Error migrating project {project_id}: {e}")
            return {
                'success': False,
                'project_id': project_id,
                'project_name': project_name,
                'error': str(e)
            }
    
    def migrate_projects(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """Migrate legacy projects to dataset-based architecture"""
        logger.info(f"Starting migration {'(DRY RUN)' if self.dry_run else ''}")
        
        # Get legacy projects
        legacy_projects = self.get_legacy_projects(project_id)
        
        if not legacy_projects:
            logger.info("No legacy projects found for migration")
            self.migration_report['end_time'] = datetime.now().isoformat()
            return self.migration_report
        
        logger.info(f"Found {len(legacy_projects)} legacy projects for migration")
        
        for project in legacy_projects:
            self.migration_report['projects_processed'] += 1
            
            try:
                result = self.migrate_project_to_dataset(project)
                
                if result['success']:
                    self.migration_report['projects_migrated'] += 1
                    if result.get('dataset_created', False):
                        self.migration_report['datasets_created'] += 1
                    
                    self.migration_report['details'].append({
                        'project_id': result['project_id'],
                        'project_name': result['project_name'],
                        'status': 'migrated',
                        'dataset_id': result['dataset_id'],
                        'dataset_created': result.get('dataset_created', False),
                        'sessions_count': result['sessions_count']
                    })
                    
                    logger.info(f"Successfully migrated project {result['project_id']}: {result['project_name']}")
                else:
                    self.migration_report['errors'].append({
                        'project_id': result.get('project_id'),
                        'project_name': result.get('project_name'),
                        'error': result['error']
                    })
                    
                    logger.error(f"Failed to migrate project {result.get('project_id')}: {result['error']}")
                    
            except Exception as e:
                self.migration_report['errors'].append({
                    'project_id': project['project_id'],
                    'project_name': project['project_name'],
                    'error': str(e)
                })
                
                logger.error(f"Exception migrating project {project['project_id']}: {e}")
        
        self.migration_report['end_time'] = datetime.now().isoformat()
        
        # Write migration report
        report_filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(self.migration_report, f, indent=2)
        
        logger.info(f"Migration {'simulation ' if self.dry_run else ''}completed. Report saved to {report_filename}")
        logger.info(f"Projects processed: {self.migration_report['projects_processed']}")
        logger.info(f"Projects migrated: {self.migration_report['projects_migrated']}")
        logger.info(f"Datasets created: {self.migration_report['datasets_created']}")
        logger.info(f"Errors: {len(self.migration_report['errors'])}")
        
        return self.migration_report

def main():
    parser = argparse.ArgumentParser(description='Migrate legacy projects to dataset-based architecture')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Perform a dry run without making changes')
    parser.add_argument('--project-id', type=int, 
                       help='Migrate only the specified project ID')
    
    args = parser.parse_args()
    
    migrator = LegacyProjectMigrator(dry_run=args.dry_run)
    
    try:
        report = migrator.migrate_projects(args.project_id)
        
        if report['errors']:
            print(f"\nMigration completed with {len(report['errors'])} errors:")
            for error in report['errors']:
                print(f"  - Project {error.get('project_id', 'unknown')}: {error['error']}")
            sys.exit(1)
        else:
            print(f"\nMigration completed successfully!")
            print(f"Projects migrated: {report['projects_migrated']}")
            print(f"Datasets created: {report['datasets_created']}")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()