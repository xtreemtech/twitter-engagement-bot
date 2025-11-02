import os
import time
import random
from datetime import datetime
import tweepy
from dotenv import load_dotenv

load_dotenv()

class LevvaBotNoAI:
    def __init__(self, twitter_client):
        self.client = twitter_client
        self.utm_link = os.getenv('LEVVA_UTM_LINK', 'https://levva.fi?utm_source=plortal&utm_medium=twitter&utm_campaign=engagement')
        
        # Statistics
        self.last_post_time = "Never"
        self.posts_today = 0
        self.engagements_today = 0
        
        # Load content pool
        self.content_templates = self.load_content_pool()
        self.used_content = []
        
        # Engagement keywords
        self.keywords = [
            "DeFi", "yield farming", "APY", "crypto earnings", "Pendle", "AAVE", 
            "Lido", "Morpho", "Curve", "Uniswap", "Ethereum staking", 
            "passive income crypto", "smart vaults", "AI DeFi"
        ]

    def load_content_pool(self):
        """Load content from file or use defaults"""
        try:
            with open('content_pool.txt', 'r', encoding='utf-8') as f:
                content = [line.strip().replace('{utm}', self.utm_link) 
                          for line in f if line.strip() and not line.startswith('#')]
                print(f"📁 Loaded {len(content)} content pieces from file")
                return content
        except FileNotFoundError:
            print("📝 Using default content pool")
            return self.get_default_content()

    def get_default_content(self):
        """Default content if file doesn't exist"""
        return [
            f"🤖 Tell AI: 'I want safe yield.'\n\nLevva's Smart Vaults make DeFi effortless! 5-25% APY 🚀\n\n{self.utm_link}",
            f"📊 Just deposited into Levva's AI vaults! No more DeFi complexity - just automated earnings\n\nWhat's your favorite feature? 👇\n\n{self.utm_link}",
            f"🛡️ Tired of managing 10+ DeFi dashboards?\n\nLevva handles: Pendle, AAVE, Lido, Morpho, Curve + more!\n\nAll in one vault 🔥\n\n{self.utm_link}",
            f"💡 DeFi made simple:\n• Deposit once\n• AI handles the rest\n• Earn 5-25% APY\n• Non-custodial & audited\n\nZero complexity, real yield 👇\n{self.utm_link}",
            f"🎯 Replaced my DeFi spreadsheet mess with @levvafi\n\nSmart Vaults automate:\n• Allocations\n• Rebalancing  \n• Yield optimization\n\nGame changer! {self.utm_link}",
            f"🚀 Leveling up my DeFi game with @levvafi AI vaults!\n\nAutomated yield, zero stress.\n\nWhat's not to love? {self.utm_link}",
            f"📈 Watching my yield grow automatically with Levva!\n\nSet it and forget it strategy working perfectly 🎯\n\n{self.utm_link}",
            f"⚡ Just optimized my portfolio with Levva's AI!\n\nNo more manual rebalancing - the bot handles everything\n\n{self.utm_link}",
            f"🔄 Auto-rebalancing working perfectly!\n\nLevva's AI just adjusted my positions across multiple protocols\n\nZero effort required 👏\n\n{self.utm_link}",
            f"🎊 Celebrating consistent returns with @levvafi!\n\nPassive income should be this easy\n\n{self.utm_link}"
        ]

    def get_fresh_content(self):
        """Get content that hasn't been used recently"""
        available = [c for c in self.content_templates if c not in self.used_content]
        
        if not available:
            # Reset if we've used everything
            self.used_content = []
            available = self.content_templates
        
        content = random.choice(available)
        self.used_content.append(content)
        
        # Keep only last 15 used to manage memory
        if len(self.used_content) > 15:
            self.used_content = self.used_content[-15:]
            
        return content

    def post_content(self):
        """Post content from rotation"""
        try:
            content = self.get_fresh_content()
            response = self.client.create_tweet(text=content)
            
            # Update statistics
            self.last_post_time = datetime.now().strftime('%H:%M:%S')
            self.posts_today += 1
            
            print(f"✅ Posted: {content[:80]}...")
            return {"success": True, "content": content}
            
        except Exception as e:
            print(f"❌ Post failed: {e}")
            return {"success": False, "error": str(e)}

    def engage_with_community(self):
        """Engage with relevant tweets"""
        try:
            keyword = random.choice(self.keywords)
            print(f"🔍 Engaging with tweets about: {keyword}")
            
            tweets = self.client.search_recent_tweets(
                f"{keyword} -is:retweet -from:levvafi",
                max_results=8,
                tweet_fields=['public_metrics']
            )
            
            engagements = 0
            if tweets.data:
                for tweet in tweets.data[:3]:  # Limit to 3 engagements
                    # Only engage with tweets that have some activity
                    if tweet.public_metrics['like_count'] >= 1:
                        try:
                            self.client.like(tweet.id)
                            engagements += 1
                            self.engagements_today += 1
                            print(f"   👍 Liked tweet about {keyword}")
                            time.sleep(random.randint(30, 60))  # Be human-like
                        except Exception as e:
                            print(f"   ❌ Failed to like tweet: {e}")
                
            return {"success": True, "engagements": engagements}
            
        except Exception as e:
            print(f"❌ Engagement failed: {e}")
            return {"success": False, "error": str(e)}

    def get_stats(self):
        """Get current bot statistics"""
        return {
            'last_post': self.last_post_time,
            'posts_today': self.posts_today,
            'engagements_today': self.engagements_today,
            'content_pool_size': len(self.content_templates)
        }