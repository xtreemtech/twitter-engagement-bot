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
import base64

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
        
        # Image management
        self.uploaded_images = self.load_uploaded_images()
        self.used_images = []
        
        self.keywords = ["DeFi", "yield farming", "APY", "crypto earnings", "Pendle", "AAVE", "Lido", "smart contracts"]

    def load_uploaded_images(self):
        """Load uploaded images from a storage file"""
        try:
            with open('uploaded_images.txt', 'r', encoding='utf-8') as f:
                images = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                self.add_log(f"🖼️ Loaded {len(images)} uploaded images")
                return images
        except FileNotFoundError:
            self.add_log("📝 No uploaded images found - using default campaign images")
            return self.get_default_campaign_images()

    def get_default_campaign_images(self):
        """Default campaign images if none uploaded"""
        return [
            "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&h=400&fit=crop",
            "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=800&h=400&fit=crop",
        ]

    def save_uploaded_images(self):
        """Save uploaded images to file"""
        try:
            with open('uploaded_images.txt', 'w', encoding='utf-8') as f:
                for image_url in self.uploaded_images:
                    f.write(image_url + '\n')
            self.add_log("💾 Uploaded images saved to file")
        except Exception as e:
            self.add_log(f"❌ Failed to save images: {e}")

    def add_uploaded_image(self, image_url):
        """Add a new uploaded image"""
        if image_url not in self.uploaded_images:
            self.uploaded_images.append(image_url)
            self.save_uploaded_images()
            self.add_log(f"✅ New image added to campaign: {image_url}")
            return True
        return False

    def get_next_image(self):
        """Get the next image to use (round-robin)"""
        if not self.uploaded_images:
            return None
        
        # If we've used all images, reset
        if not self.used_images or len(self.used_images) >= len(self.uploaded_images):
            self.used_images = []
        
        # Find next unused image
        available_images = [img for img in self.uploaded_images if img not in self.used_images]
        if not available_images:
            # All images used, start over
            self.used_images = []
            available_images = self.uploaded_images
        
        next_image = available_images[0]
        self.used_images.append(next_image)
        return next_image

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
            image_used = None
            
            if use_image and self.uploaded_images:
                image_used = self.get_next_image()
                self.add_log(f"🖼️ Using campaign image: {image_used}")
                image_file = self.download_image(image_used)
                if image_file:
                    try:
                        # Upload media to Twitter
                        media = self.client.media_upload(filename="campaign_image.jpg", file=image_file)
                        media_ids.append(media.media_id)
                        self.add_log("✅ Campaign image uploaded successfully")
                    except Exception as e:
                        self.add_log(f"❌ Image upload failed: {e}")
                        image_used = None
            
            # Create tweet with or without media
            if media_ids:
                response = self.client.create_tweet(text=content, media_ids=media_ids)
            else:
                response = self.client.create_tweet(text=content)
            
            self.last_post_time = datetime.now().strftime('%H:%M:%S')
            self.posts_today += 1
            
            log_message = "✅ Post created successfully"
            if image_used:
                log_message += f" with campaign image"
            self.add_log(log_message)
            
            return {
                "success": True, 
                "content": content, 
                "with_image": bool(media_ids),
                "image_url": image_used,
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
        
        # Content posting (3x daily - always with campaign images when available)
        schedule.every().day.at("09:00").do(lambda: self.post_content(use_image=True))
        schedule.every().day.at("14:00").do(lambda: self.post_content(use_image=True))
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
            'image_pool_size': len(self.uploaded_images),
            'logs': self.logs[-10:]  # Last 10 logs
        }

    def upload_image_url(self, image_url):
        """Add a new image URL to the campaign"""
        success = self.add_uploaded_image(image_url)
        return {
            'success': success,
            'message': 'Image added to campaign' if success else 'Image already exists',
            'total_images': len(self.uploaded_images)
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
    result = bot.post_content(use_image=True)  # Always use images for manual posts
    return jsonify(result)

@app.route('/api/engage', methods=['POST'])
def manual_engage():
    result = bot.engage_with_community()
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(bot.get_stats())

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    data = request.get_json()
    image_url = data.get('image_url', '').strip()
    
    if not image_url:
        return jsonify({'success': False, 'error': 'No image URL provided'})
    
    # Validate URL format
    if not image_url.startswith(('http://', 'https://')):
        return jsonify({'success': False, 'error': 'Invalid URL format'})
    
    result = bot.upload_image_url(image_url)
    return jsonify(result)

@app.route('/api/campaign-images', methods=['GET'])
def get_campaign_images():
    return jsonify({
        'success': True,
        'images': bot.uploaded_images,
        'total': len(bot.uploaded_images)
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "Campaign bot with image management running"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)