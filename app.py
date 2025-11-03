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
        self.api = None  # v1.1 API
        self.client = None  # v2 API (for some operations)
        self.running = False
        self.logs = []
        self.last_post_time = "Never"
        self.posts_today = 0
        self.engagements_today = 0
        self.thread = None
        
        # Rate limiting
        self.last_engagement_time = None
        self.engagement_count_15min = 0
        
        # Content pool
        self.content_templates = self.load_content_pool()
        self.used_content = []
        self.utm_link = os.getenv('LEVVA_UTM_LINK', 'https://levva.fi?utm_source=plortal&utm_medium=twitter&utm_campaign=engagement')
        
        # Image management
        self.uploaded_images = self.load_uploaded_images()
        self.used_images = []
        
        # Engagement keywords
        self.keywords = [
            "DeFi", "yield farming", "APY", "crypto", 
            "Ethereum", "staking", "passive income"
        ]

    def initialize_twitter(self):
        """Initialize Twitter API v1.1 (more stable for engagement)"""
        try:
            # API v1.1 for engagement (more stable)
            auth = tweepy.OAuth1UserHandler(
                os.getenv('TWITTER_API_KEY'),
                os.getenv('TWITTER_API_SECRET'),
                os.getenv('TWITTER_ACCESS_TOKEN'),
                os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Verify credentials
            user = self.api.verify_credentials()
            self.add_log(f"✅ Twitter v1.1 connected: @{user.screen_name}")
            
            # Also initialize v2 client for posting if needed
            self.client = tweepy.Client(
                bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
                consumer_key=os.getenv('TWITTER_API_KEY'),
                consumer_secret=os.getenv('TWITTER_API_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            
            return True
        except Exception as e:
            self.add_log(f"❌ Twitter connection failed: {e}")
            return False

    def engage_with_community(self):
        """Engage with relevant tweets using API v1.1"""
        if not self.api:
            if not self.initialize_twitter():
                return {"success": False, "error": "Twitter not connected"}
        
        # Check rate limits
        can_engage, reason = self.check_rate_limits()
        if not can_engage:
            return {"success": False, "error": reason}
        
        try:
            keyword = random.choice(self.keywords)
            self.add_log(f"🔍 Searching for tweets about: {keyword}")
            
            # Use API v1.1 for search (more reliable)
            tweets = self.api.search_tweets(
                q=keyword,
                count=10,  # Get 10 tweets
                lang="en",  # English only
                result_type="recent"  # Recent tweets
            )
            
            engagements = 0
            if tweets:
                # Filter for quality tweets
                quality_tweets = []
                for tweet in tweets:
                    # Skip retweets and replies
                    if not hasattr(tweet, 'retweeted_status') and not tweet.in_reply_to_status_id:
                        # Only engage with tweets that have some likes
                        if tweet.favorite_count >= 1:
                            quality_tweets.append(tweet)
                
                self.add_log(f"   Found {len(quality_tweets)} quality tweets")
                
                # Engage with up to 2 quality tweets
                for tweet in quality_tweets[:2]:
                    try:
                        # Check rate limit again
                        can_engage, reason = self.check_rate_limits()
                        if not can_engage:
                            self.add_log(f"   ⚠️ Rate limit reached during engagement")
                            break
                            
                        # Like the tweet using v1.1 API
                        self.api.create_favorite(tweet.id)
                        engagements += 1
                        self.engagements_today += 1
                        self.engagement_count_15min += 1
                        self.last_engagement_time = datetime.now()
                        
                        self.add_log(f"   👍 Liked tweet by @{tweet.user.screen_name}")
                        
                        # Random delay between engagements
                        delay = random.randint(60, 120)  # Longer delays
                        time.sleep(delay)
                        
                    except tweepy.TweepyException as e:
                        self.add_log(f"   ❌ Failed to like tweet: {e}")
                        continue
                
            result_msg = f"💬 Engagement complete: {engagements} interactions"
            self.add_log(result_msg)
            return {"success": True, "engagements": engagements, "message": result_msg}
            
        except Exception as e:
            error_msg = f"Engagement failed: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def post_content(self, use_image=True):
        """Post content using the most reliable method"""
        if not self.client and not self.api:
            if not self.initialize_twitter():
                return {"success": False, "error": "Twitter not connected"}
        
        # Check rate limits
        can_post, reason = self.check_rate_limits()
        if not can_post:
            return {"success": False, "error": reason}
        
        try:
            content = self.get_fresh_content()
            
            # Try v2 API first for posting
            if self.client:
                try:
                    if use_image and self.uploaded_images:
                        image_used = self.get_next_image()
                        image_file = self.download_image(image_used)
                        if image_file:
                            media = self.client.media_upload(filename="campaign.jpg", file=image_file)
                            response = self.client.create_tweet(text=content, media_ids=[media.media_id])
                            self.add_log("✅ Post with image published via v2 API")
                        else:
                            response = self.client.create_tweet(text=content)
                            self.add_log("✅ Text post published via v2 API")
                    else:
                        response = self.client.create_tweet(text=content)
                        self.add_log("✅ Text post published via v2 API")
                except Exception as e:
                    self.add_log(f"⚠️ v2 API failed, trying v1.1: {e}")
                    # Fall back to v1.1
                    if self.api:
                        if use_image and self.uploaded_images:
                            image_used = self.get_next_image()
                            image_file = self.download_image(image_used)
                            if image_file:
                                media = self.api.media_upload(filename="campaign.jpg", file=image_file)
                                response = self.api.update_status(status=content, media_ids=[media.media_id])
                            else:
                                response = self.api.update_status(status=content)
                        else:
                            response = self.api.update_status(status=content)
                        self.add_log("✅ Post published via v1.1 API")
                    else:
                        raise e
            else:
                # Use v1.1 only
                response = self.api.update_status(status=content)
                self.add_log("✅ Post published via v1.1 API")
            
            # Update statistics
            self.last_post_time = datetime.now().strftime('%H:%M:%S')
            self.posts_today += 1
            
            return {
                "success": True, 
                "content": content,
                "with_image": use_image and self.uploaded_images,
                "message": "Post published successfully"
            }
            
        except Exception as e:
            error_msg = str(e)
            self.add_log(f"❌ Post failed: {error_msg}")
            return {"success": False, "error": error_msg}

    def check_rate_limits(self):
        """Check rate limits"""
        now = datetime.now()
        
        # Reset engagement count every 15 minutes
        if self.last_engagement_time and (now - self.last_engagement_time) > timedelta(minutes=15):
            self.engagement_count_15min = 0
            self.last_engagement_time = now
        
        # Conservative limits
        if self.engagement_count_15min >= 20:
            return False, "Rate limit: Too many engagements (20/15min)"
            
        return True, "OK"

    # ... (keep all your other methods the same - load_content_pool, download_image, etc.)

# Global bot instance
bot = LevvaCampaignBot()

# ... (keep all your routes the same)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)