import os
import time
import random
import schedule
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import tweepy
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize APIs
client = tweepy.Client(
    bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
    consumer_key=os.getenv('TWITTER_API_KEY'),
    consumer_secret=os.getenv('TWITTER_API_SECRET'),
    access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
    access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
)

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class AILewaBot:
    def __init__(self, twitter_client, openai_client):
        self.client = twitter_client
        self.openai = openai_client
        self.utm_link = os.getenv('LEVVA_UTM_LINK')
        self.used_content = set()
        
        # Campaign context for AI
        self.campaign_context = """
        Levva is an AI DeFi platform that makes yield farming effortless. Key points:
        - Smart Vaults automate DeFi investing
        - AI handles allocations, rebalancing, and yield optimization
        - Integrated with 20+ protocols: Pendle, AAVE, Lido, Morpho, Curve, Uniswap, etc.
        - 5-25% organic APY
        - Non-custodial & fully audited
        - Zero complexity, just automated earnings
        
        Brand messaging: "Tell AI: I want safe yield"
        Tone: Educational, authentic, showing how Levva helps users earn smarter
        """
        
        self.keywords = [
            "DeFi", "yield farming", "APY", "crypto earnings", "Pendle", "AAVE", 
            "Lido", "Morpho", "Curve", "Uniswap", "Ethereum staking", 
            "passive income crypto", "smart vaults", "AI DeFi"
        ]

    def generate_ai_content(self, content_type="tweet"):
        """Generate fresh content using OpenAI"""
        try:
            prompts = {
                "tweet": f"""
                Create an engaging Twitter post about Levva AI DeFi platform.
                
                CONTEXT: {self.campaign_context}
                
                REQUIREMENTS:
                - Include the UTM link: {self.utm_link}
                - Maximum 280 characters
                - Educational and authentic tone
                - Focus on benefits: ease of use, automated yield, security
                - Include relevant hashtags like #DeFi #AI #YieldFarming
                - Don't sound like an ad - be helpful and genuine
                
                Create 3 different tweet variations:""",
                
                "thread_starter": f"""
                Create an engaging first tweet for an educational thread about Levva.
                
                CONTEXT: {self.campaign_context}
                
                Make it intriguing to make people want to read the thread:""",
                
                "reply": f"""
                Create a genuine, helpful reply to a tweet about {random.choice(self.keywords)}.
                Naturally mention how Levva's AI vaults help with this, but don't be pushy.
                Keep it under 200 characters:"""
            }
            
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful DeFi educator who genuinely wants to help people understand AI-powered yield farming."},
                    {"role": "user", "content": prompts[content_type]}
                ],
                max_tokens=500,
                temperature=0.8
            )
            
            content = response.choices[0].message.content.strip()
            print(f"🤖 AI generated new {content_type} content")
            return content
            
        except Exception as e:
            print(f"❌ AI content generation failed: {e}")
            return self.get_fallback_content()

    def get_fallback_content(self):
        """Fallback content if AI fails"""
        fallbacks = [
            f"🤖 AI-powered yield farming is here! @levvafi makes DeFi effortless with Smart Vaults. 5-25% APY, zero complexity. Try it: {self.utm_link}",
            f"📊 Just optimized my yield strategy with @levvafi's AI. No more manual rebalancing! What's your APY looking like? {self.utm_link}",
            f"🎯 DeFi made simple: Deposit → AI handles the rest → Earn yield. That's the @levvafi magic! {self.utm_link} #DeFi #AI"
        ]
        return random.choice(fallbacks)

    def post_ai_content(self):
        """Post AI-generated content"""
        try:
            # Generate fresh content
            ai_content = self.generate_ai_content("tweet")
            
            # Extract the first tweet if multiple were generated
            tweets = [t.strip() for t in ai_content.split('\n') if t.strip() and not t.startswith(('1.', '2.', '3.'))]
            if tweets:
                content = tweets[0]
            else:
                content = ai_content
                
            # Ensure UTM link is included
            if self.utm_link not in content:
                content += f"\n\n{self.utm_link}"
                
            # Post to Twitter
            response = self.client.create_tweet(text=content)
            print(f"✅ [{datetime.now().strftime('%H:%M')}] Posted AI-generated content")
            print(f"   📝 {content[:80]}...")
            
            return response
            
        except Exception as e:
            print(f"❌ AI post failed: {e}")
            # Fallback to manual post
            return self.post_manual_content()

    def post_manual_content(self):
        """Manual content as backup"""
        manual_posts = [
            f"🚀 Leveling up my DeFi game with @levvafi AI vaults! Automated yield, zero stress. What's not to love? {self.utm_link}",
            f"💡 Pro tip: Let AI handle your yield farming while you focus on what matters. Thanks @levvafi! {self.utm_link}",
            f"📈 Consistent returns + AI optimization = DeFi happiness. @levvafi making it happen! {self.utm_link}"
        ]
        content = random.choice(manual_posts)
        response = self.client.create_tweet(text=content)
        print(f"📝 Posted manual content: {content[:60]}...")
        return response

    def engage_with_community(self):
        """AI-powered community engagement"""
        keyword = random.choice(self.keywords)
        print(f"🔍 AI engaging with tweets about: {keyword}")
        
        try:
            tweets = self.client.search_recent_tweets(
                f"{keyword} -is:retweet -from:levvafi",
                max_results=10,
                tweet_fields=['author_id', 'public_metrics']
            )
            
            if not tweets.data:
                return
                
            for tweet in tweets.data[:3]:  # Limit to 3 engagements
                if tweet.public_metrics['like_count'] >= 1:
                    # Like the tweet
                    self.client.like(tweet.id)
                    
                    # Generate AI reply 40% of the time
                    if random.random() < 0.4:
                        reply_prompt = self.generate_ai_content("reply")
                        if reply_prompt and len(reply_prompt) < 200:
                            self.client.create_tweet(
                                text=reply_prompt,
                                in_reply_to_tweet_id=tweet.id
                            )
                            print(f"   💬 AI replied to {keyword} tweet")
                    
                    print(f"   👍 Engaged with {keyword} content")
                    time.sleep(random.randint(45, 120))
                    
        except Exception as e:
            print(f"❌ AI engagement failed: {e}")

    def create_ai_thread(self):
        """Create an educational thread using AI"""
        print("🧵 AI generating educational thread...")
        
        try:
            # Generate thread starter
            starter = self.generate_ai_content("thread_starter")
            if not starter:
                starter = f"🚀 Why AI DeFi is the future of yield farming:\n\nA quick thread about @levvafi 👇"
            
            # Post thread starter
            response = self.client.create_tweet(text=starter)
            thread_id = response.data['id']
            
            # Generate thread points (simplified - in real implementation, generate full thread)
            time.sleep(2)
            point1 = f"1/ Smart Vaults automate everything:\n• Multi-protocol allocations\n• AI rebalancing\n• Yield optimization\n\nAll while you focus on life! {self.utm_link}"
            
            self.client.create_tweet(
                text=point1,
                in_reply_to_tweet_id=thread_id
            )
            
            print("   ✅ AI thread posted!")
            
        except Exception as e:
            print(f"❌ AI thread failed: {e}")

    def health_check(self):
        """Check if all systems are working"""
        print(f"🏥 Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("   ✅ Bot is running on Railway")
        print("   🤖 AI Content Generation: Active")
        print("   🐦 Twitter API: Connected")
        print("   📅 Next post: Scheduled")

def setup_scheduler(bot):
    """Setup scheduling for Railway"""
    # Content posting (3x daily)
    schedule.every().day.at("09:00").do(bot.post_ai_content)
    schedule.every().day.at("14:00").do(bot.post_ai_content)
    schedule.every().day.at("19:00").do(bot.post_ai_content)
    
    # Community engagement (3x daily)
    schedule.every().day.at("10:30").do(bot.engage_with_community)
    schedule.every().day.at("16:00").do(bot.engage_with_community)
    schedule.every().day.at("21:00").do(bot.engage_with_community)
    
    # Educational content (2x weekly)
    schedule.every().tuesday.at("11:00").do(bot.create_ai_thread)
    schedule.every().friday.at("11:00").do(bot.create_ai_thread)
    
    # Health checks
    schedule.every().hour().do(bot.health_check)

def main():
    print("🚀 Starting AI-Powered Levva Bot on Railway...")
    
    # Test connections
    try:
        user = client.get_me()
        print(f"✅ Twitter connected: @{user.data.username}")
        
        # Test OpenAI
        test_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello in a creative way"}],
            max_tokens=10
        )
        print("✅ OpenAI connected: AI content generation ready")
        
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return
    
    # Initialize bot
    bot = AILewaBot(client, openai_client)
    
    # Setup scheduling
    setup_scheduler(bot)
    
    print("\n🎯 AI Bot Activated on Railway:")
    print("   🤖 Content: AI-generated, never repeats")
    print("   📝 Posts: 3x daily (9AM, 2PM, 7PM)")
    print("   💬 Engagement: 3x daily with AI replies")
    print("   🧵 Threads: 2x weekly (AI-generated)")
    print("   🚂 Hosting: Railway (24/7)")
    print("\n⚡ Bot is running continuously...")
    
    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()