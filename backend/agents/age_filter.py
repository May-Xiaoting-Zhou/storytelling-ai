import openai
from typing import Dict, List
from config import OPENAI_API_KEY

# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class AgeFilterAgent:
    def __init__(self):
        self.age_ranges = {
            '5-7': {
                'vocabulary_level': 'simple, concrete words, short sentences',
                'concepts': 'basic emotions, clear cause-effect, familiar situations',
                'themes': 'friendship, family, animals, simple adventures'
            },
            '8-10': {
                'vocabulary_level': 'expanded vocabulary, longer sentences, some abstract concepts',
                'concepts': 'more complex emotions, basic moral dilemmas, fantasy elements',
                'themes': 'teamwork, overcoming challenges, discovery, magical adventures'
            }
        }
        self.content_guidelines = {
            'prohibited': [
                'violence or physical harm',
                'scary or disturbing content',
                'adult themes or references',
                'complex political or social issues',
                'inappropriate language'
            ],
            'approach_with_care': [
                'loss or separation (gentle treatment)',
                'conflicts (with clear resolution)',
                'mistakes and consequences (with learning)',
                'differences between people (positive framing)'
            ]
        }
    
    def simplify_vocabulary(self, text: str, age_range: str = '5-7') -> str:
        """Simplify text vocabulary for the specified age range"""
        vocabulary_level = self.age_ranges.get(age_range, self.age_ranges['5-7'])['vocabulary_level']
        
        prompt = f"""
        Simplify this text for children aged {age_range}:
        
        Original text: {text}
        
        Target vocabulary level: {vocabulary_level}
        
        Guidelines:
        - Replace complex words with simpler alternatives
        - Shorten sentences where needed
        - Maintain the original meaning and story elements
        - Keep the text engaging and interesting
        - Do not remove important story elements
        
        Return only the simplified text without explanations.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in creating age-appropriate content for children."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=len(text) + 50  # Allow some expansion
        )
        
        return response.choices[0].message.content
    
    def check_content_safety(self, text: str) -> Dict:
        """Check if content is safe and appropriate for children aged 5-10"""
        prompt = f"""
        Evaluate this children's story content for age-appropriateness (ages 5-10):
        
        Content: {text}
        
        Prohibited content includes:
        {', '.join(self.content_guidelines['prohibited'])}
        
        Content to approach with care:
        {', '.join(self.content_guidelines['approach_with_care'])}
        
        Please identify:
        1. Any inappropriate content that should be removed
        2. Content that needs modification to be age-appropriate
        3. Whether the overall content is suitable for children aged 5-10
        
        Provide specific examples from the text if issues are found.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in child-appropriate content evaluation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        evaluation = response.choices[0].message.content
        
        # Determine if content is safe based on the evaluation
        is_safe = 'inappropriate' not in evaluation.lower() and 'not suitable' not in evaluation.lower()
        
        return {
            'is_safe': is_safe,
            'evaluation': evaluation,
            'needs_modification': not is_safe
        }
    
    def adjust_tone(self, text: str, target_tone: str = 'gentle') -> str:
        """Adjust the tone of the content to be appropriate for children"""
        prompt = f"""
        Adjust the tone of this children's story content to be {target_tone}:
        
        Original content: {text}
        
        Guidelines:
        - Maintain the same story and characters
        - Adjust language to create a {target_tone} tone
        - Ensure the content remains engaging and interesting
        - Keep vocabulary appropriate for children aged 5-10
        
        Return only the adjusted content without explanations.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in creating age-appropriate content for children."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=len(text) + 50  # Allow some expansion
        )
        
        return response.choices[0].message.content
    
    def filter_story(self, story: str, age_range: str = '5-10', target_tone: str = 'gentle') -> Dict:
        """Apply all filtering and adjustments to make content age-appropriate"""
        # First check content safety
        safety_check = self.check_content_safety(story)
        
        if not safety_check['is_safe']:
            # If not safe, we need to adjust the content
            adjusted_story = self.adjust_tone(story, target_tone)
            # Check again after adjustment
            safety_check = self.check_content_safety(adjusted_story)
        else:
            adjusted_story = story
        
        # Simplify vocabulary based on age range
        if '-' in age_range:
            # If range like '5-10', use the lower end for vocabulary simplification
            lower_age = age_range.split('-')[0]
            simplified_age_range = f"{lower_age}-{int(lower_age) + 2}"
        else:
            simplified_age_range = '5-7'  # Default to younger range
        
        simplified_story = self.simplify_vocabulary(adjusted_story, simplified_age_range)
        
        return {
            'original_story': story,
            'filtered_story': simplified_story,
            'is_safe': safety_check['is_safe'],
            'safety_evaluation': safety_check['evaluation'],
            'age_range': age_range,
            'modifications_made': story != simplified_story
        }