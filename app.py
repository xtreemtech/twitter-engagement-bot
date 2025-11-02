from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import schedule
from datetime import datetime
import tweepy
from dotenv import load_dotenv
import os
from bot_engine import LevvaBotNoAI  # Import our no-AI bot

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, async_mode='threading')

class BotManager:
    def __init__(self):
        self.bot = None
        self.running = False
        self.schedule_thread = None
        
    def initialize_bot(self):
        """Initialize the bot with Twitter credentials"""
        try:
            twitter_client = tweepy.Client(
                bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
                consumer_key=os.getenv('TWITTER_API_KEY'),
                consumer_secret=os.getenv('TWITTER_API_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            
            self.bot = LevvaBotNoAI(twitter_client)
            self.log_message("🤖 Bot initialized successfully (No AI Version)")
            return True
        except Exception as e:
            self.log_message(f"❌ Bot initialization failed: {e}")
            return False
    
    def start_bot(self):
        """Start the automated bot"""
        if not self.bot:
            if not self.initialize_bot():
                return False
        
        self.running = True
        self.setup_schedule()
        self.log_message("🚀 Bot started - Automated posting enabled")
        
        # Start schedule in a separate thread
        self.schedule_thread = threading.Thread(target=self.run_scheduler)
        self.schedule_thread.daemon = True
        self.schedule_thread.start()
        
        return True
    
    def stop_bot(self):
        """Stop the automated bot"""
        self.running = False
        self.log_message("⏹️ Bot stopped - Automated posting disabled")
    
    def setup_schedule(self):
        """Setup the posting schedule"""
        schedule.clear()
        
        # Content posting (3x daily at optimal times)
        schedule.every().day.at("09:00").do(self.scheduled_post)
        schedule.every().day.at("14:00").do(self.scheduled_post)
        schedule.every().day.at("19:00").do(self.scheduled_post)
        
        # Community engagement (3x daily)
        schedule.every().day.at("10:30").do(self.scheduled_engage)
        schedule.every().day.at("16:00").do(self.scheduled_engage)
        schedule.every().day.at("21:00").do(self.scheduled_engage)
        
        self.log_message("📅 Schedule: Posts at 9:00, 14:00, 19:00 | Engagement at 10:30, 16:00, 21:00")
    
    def run_scheduler(self):
        """Run the schedule loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)
    
    def scheduled_post(self):
        """Scheduled post"""
        if self.bot and self.running:
            self.log_message("🕒 Scheduled post triggered")
            self.manual_post()
    
    def scheduled_engage(self):
        """Scheduled engagement"""
        if self.bot and self.running:
            self.log_message("🕒 Scheduled engagement triggered")
            self.manual_engage()
    
    def manual_post(self):
        """Manual post"""
        if self.bot:
            result = self.bot.post_content()
            if result['success']:
                self.log_message("📝 Manual post created successfully")
            else:
                self.log_message(f"❌ Manual post failed: {result.get('error', 'Unknown error')}")
            return result
        return {"success": False, "error": "Bot not initialized"}
    
    def manual_engage(self):
        """Manual engagement"""
        if self.bot:
            result = self.bot.engage_with_community()
            if result['success']:
                self.log_message(f"💬 Manual engagement: {result['engagements']} interactions")
            else:
                self.log_message(f"❌ Manual engagement failed: {result.get('error', 'Unknown error')}")
            return result
        return {"success": False, "error": "Bot not initialized"}
    
    def log_message(self, message):
        """Send log message to web interface"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        socketio.emit('log_update', {'message': log_entry})
    
    def get_bot_stats(self):
        """Get bot statistics"""
        if self.bot:
            stats = self.bot.get_stats()
            stats['status'] = 'running' if self.running else 'stopped'
            return stats
        return {
            'status': 'not_initialized',
            'last_post': 'Never',
            'posts_today': 0,
            'engagements_today': 0,
            'content_pool_size': 0
        }

# Global bot manager
bot_manager = BotManager()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    if bot_manager.start_bot():
        return jsonify({'success': True, 'message': 'Bot started successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to start bot'})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    bot_manager.stop_bot()
    return jsonify({'success': True, 'message': 'Bot stopped successfully'})

@app.route('/api/post', methods=['POST'])
def manual_post():
    result = bot_manager.manual_post()
    return jsonify(result)

@app.route('/api/engage', methods=['POST'])
def manual_engage():
    result = bot_manager.manual_engage()
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = bot_manager.get_bot_stats()
    return jsonify(stats)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    emit('log_update', {'message': '🔗 Connected to Levva Bot Dashboard'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)