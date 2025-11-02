from flask import Flask, render_template, request, jsonify
import threading
import time
import schedule
from datetime import datetime
import tweepy
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

class SimpleBot:
    def __init__(self):
        self.running = False
        self.logs = []
        self.last_post = "Never"
        self.posts_today = 0
        self.engagements_today = 0
        
    def initialize_twitter(self):
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
                consumer_key=os.getenv('TWITTER_API_KEY'),
                consumer_secret=os.getenv('TWITTER_API_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            
            # Test connection
            user = self.client.get_me()
            self.add_log(f"✅ Twitter connected: @{user.data.username}")
            return True
        except Exception as e:
            self.add_log(f"❌ Twitter failed: {e}")
            return False
    
    def add_log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        # Keep only last 20 logs
        if len(self.logs) > 20:
            self.logs = self.logs[-20:]
        print(log_entry)
    
    def post_content(self):
        try:
            content = f"🚀 Testing Levva Bot from Railway! AI DeFi made easy. {os.getenv('LEVVA_UTM_LINK')}"
            response = self.client.create_tweet(text=content)
            self.last_post = datetime.now().strftime('%H:%M:%S')
            self.posts_today += 1
            self.add_log("✅ Post successful!")
            return {"success": True}
        except Exception as e:
            self.add_log(f"❌ Post failed: {e}")
            return {"success": False, "error": str(e)}
    
    def engage(self):
        try:
            # Simple engagement - like a few tweets
            tweets = self.client.search_recent_tweets("DeFi", max_results=3)
            if tweets.data:
                for tweet in tweets.data[:2]:
                    self.client.like(tweet.id)
                self.engagements_today += len(tweets.data[:2])
                self.add_log(f"✅ Liked {len(tweets.data[:2])} tweets")
                return {"success": True, "engagements": len(tweets.data[:2])}
            return {"success": True, "engagements": 0}
        except Exception as e:
            self.add_log(f"❌ Engage failed: {e}")
            return {"success": False, "error": str(e)}
    
    def start_auto(self):
        if not hasattr(self, 'client') or not self.client:
            if not self.initialize_twitter():
                return False
        
        self.running = True
        self.add_log("🤖 Auto mode started")
        
        # Simple schedule in background thread
        def scheduler():
            while self.running:
                current_hour = datetime.now().hour
                # Post at 9, 14, 19 (24h format)
                if current_hour in [9, 14, 19] and datetime.now().minute == 0:
                    self.post_content()
                time.sleep(60)
        
        self.thread = threading.Thread(target=scheduler)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def stop_auto(self):
        self.running = False
        self.add_log("⏹️ Auto mode stopped")
    
    def get_stats(self):
        return {
            'status': 'running' if self.running else 'stopped',
            'last_post': self.last_post,
            'posts_today': self.posts_today,
            'engagements_today': self.engagements_today,
            'logs': self.logs[-10:]  # Last 10 logs
        }

# Global bot instance
bot = SimpleBot()

@app.route('/')
def home():
    return render_template('index_simple.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    if bot.start_auto():
        return jsonify({'success': True, 'message': 'Bot started'})
    return jsonify({'success': False, 'message': 'Failed to start'})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    bot.stop_auto()
    return jsonify({'success': True, 'message': 'Bot stopped'})

@app.route('/api/post', methods=['POST'])
def manual_post():
    result = bot.post_content()
    return jsonify(result)

@app.route('/api/engage', methods=['POST'])
def manual_engage():
    result = bot.engage()
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(bot.get_stats())

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "Bot is running"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)