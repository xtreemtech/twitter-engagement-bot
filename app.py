from flask import Flask, render_template, request, jsonify
import threading
import time
import schedule
from datetime import datetime
import tweepy
from dotenv import load_dotenv
import os
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

class FullFunctionalBot:
    def __init__(self):
        self.client = None
        self.running = False
        self.logs = []
        self.last_post_time = "Never"
        self.posts_today = 0
        self.engagements_today = 0
        self.thread = None
        
        # Content pool
        self.content_templates = [
            "🤖 Tell AI: 'I want safe yield.' Levva's Smart Vaults make DeFi effortless! 5-25% APY 🚀 {utm}",
            "📊 Just deposited into Levva's AI vaults! No more DeFi complexity - just automated earnings {utm}",
            "🛡️ Tired of managing 10+ DeFi dashboards? Levva handles everything! {utm}",
            "💡 DeFi made simple: Deposit once → AI handles the rest → Earn yield {utm}",
            "🎯 Replaced my DeFi spreadsheet mess with @levvafi Smart Vaults. Game changer! {utm}"
        ]
        self.used_content = []
        self.utm_link = os.getenv('LEVVA_UTM_LINK', 'https://levva.fi?utm_source=plortal&utm_medium=twitter&utm_campaign=engagement')
        
        self.keywords = ["DeFi", "yield farming", "APY", "crypto earnings", "Pendle", "AAVE"]

    def initialize_twitter(self):
        """Initialize Twitter client"""
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
            self.add_log(f"❌ Twitter connection failed: {e}")
            return False

    def add_log(self, message):
        """Add log message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        # Keep only last 20 logs
        if len(self.logs) > 20:
            self.logs = self.logs[-20:]
        print(log_entry)

    def get_fresh_content(self):
        """Get content that hasn't been used recently"""
        available = [c for c in self.content_templates if c not in self.used_content]
        
        if not available:
            # Reset if we've used everything
            self.used_content = []
            available = self.content_templates
        
        content = random.choice(available)
        self.used_content.append(content)
        
        # Keep only last 10 used
        if len(self.used_content) > 10:
            self.used_content = self.used_content[-10:]
            
        return content.replace('{utm}', self.utm_link)

    def post_content(self):
        """Post content to Twitter"""
        if not self.client:
            if not self.initialize_twitter():
                return {"success": False, "error": "Twitter not connected"}
        
        try:
            content = self.get_fresh_content()
            response = self.client.create_tweet(text=content)
            self.last_post_time = datetime.now().strftime('%H:%M:%S')
            self.posts_today += 1
            self.add_log("✅ Post created successfully")
            return {"success": True, "content": content}
        except Exception as e:
            self.add_log(f"❌ Post failed: {e}")
            return {"success": False, "error": str(e)}

    def engage_with_community(self):
        """Engage with relevant tweets"""
        if not self.client:
            if not self.initialize_twitter():
                return {"success": False, "error": "Twitter not connected"}
        
        try:
            keyword = random.choice(self.keywords)
            self.add_log(f"🔍 Engaging with tweets about: {keyword}")
            
            tweets = self.client.search_recent_tweets(
                f"{keyword} -is:retweet -from:levvafi",
                max_results=5,
                tweet_fields=['public_metrics']
            )
            
            engagements = 0
            if tweets.data:
                for tweet in tweets.data[:2]:  # Limit to 2 engagements
                    if tweet.public_metrics['like_count'] >= 1:
                        self.client.like(tweet.id)
                        engagements += 1
                        self.engagements_today += 1
                        self.add_log(f"   👍 Liked tweet about {keyword}")
                        time.sleep(30)  # Be human-like
                
            self.add_log(f"💬 Engagement complete: {engagements} interactions")
            return {"success": True, "engagements": engagements}
            
        except Exception as e:
            self.add_log(f"❌ Engagement failed: {e}")
            return {"success": False, "error": str(e)}

    def start_auto_mode(self):
        """Start automated posting and engagement"""
        if not self.client:
            if not self.initialize_twitter():
                return False
        
        self.running = True
        self.setup_schedule()
        self.add_log("🚀 AUTO MODE STARTED - Bot will post and engage automatically")
        
        # Start schedule in background thread
        def scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        
        self.thread = threading.Thread(target=scheduler)
        self.thread.daemon = True
        self.thread.start()
        return True

    def setup_schedule(self):
        """Setup automated schedule"""
        schedule.clear()
        
        # Content posting (3x daily)
        schedule.every().day.at("09:00").do(lambda: self.post_content())
        schedule.every().day.at("14:00").do(lambda: self.post_content())
        schedule.every().day.at("19:00").do(lambda: self.post_content())
        
        # Community engagement (3x daily)
        schedule.every().day.at("10:30").do(lambda: self.engage_with_community())
        schedule.every().day.at("16:00").do(lambda: self.engage_with_community())
        schedule.every().day.at("21:00").do(lambda: self.engage_with_community())
        
        self.add_log("📅 Schedule: Posts at 9:00, 14:00, 19:00 | Engagement at 10:30, 16:00, 21:00")

    def stop_auto_mode(self):
        """Stop automated mode"""
        self.running = False
        schedule.clear()
        self.add_log("⏹️ AUTO MODE STOPPED")

    def get_stats(self):
        """Get bot statistics"""
        return {
            'status': 'running' if self.running else 'stopped',
            'last_post': self.last_post_time,
            'posts_today': self.posts_today,
            'engagements_today': self.engagements_today,
            'logs': self.logs[-10:]  # Last 10 logs
        }

# Global bot instance
bot = FullFunctionalBot()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    if bot.start_auto_mode():
        return jsonify({'success': True, 'message': 'Auto mode started'})
    return jsonify({'success': False, 'message': 'Failed to start'})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    bot.stop_auto_mode()
    return jsonify({'success': True, 'message': 'Auto mode stopped'})

@app.route('/api/post', methods=['POST'])
def manual_post():
    result = bot.post_content()
    return jsonify(result)

@app.route('/api/engage', methods=['POST'])
def manual_engage():
    result = bot.engage_with_community()
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(bot.get_stats())

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "Full functional bot running"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)