#!/usr/bin/env python3
"""
Rollback tool to revert dataset-based projects back to legacy architecture

This script will:
1. Identify migrated projects that were converted to dataset-based
2. Restore original project paths from legacy_path field
3. Remove dataset references while preserving project data
4. Revert project_type back to legacy

Usage:
    python3 rollback_migration.py [--dry-run] [--project-id PROJECT_ID]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database_service import get_db_connection
from app.logging_config import get_logger

logger = get_logger(__name__)

class MigrationRollback:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.rollback_report = {
            'start_time': datetime.now().isoformat(),
            'dry_run': dry_run,
            'projects_processed': 0,
            'projects_rolled_back': 0,
            'errors': [],
            'details': []
        }
    
    def get_migrated_projects(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all projects that were migrated to dataset-based and can be rolled back"""
        conn = get_db_connection()
        if conn is None:
            raise Exception('Database connection failed')
        
        try:
            with conn.cursor() as cursor:
                if project_id:
                    cursor.execute("""
                        SELECT project_id, project_name, participant_id, path, legacy_path, 
                               project_type, analysis_config, labelings
                        FROM projects 
                        WHERE project_id = %s AND project_type = 'dataset_based' 
                        AND legacy_path IS NOT NULL
                    """, (project_id,))
                else:
                    cursor.execute("""
                        SELECT project_id, project_name, participant_id, path, legacy_path, 
                               project_type, analysis_config, labelings
                        FROM projects 
                        WHERE project_type = 'dataset_based' AND legacy_path IS NOT NULL
                        ORDER BY project_id
                    """)
                
                results = cursor.fetchall()
                projects = []
                
                for result in results:
                    analysis_config = json.loads(result[6]) if result[6] else {}
                    
                    # Only rollback projects that were migrated (not manually created as dataset-based)
                    if analysis_config.get('migrated_from') == 'legacy':
                        projects.append({
                            'project_id': result[0],
                            'project_name': result[1],
                            'participant_id': result[2],
                            'current_path': result[3],
                            'legacy_path': result[4],
                            'project_type': result[5],
                            'analysis_config': analysis_config,
                            'labelings': json.loads(result[7]) if result[7] else []
                        })
                
                return projects
                
        finally:
            cursor.close()
            conn.close()
    
    def rollback_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback a single project from dataset-based to legacy"""
        project_id = project['project_id']
        project_name = project['project_name']
        legacy_path = project['legacy_path']
        
        logger.info(f"Rolling back project {project_id}: {project_name}")
        
        try:
            # Verify legacy path still exists
            if not os.path.exists(legacy_path):
                return {
                    'success': False,
                    'error': f"Legacy path no longer exists: {legacy_path}"
                }
            
            if not self.dry_run:
                conn = get_db_connection()
                try:
                    with conn.cursor() as cursor:
                        # Remove dataset references first
                        cursor.execute("""
                            DELETE FROM project_dataset_refs WHERE project_id = %s
                        """, (project_id,))
                        
                        # Restore project to legacy state
                        cursor.execute("""
                            UPDATE projects 
                            SET path = %s,
                                legacy_path = NULL,
                                project_type = 'legacy',
                                analysis_config = NULL
                            WHERE project_id = %s
                        """, (legacy_path, project_id))
                        
                        conn.commit()
                        logger.info(f"Rolled back project {project_id} to legacy type")
                        
                finally:
                    cursor.close()
                    conn.close()
            
            return {
                'success': True,
                'project_id': project_id,
                'project_name': project_name,
                'restored_path': legacy_path
            }
            
        except Exception as e:
            logger.error(f"Error rolling back project {project_id}: {e}")
            return {
                'success': False,
                'project_id': project_id,
                'project_name': project_name,
                'error': str(e)
            }
    
    def rollback_projects(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """Rollback migrated projects to legacy architecture"""
        logger.info(f"Starting rollback {'(DRY RUN)' if self.dry_run else ''}")
        
        # Get migrated projects
        migrated_projects = self.get_migrated_projects(project_id)
        
        if not migrated_projects:
            logger.info("No migrated projects found for rollback")
            self.rollback_report['end_time'] = datetime.now().isoformat()
            return self.rollback_report
        
        logger.info(f"Found {len(migrated_projects)} migrated projects for rollback")
        
        for project in migrated_projects:
            self.rollback_report['projects_processed'] += 1
            
            try:
                result = self.rollback_project(project)
                
                if result['success']:
                    self.rollback_report['projects_rolled_back'] += 1
                    
                    self.rollback_report['details'].append({
                        'project_id': result['project_id'],
                        'project_name': result['project_name'],
                        'status': 'rolled_back',
                        'restored_path': result['restored_path']
                    })
                    
                    logger.info(f"Successfully rolled back project {result['project_id']}: {result['project_name']}")
                else:
                    self.rollback_report['errors'].append({
                        'project_id': result.get('project_id'),
                        'project_name': result.get('project_name'),
                        'error': result['error']
                    })
                    
                    logger.error(f"Failed to rollback project {result.get('project_id')}: {result['error']}")
                    
            except Exception as e:
                self.rollback_report['errors'].append({
                    'project_id': project['project_id'],
                    'project_name': project['project_name'],
                    'error': str(e)
                })
                
                logger.error(f"Exception rolling back project {project['project_id']}: {e}")
        
        self.rollback_report['end_time'] = datetime.now().isoformat()
        
        # Write rollback report
        report_filename = f"rollback_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(self.rollback_report, f, indent=2)
        
        logger.info(f"Rollback {'simulation ' if self.dry_run else ''}completed. Report saved to {report_filename}")
        logger.info(f"Projects processed: {self.rollback_report['projects_processed']}")
        logger.info(f"Projects rolled back: {self.rollback_report['projects_rolled_back']}")
        logger.info(f"Errors: {len(self.rollback_report['errors'])}")
        
        return self.rollback_report

def main():
    parser = argparse.ArgumentParser(description='Rollback migrated projects to legacy architecture')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Perform a dry run without making changes')
    parser.add_argument('--project-id', type=int, 
                       help='Rollback only the specified project ID')
    
    args = parser.parse_args()
    
    rollback = MigrationRollback(dry_run=args.dry_run)
    
    try:
        report = rollback.rollback_projects(args.project_id)
        
        if report['errors']:
            print(f"\nRollback completed with {len(report['errors'])} errors:")
            for error in report['errors']:
                print(f"  - Project {error.get('project_id', 'unknown')}: {error['error']}")
            sys.exit(1)
        else:
            print(f"\nRollback completed successfully!")
            print(f"Projects rolled back: {report['projects_rolled_back']}")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        print(f"Rollback failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()