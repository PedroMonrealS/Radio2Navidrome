from flask import Blueprint, request, jsonify
from services.stats_service import (
    get_stats,
    get_top_artists,
    get_top_albums,
    get_songs,
    get_history
)

stats_bp = Blueprint('stats_bp', __name__)

@stats_bp.route('/api/stats')
def api_stats():
    range_val = request.args.get('range', 'all')
    try:
        data = get_stats(range_val)
        return jsonify(data)
    except Exception as e:
        print(f"Error api_stats: {e}")
        return jsonify({"error": str(e)}), 500

@stats_bp.route('/api/top-artists')
def api_top_artists():
    range_val = request.args.get('range', 'all')
    try:
        data = get_top_artists(range_val)
        return jsonify(data)
    except Exception as e:
        print(f"Error api_top_artists: {e}")
        return jsonify({"error": str(e)}), 500

@stats_bp.route('/api/top-albums')
def api_top_albums():
    range_val = request.args.get('range', 'all')
    try:
        data = get_top_albums(range_val)
        return jsonify(data)
    except Exception as e:
        print(f"Error api_top_albums: {e}")
        return jsonify({"error": str(e)}), 500

@stats_bp.route('/api/songs')
def api_songs():
    range_val = request.args.get('range', 'all')
    try:
        data = get_songs(range_val)
        return jsonify(data)
    except Exception as e:
        print(f"Error api_songs: {e}")
        return jsonify({"error": str(e)}), 500

@stats_bp.route('/api/history')
def api_history():
    limit = min(max(int(request.args.get('limit', 50)), 1), 200)
    offset = max(int(request.args.get('offset', 0)), 0)
    search = request.args.get('search', '').strip()
    try:
        data = get_history(limit, offset, search)
        return jsonify(data)
    except Exception as e:
        print(f"Error api_history: {e}")
        return jsonify({"error": str(e)}), 500
