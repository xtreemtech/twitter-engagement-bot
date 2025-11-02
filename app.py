from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    return jsonify({'success': True, 'message': 'Bot started'})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    return jsonify({'success': True, 'message': 'Bot stopped'})

@app.route('/api/post', methods=['POST'])
def manual_post():
    return jsonify({'success': True, 'message': 'Post created'})

@app.route('/api/engage', methods=['POST'])
def manual_engage():
    return jsonify({'success': True, 'message': 'Engagement done'})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify({
        'status': 'stopped',
        'last_post': 'Never',
        'posts_today': 0,
        'engagements_today': 0,
        'logs': ['[System] Basic version running']
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)