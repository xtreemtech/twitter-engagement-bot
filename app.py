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
from flask import Flask, render_template, request, jsonify
import threading
import time
import schedule
from datetime import datetime
import tweepy
from dotenv import load_dotenv
import os
import random
import requests
from io import BytesIO

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
        self.content_templates = self.load_content_pool()
        self.used_content = []
        self.utm_link = os.getenv('LEVVA_UTM_LINK', 'https://levva.fi?utm_source=plortal&utm_medium=twitter&utm_campaign=engagement')
        
        # Image URLs for tweets
        self.images = [
            "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&h=400&fit=crop",  # Crypto concept
            "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=800&h=400&fit=crop",  # Blockchain
            "https://images.unsplash.com/photo-1621761191311-89dc49c05cff?w=800&h=400&fit=crop",  # Finance
            "https://images.unsplash.com/photo-1620321023374-d1a68fbc720d?w=800&h=400&fit=crop",  # Technology
            "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=400&fit=crop",  # Data visualization
        ]
        
        self.keywords = ["DeFi", "yield farming", "APY", "crypto earnings", "Pendle", "AAVE", "Lido", "smart contracts"]

    def load_content_pool(self):
        """Load content from file or use defaults"""
        try:
            with open('content_pool.txt', 'r', encoding='utf-8') as f:
                content = [line.strip().replace('{utm}', self.utm_link) 
                          for line in f if line.strip() and not line.startswith('#')]
                self.add_log(f"📁 Loaded {len(content)} content pieces from file")
                return content
        except FileNotFoundError:
            self.add_log("📝 Using default content pool")
            return self.get_default_content()

    def get_default_content(self):
        """Default content if file doesn't exist"""
        return [
            f"🤖 Tell AI: 'I want safe yield.' Levva's Smart Vaults make DeFi effortless! 5-25% APY 🚀 {self.utm_link}",
            f"📊 Just deposited into Levva's AI vaults! No more DeFi complexity - just automated earnings {self.utm_link}",
        ]

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

    def download_image(self, url):
        """Download and prepare image for Twitter"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return BytesIO(response.content)
        except Exception as e:
            self.add_log(f"❌ Image download failed: {e}")
            return None

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
            
        return content

    def post_content(self, use_image=False):
        """Post content to Twitter with optional image"""
        if not self.client:
            if not self.initialize_twitter():
                return {"success": False, "error": "Twitter not connected"}
        
        try:
            content = self.get_fresh_content()
            media_ids = []
            
            # 30% chance to include image if requested
            if use_image and random.random() < 0.3:
                image_url = random.choice(self.images)
                self.add_log(f"🖼️ Attempting to download image: {image_url}")
                image_file = self.download_image(image_url)
                if image_file:
                    try:
                        # Upload media to Twitter
                        media = self.client.media_upload(filename="levva_image.jpg", file=image_file)
                        media_ids.append(media.media_id)
                        self.add_log("✅ Image uploaded successfully")
                    except Exception as e:
                        self.add_log(f"❌ Image upload failed: {e}")
            
            # Create tweet with or without media
            if media_ids:
                response = self.client.create_tweet(text=content, media_ids=media_ids)
            else:
                response = self.client.create_tweet(text=content)
            
            self.last_post_time = datetime.now().strftime('%H:%M:%S')
            self.posts_today += 1
            
            log_message = "✅ Post created successfully"
            if media_ids:
                log_message += " with image"
            self.add_log(log_message)
            
            return {
                "success": True, 
                "content": content, 
                "with_image": bool(media_ids),
                "message": log_message
            }
            
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
                        try:
                            self.client.like(tweet.id)
                            engagements += 1
                            self.engagements_today += 1
                            self.add_log(f"   👍 Liked tweet about {keyword}")
                            time.sleep(random.randint(20, 40))  # Be human-like
                        except Exception as e:
                            self.add_log(f"   ❌ Failed to like tweet: {e}")
                
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
        
        # Content posting (3x daily - sometimes with images)
        schedule.every().day.at("09:00").do(lambda: self.post_content(use_image=True))
        schedule.every().day.at("14:00").do(lambda: self.post_content(use_image=False))
        schedule.every().day.at("19:00").do(lambda: self.post_content(use_image=True))
        
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
            'content_pool_size': len(self.content_templates),
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
    result = bot.post_content(use_image=False)
    return jsonify(result)

@app.route('/api/post-with-image', methods=['POST'])
def manual_post_with_image():
    result = bot.post_content(use_image=True)
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
    return jsonify({"status": "healthy", "message": "Full functional bot with image support running"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "Full functional bot running"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)