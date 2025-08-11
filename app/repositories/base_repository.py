from app.exceptions import DatabaseError

class BaseRepository:
    """Base repository class providing common database operations"""
    
    def __init__(self, get_db_connection=None):
        self.get_db_connection = get_db_connection
    
    def _get_connection(self):
        """Get database connection with error handling"""
        conn = self.get_db_connection()
        if conn is None:
            raise DatabaseError('Database connection failed')
        return conn
    
    def _execute_query(self, query, params=None, fetch_one=False, fetch_all=False, commit=False, return_cursor=False):
        """
        Execute a database query with proper error handling and cleanup
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single result
            fetch_all: Return all results
            commit: Whether to commit the transaction
            return_cursor: Return cursor object (caller must handle cleanup)
            
        Returns:
            Query result, cursor.rowcount for modifications, or cursor object
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(query, params or ())
            
            if commit:
                conn.commit()
            
            if return_cursor:
                # Caller is responsible for cursor/connection cleanup
                return cursor
            elif fetch_one:
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result
            elif fetch_all:
                result = cursor.fetchall()
                cursor.close()
                conn.close()
                return result
            else:
                rowcount = cursor.rowcount
                cursor.close()
                conn.close()
                return rowcount
                
        except Exception as e:
            if commit:
                conn.rollback()
            cursor.close()
            conn.close()
            raise DatabaseError(f'Database operation failed: {str(e)}')
    
    def _execute_transaction(self, operations):
        """
        Execute multiple operations in a single transaction
        
        Args:
            operations: List of (query, params) tuples
            
        Returns:
            List of results from each operation
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        results = []
        
        try:
            for query, params in operations:
                cursor.execute(query, params or ())
                results.append(cursor.rowcount)
            
            conn.commit()
            return results
            
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f'Transaction failed: {str(e)}')
        finally:
            cursor.close()
            conn.close()
