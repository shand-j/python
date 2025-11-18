"""
User Agent Rotation Module
Manages user agent rotation for respectful scraping
"""
import random
from typing import List


class UserAgentRotator:
    """Rotates user agents for web scraping"""
    
    # Realistic browser user agents
    USER_AGENTS = [
        # Chrome on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        
        # Chrome on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        
        # Firefox on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        
        # Firefox on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        
        # Safari on Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        
        # Edge on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    ]
    
    def __init__(self, logger=None):
        """
        Initialize user agent rotator
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.current_index = 0
        self.use_random = True
    
    def get_user_agent(self) -> str:
        """
        Get a user agent
        
        Returns:
            User agent string
        """
        if self.use_random:
            return random.choice(self.USER_AGENTS)
        else:
            # Sequential rotation
            user_agent = self.USER_AGENTS[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.USER_AGENTS)
            return user_agent
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.USER_AGENTS)
    
    def set_rotation_mode(self, random_mode: bool):
        """
        Set rotation mode
        
        Args:
            random_mode: True for random selection, False for sequential
        """
        self.use_random = random_mode
        if self.logger:
            mode = "random" if random_mode else "sequential"
            self.logger.debug(f"User agent rotation mode: {mode}")
    
    def get_all_user_agents(self) -> List[str]:
        """Get all available user agents"""
        return self.USER_AGENTS.copy()
    
    def add_custom_user_agent(self, user_agent: str):
        """Add a custom user agent to the pool"""
        if user_agent not in self.USER_AGENTS:
            self.USER_AGENTS.append(user_agent)
            if self.logger:
                self.logger.debug(f"Added custom user agent")
