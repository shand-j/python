"""
GPT Integration Module
Handles AI-powered description enhancement and tag generation
"""
from openai import OpenAI


class GPTProcessor:
    """GPT processor for content enhancement and tag generation"""
    
    def __init__(self, config, logger):
        """
        Initialize GPT processor
        
        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        
        if config.openai_api_key:
            # Support for custom base URL (like Ollama)
            base_url = getattr(config, 'openai_base_url', None)
            if base_url:
                self.client = OpenAI(api_key=config.openai_api_key, base_url=base_url)
                self.logger.info(f"Using custom OpenAI base URL: {base_url}")
            else:
                self.client = OpenAI(api_key=config.openai_api_key)
        else:
            self.client = None
            self.logger.warning("OpenAI API key not provided. GPT features will be disabled.")
    
    def enhance_description(self, original_description, product_name='', additional_context=''):
        """
        Enhance product description using GPT
        
        Args:
            original_description: Original product description
            product_name: Product name
            additional_context: Additional context (specs, features, etc.)
        
        Returns:
            str: Enhanced description
        """
        if not self.client:
            self.logger.warning("GPT client not initialized. Returning original description.")
            return original_description
        
        try:
            self.logger.info(f"Enhancing description for: {product_name}")
            
            prompt = f"""You are a professional product copywriter. Enhance the following product description to make it more compelling, clear, and SEO-friendly while maintaining factual accuracy.

Product Name: {product_name}

Original Description:
{original_description}

{f'Additional Context: {additional_context}' if additional_context else ''}

Instructions:
- Make it engaging and customer-focused
- Highlight key features and benefits
- Use clear, concise language
- Optimize for search engines
- Maintain all factual information
- Format with proper paragraphs

Enhanced Description:"""

            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are a professional product copywriter specializing in e-commerce."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            enhanced_description = response.choices[0].message.content.strip()
            self.logger.info("Description enhanced successfully")
            
            return enhanced_description
            
        except Exception as e:
            self.logger.error(f"Error enhancing description: {e}")
            return original_description
    
    def generate_tags(self, product_name, description, metadata=None):
        """
        Generate intelligent product tags using GPT
        
        Args:
            product_name: Product name
            description: Product description
            metadata: Additional metadata (breadcrumbs, categories, etc.)
        
        Returns:
            list: List of generated tags
        """
        if not self.client:
            self.logger.warning("GPT client not initialized. Returning basic tags.")
            return self._generate_basic_tags(product_name, description)
        
        try:
            self.logger.info(f"Generating tags for: {product_name}")
            
            metadata_str = ""
            if metadata:
                if metadata.get('breadcrumbs'):
                    metadata_str += f"\nCategories: {', '.join(metadata['breadcrumbs'])}"
                if metadata.get('keywords'):
                    metadata_str += f"\nKeywords: {metadata['keywords']}"
            
            prompt = f"""Generate relevant product tags for an e-commerce platform.

Product Name: {product_name}

Description:
{description[:500]}...

{metadata_str}

Instructions:
- Generate 10-15 relevant tags
- Include category tags, feature tags, and style tags
- Use lowercase
- Use single words or short phrases (2-3 words max)
- Make tags searchable and practical
- Focus on what customers would search for

Return only the tags, comma-separated, nothing else."""

            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are an e-commerce product tagging expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            tags_text = response.choices[0].message.content.strip()
            tags = [tag.strip().lower() for tag in tags_text.split(',')]
            
            # Clean up tags
            tags = [tag for tag in tags if tag and len(tag) > 2]
            
            self.logger.info(f"Generated {len(tags)} tags")
            
            return tags
            
        except Exception as e:
            self.logger.error(f"Error generating tags: {e}")
            return self._generate_basic_tags(product_name, description)
    
    def _generate_basic_tags(self, product_name, description):
        """
        Generate basic tags without GPT (fallback)
        
        Args:
            product_name: Product name
            description: Product description
        
        Returns:
            list: List of basic tags
        """
        tags = []
        
        # Extract words from product name
        words = product_name.lower().split()
        tags.extend([w for w in words if len(w) > 3])
        
        # Extract common keywords from description
        common_keywords = ['new', 'premium', 'quality', 'professional', 'modern', 'classic']
        description_lower = description.lower()
        for keyword in common_keywords:
            if keyword in description_lower:
                tags.append(keyword)
        
        return list(set(tags))[:10]
    
    def generate_summary(self, description, max_words=50):
        """
        Generate a short summary of the description
        
        Args:
            description: Full product description
            max_words: Maximum words in summary
        
        Returns:
            str: Summary text
        """
        if not self.client:
            # Fallback: return first N words
            words = description.split()
            return ' '.join(words[:max_words])
        
        try:
            self.logger.info("Generating description summary")
            
            prompt = f"""Create a concise summary of the following product description in {max_words} words or less.

Description:
{description}

Summary:"""

            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are a professional content summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=150
            )
            
            summary = response.choices[0].message.content.strip()
            self.logger.info("Summary generated successfully")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            words = description.split()
            return ' '.join(words[:max_words])
