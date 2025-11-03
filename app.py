from flask import Flask, render_template, request, jsonify
import threading
import time
import schedule
from datetime import datetime, timedelta
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

class LevvaCampaignBot:
    def __init__(self):
        self.client = None
        self.running = False
        self.logs = []
        self.last_post_time = "Never"
        self.posts_today = 0
        self.engagements_today = 0
        self.thread = None
        
        # Rate limiting
        self.last_engagement_time = None
        self.engagement_count_15min = 0
        self.last_post_time_obj = None
        
        # Content pool
        self.content_templates = self.load_content_pool()
        self.used_content = []
        self.utm_link = os.getenv('LEVVA_UTM_LINK', 'https://levva.fi?utm_source=plortal&utm_medium=twitter&utm_campaign=engagement')
        
        # Image management
        self.uploaded_images = self.load_uploaded_images()
        self.used_images = []
        
        # Engagement keywords (broader for better results)
        self.keywords = [
            "DeFi", "yield farming", "APY", "crypto", 
            "Ethereum", "staking", "passive income", "investing",
            "web3", "blockchain", "digital assets"
        ]

    def load_uploaded_images(self):
        """Load uploaded images from storage file"""
        try:
            with open('uploaded_images.txt', 'r', encoding='utf-8') as f:
                images = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                self.add_log(f"🖼️ Loaded {len(images)} campaign images")
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
            self.add_log("💾 Campaign images saved")
        except Exception as e:
            self.add_log(f"❌ Failed to save images: {e}")

    def add_uploaded_image(self, image_url):
        """Add a new uploaded image to campaign"""
        if image_url not in self.uploaded_images:
            self.uploaded_images.append(image_url)
            self.save_uploaded_images()
            self.add_log(f"✅ New campaign image added")
            return True
        return False

    def get_next_image(self):
        """Get the next image to use (round-robin rotation)"""
        if not self.uploaded_images:
            return None
        
        # Reset if we've used all images
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
                self.add_log(f"📁 Loaded {len(content)} content variations")
                return content
        except FileNotFoundError:
            self.add_log("📝 Using default content pool")
            return self.get_default_content()

    def get_default_content(self):
        """Default content if file doesn't exist"""
        return [
            f"🤖 Tell AI: 'I want safe yield.' Levva's Smart Vaults make DeFi effortless! 5-25% APY 🚀 {self.utm_link}",
            f"📊 Just deposited into Levva's AI vaults! No more DeFi complexity - just automated earnings {self.utm_link}",
            f"🛡️ Tired of managing 10+ DeFi dashboards? Levva handles everything automatically! {self.utm_link}",
        ]

    def check_rate_limits(self):
        """Check if we're hitting rate limits"""
        now = datetime.now()
        
        # Reset engagement count every 15 minutes
        if self.last_engagement_time and (now - self.last_engagement_time) > timedelta(minutes=15):
            self.engagement_count_15min = 0
            self.last_engagement_time = now
        
        # Twitter rate limits (conservative estimates)
        if self.engagement_count_15min >= 25:  # 25 likes per 15 min window
            return False, "Rate limit: Too many engagements in 15 minutes"
            
        # Post rate limiting (1 per 2 minutes minimum)
        if self.last_post_time_obj and (now - self.last_post_time_obj) < timedelta(minutes=2):
            return False, "Rate limit: Posts too frequent"
            
        return True, "OK"

    def initialize_twitter(self):
        """Initialize Twitter client with error handling"""
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
                consumer_key=os.getenv('TWITTER_API_KEY'),
                consumer_secret=os.getenv('TWITTER_API_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            
            # Test connection with a simple call
            user = self.client.get_me()
            self.add_log(f"✅ Twitter connected: @{user.data.username}")
            return True
        except Exception as e:
            self.add_log(f"❌ Twitter connection failed: {e}")
            return False

    def download_image(self, url):
        """Download and prepare image for Twitter"""
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            # Check file size (Twitter limit is 5MB for images)
            if int(response.headers.get('content-length', 0)) > 5 * 1024 * 1024:
                self.add_log("❌ Image too large (max 5MB)")
                return None
                
            return BytesIO(response.content)
        except Exception as e:
            self.add_log(f"❌ Image download failed: {e}")
            return None

    def add_log(self, message):
        """Add log message with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        # Keep only last 25 logs
        if len(self.logs) > 25:
            self.logs = self.logs[-25:]
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
        
        # Keep only last 15 used to prevent memory issues
        if len(self.used_content) > 15:
            self.used_content = self.used_content[-15:]
            
        return content

    def post_content(self, use_image=True):
        """Post content to Twitter with campaign image"""
        if not self.client:
            if not self.initialize_twitter():
                return {"success": False, "error": "Twitter not connected"}
        
        # Check rate limits
        can_post, reason = self.check_rate_limits()
        if not can_post:
            return {"success": False, "error": reason}
        
        try:
            content = self.get_fresh_content()
            media_ids = []
            image_used = None
            
            # Always try to use images if available and requested
            if use_image and self.uploaded_images:
                image_used = self.get_next_image()
                self.add_log(f"🖼️ Using campaign image")
                image_file = self.download_image(image_used)
                if image_file:
                    try:
                        # Upload media to Twitter
                        media = self.client.media_upload(
                            filename="levva_campaign.jpg", 
                            file=image_file
                        )
                        media_ids.append(media.media_id)
                        self.add_log("✅ Image uploaded to Twitter")
                    except Exception as e:
                        self.add_log(f"❌ Image upload failed: {e}")
                        image_used = None
                else:
                    self.add_log("⚠️ Could not download image, posting text only")
            
            # Create tweet with or without media
            if media_ids:
                response = self.client.create_tweet(text=content, media_ids=media_ids)
            else:
                response = self.client.create_tweet(text=content)
            
            # Update statistics and rate limiting
            self.last_post_time = datetime.now().strftime('%H:%M:%S')
            self.last_post_time_obj = datetime.now()
            self.posts_today += 1
            
            log_message = "✅ Post published successfully"
            if image_used:
                log_message += " with campaign image"
            self.add_log(log_message)
            
            return {
                "success": True, 
                "content": content, 
                "with_image": bool(media_ids),
                "image_url": image_used,
                "message": log_message
            }
            
        except Exception as e:
            error_msg = str(e)
            self.add_log(f"❌ Post failed: {error_msg}")
            return {"success": False, "error": error_msg}

    def engage_with_community(self):
        """Engage with relevant tweets with rate limit protection"""
        if not self.client:
            if not self.initialize_twitter():
                return {"success": False, "error": "Twitter not connected"}
        
        # Check rate limits before engaging
        can_engage, reason = self.check_rate_limits()
        if not can_engage:
            return {"success": False, "error": reason}
        
        try:
            keyword = random.choice(self.keywords)
            self.add_log(f"🔍 Searching for tweets about: {keyword}")
            
            # Use broader search terms to get more results
            tweets = self.client.search_recent_tweets(
                query=f"{keyword} -is:retweet -is:reply lang:en",  # English tweets only
                max_results=15,  # Get more to filter from
                tweet_fields=['public_metrics', 'author_id']
            )
            
            engagements = 0
            if tweets.data:
                # Filter for quality tweets (some engagement, not spam)
                quality_tweets = []
                for tweet in tweets.data:
                    metrics = tweet.public_metrics
                    # Only engage with tweets that have some organic activity
                    # But not TOO popular (avoid massive accounts)
                    if (2 <= metrics['like_count'] <= 50 and 
                        metrics['reply_count'] >= 0):
                        quality_tweets.append(tweet)
                
                self.add_log(f"   Found {len(quality_tweets)} quality tweets")
                
                # Engage with up to 2 quality tweets (conservative)
                for tweet in quality_tweets[:2]:
                    try:
                        # Check rate limit again before each engagement
                        can_engage, reason = self.check_rate_limits()
                        if not can_engage:
                            self.add_log(f"   ⚠️ Rate limit reached during engagement")
                            break
                            
                        self.client.like(tweet.id)
                        engagements += 1
                        self.engagements_today += 1
                        self.engagement_count_15min += 1
                        self.last_engagement_time = datetime.now()
                        
                        self.add_log(f"   👍 Liked quality tweet (likes: {tweet.public_metrics['like_count']})")
                        
                        # Random delay between engagements (be human-like)
                        delay = random.randint(45, 90)  # Longer delays to avoid rate limits
                        time.sleep(delay)
                        
                    except tweepy.TooManyRequests as e:
                        self.add_log(f"   🚨 Twitter rate limit hit: {e}")
                        return {"success": False, "error": "Twitter rate limit exceeded - try again later"}
                    except Exception as e:
                        self.add_log(f"   ❌ Failed to like tweet: {e}")
                        # Continue with next tweet instead of breaking
                        continue
                
            result_msg = f"💬 Engagement complete: {engagements} interactions"
            self.add_log(result_msg)
            return {"success": True, "engagements": engagements, "message": result_msg}
            
        except tweepy.TooManyRequests as e:
            error_msg = "Twitter API rate limit exceeded - please wait 15 minutes"
            self.add_log(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Engagement failed: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def start_auto_mode(self):
        """Start automated posting and engagement"""
        if not self.client:
            if not self.initialize_twitter():
                return False
        
        self.running = True
        self.setup_schedule()
        self.add_log("🚀 AUTOMATION STARTED - Campaign bot is now active")
        
        # Start schedule in background thread
        def scheduler():
            while self.running:
                try:
                    schedule.run_pending()
                except Exception as e:
                    self.add_log(f"❌ Scheduler error: {e}")
                time.sleep(60)  # Check every minute
        
        self.thread = threading.Thread(target=scheduler)
        self.thread.daemon = True
        self.thread.start()
        return True

    def setup_schedule(self):
        """Setup automated campaign schedule with conservative limits"""
        schedule.clear()
        
        # Content posting (3x daily - always with campaign images)
        schedule.every().day.at("09:00").do(lambda: self.scheduled_post())
        schedule.every().day.at("14:00").do(lambda: self.scheduled_post())
        schedule.every().day.at("19:00").do(lambda: self.scheduled_post())
        
        # Community engagement (2x daily - conservative to avoid limits)
        schedule.every().day.at("11:00").do(lambda: self.scheduled_engage())
        schedule.every().day.at("17:00").do(lambda: self.scheduled_engage())
        
        self.add_log("📅 Conservative schedule: Posts at 9:00, 14:00, 19:00 | Engagement at 11:00, 17:00")

    def scheduled_post(self):
        """Scheduled post with error handling"""
        if self.running:
            self.add_log("🕒 Scheduled post triggered")
            self.post_content(use_image=True)

    def scheduled_engage(self):
        """Scheduled engagement with error handling"""
        if self.running:
            self.add_log("🕒 Scheduled engagement triggered")
            self.engage_with_community()

    def stop_auto_mode(self):
        """Stop automated mode"""
        self.running = False
        schedule.clear()
        self.add_log("⏹️ AUTOMATION STOPPED - Campaign bot is now inactive")

    def get_stats(self):
        """Get comprehensive bot statistics"""
        return {
            'status': 'running' if self.running else 'stopped',
            'last_post': self.last_post_time,
            'posts_today': self.posts_today,
            'engagements_today': self.engagements_today,
            'engagement_count_15min': self.engagement_count_15min,
            'content_pool_size': len(self.content_templates),
            'image_pool_size': len(self.uploaded_images),
            'logs': self.logs[-15:]  # Last 15 logs
        }

    def upload_image_url(self, image_url):
        """Add a new image URL to the campaign"""
        # Validate URL
        if not image_url.startswith(('http://', 'https://')):
            return {
                'success': False, 
                'error': 'Invalid URL format. Must start with http:// or https://'
            }
        
        success = self.add_uploaded_image(image_url)
        return {
            'success': success,
            'message': 'Campaign image added successfully' if success else 'Image already in campaign',
            'total_images': len(self.uploaded_images)
        }

    def reset_rate_limits(self):
        """Reset rate limit counters (for testing)"""
        self.engagement_count_15min = 0
        self.last_engagement_time = None
        self.add_log("🔄 Rate limit counters reset")

# Global bot instance
bot = LevvaCampaignBot()

# API Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the automated campaign bot"""
    if bot.start_auto_mode():
        return jsonify({
            'success': True, 
            'message': 'Campaign automation started successfully'
        })
    return jsonify({
        'success': False, 
        'message': 'Failed to start automation - check Twitter configuration'
    })

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the automated campaign bot"""
    bot.stop_auto_mode()
    return jsonify({
        'success': True, 
        'message': 'Campaign automation stopped'
    })

@app.route('/api/post', methods=['POST'])
def manual_post():
    """Create a manual post with campaign image"""
    result = bot.post_content(use_image=True)
    return jsonify(result)

@app.route('/api/engage', methods=['POST'])
def manual_engage():
    """Manual community engagement"""
    result = bot.engage_with_community()
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get current bot statistics and logs"""
    return jsonify(bot.get_stats())

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """Upload a new campaign image"""
    data = request.get_json()
    image_url = data.get('image_url', '').strip()
    
    if not image_url:
        return jsonify({
            'success': False, 
            'error': 'No image URL provided'
        })
    
    result = bot.upload_image_url(image_url)
    return jsonify(result)

@app.route('/api/campaign-images', methods=['GET'])
def get_campaign_images():
    """Get all uploaded campaign images"""
    return jsonify({
        'success': True,
        'images': bot.uploaded_images,
        'total': len(bot.uploaded_images)
    })

@app.route('/api/reset-limits', methods=['POST'])
def reset_limits():
    """Reset rate limits (for testing)"""
    bot.reset_rate_limits()
    return jsonify({
        'success': True,
        'message': 'Rate limits reset successfully'
    })

@app.route('/health')
def health():
    """Health check endpoint for deployment"""
    return jsonify({
        "status": "healthy", 
        "message": "Levva Campaign Bot is running",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)