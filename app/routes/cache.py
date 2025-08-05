"""
Cache Management Routes
Provides endpoints for cache monitoring and management
"""

from flask import Blueprint, jsonify
from app.services.redis_cache_service import redis_cache
from app.services.utils import api_performance_monitor

cache_bp = Blueprint('cache', __name__)

class CacheController:
    def __init__(self):
        self.redis_cache = redis_cache

    @api_performance_monitor
    def get_cache_stats(self):
        """Get comprehensive cache statistics"""
        try:
            redis_stats = self.redis_cache.get_stats()
            redis_health = self.redis_cache.health_check()
            
            return jsonify({
                'redis': {
                    'stats': redis_stats,
                    'health': redis_health
                },
                'recommendations': self._get_recommendations(redis_stats)
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Failed to get cache stats: {str(e)}'}), 500

    def _get_recommendations(self, stats):
        """Generate performance recommendations based on cache stats"""
        recommendations = []
        
        if not stats.get('enabled', False):
            recommendations.append({
                'type': 'warning',
                'message': 'Redis caching is disabled. Enable Redis for better performance.',
                'action': 'Install and configure Redis server'
            })
            return recommendations
        
        # Check hit rate
        hit_rate = float(stats.get('hit_rate', '0%').rstrip('%'))
        if hit_rate < 50:
            recommendations.append({
                'type': 'info', 
                'message': f'Cache hit rate is {hit_rate:.1f}%. Consider increasing TTL for frequently accessed data.',
                'action': 'Review cache TTL settings'
            })
        elif hit_rate > 80:
            recommendations.append({
                'type': 'success',
                'message': f'Excellent cache hit rate of {hit_rate:.1f}%! Remote performance should be significantly improved.',
                'action': 'Monitor and maintain current cache strategy'
            })
        
        # Check error rate
        total_requests = stats.get('total_requests', 0)
        errors = stats.get('errors', 0)
        if total_requests > 0 and (errors / total_requests) > 0.1:
            recommendations.append({
                'type': 'error',
                'message': f'High cache error rate: {errors}/{total_requests}. Check Redis connection.',
                'action': 'Review Redis server logs and connection settings'
            })
        
        return recommendations

    @api_performance_monitor
    def clear_cache(self):
        """Clear all cache entries"""
        try:
            success = self.redis_cache.clear_all()
            
            if success:
                return jsonify({
                    'message': 'Cache cleared successfully',
                    'stats': self.redis_cache.get_stats()
                }), 200
            else:
                return jsonify({'error': 'Failed to clear cache'}), 500
                
        except Exception as e:
            return jsonify({'error': f'Failed to clear cache: {str(e)}'}), 500

    @api_performance_monitor
    def invalidate_pattern(self):
        """Invalidate cache entries matching a pattern"""
        from flask import request
        
        try:
            data = request.get_json()
            pattern = data.get('pattern')
            
            if not pattern:
                return jsonify({'error': 'Pattern is required'}), 400
            
            count = self.redis_cache.invalidate_pattern(pattern)
            
            return jsonify({
                'message': f'Invalidated {count} cache entries',
                'pattern': pattern,
                'count': count
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Failed to invalidate pattern: {str(e)}'}), 500

controller = None

def init_controller():
    global controller
    controller = CacheController()

# Routes
@cache_bp.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    return controller.get_cache_stats()

@cache_bp.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    return controller.clear_cache()

@cache_bp.route('/api/cache/invalidate', methods=['POST'])
def invalidate_pattern():
    return controller.invalidate_pattern()