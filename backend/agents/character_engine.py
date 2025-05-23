import openai
from typing import Dict, List
from config import OPENAI_API_KEY

# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class CharacterEngineAgent:
    def __init__(self):
        self.character_templates = {
            'hero': {
                'personality': 'brave, kind, determined',
                'voice': 'enthusiastic, positive, encouraging',
                'emotional_range': ['excited', 'determined', 'concerned', 'joyful']
            },
            'mentor': {
                'personality': 'wise, patient, supportive',
                'voice': 'calm, thoughtful, nurturing',
                'emotional_range': ['proud', 'concerned', 'hopeful', 'understanding']
            },
            'friend': {
                'personality': 'loyal, playful, helpful',
                'voice': 'cheerful, energetic, friendly',
                'emotional_range': ['happy', 'curious', 'worried', 'excited']
            },
            'animal_companion': {
                'personality': 'loyal, intuitive, protective',
                'voice': 'simple, direct, expressive',
                'emotional_range': ['playful', 'alert', 'affectionate', 'cautious']
            },
            'magical_being': {
                'personality': 'mysterious, whimsical, knowledgeable',
                'voice': 'lyrical, magical, slightly formal',
                'emotional_range': ['amused', 'curious', 'mysterious', 'delighted']
            }
        }
        
    def generate_character(self, character_type: str, name: str, story_theme: str) -> Dict:
        """Generate a character with consistent personality and voice"""
        template = self.character_templates.get(character_type, self.character_templates['friend'])
        
        prompt = f"""
        Create a character for a children's story (ages 5-10) with these specifications:
        - Name: {name}
        - Type: {character_type}
        - Story theme: {story_theme}
        - Personality traits: {template['personality']}
        - Voice style: {template['voice']}
        
        Provide a brief background, key traits, and 3 example dialogue lines that showcase this character's voice.
        Make sure the character is engaging for children and supports positive values.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative character designer for children's stories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        character_description = response.choices[0].message.content
        
        return {
            'name': name,
            'type': character_type,
            'theme': story_theme,
            'personality': template['personality'],
            'voice': template['voice'],
            'emotional_range': template['emotional_range'],
            'description': character_description,
        }
    
    def generate_dialogue(self, character: Dict, situation: str, emotion: str) -> str:
        """Generate dialogue for a character in a specific situation with consistent voice"""
        prompt = f"""
        Generate dialogue for this character in a children's story (ages 5-10):
        
        Character: {character['name']} ({character['type']})
        Personality: {character['personality']}
        Voice style: {character['voice']}
        Current emotion: {emotion}
        Situation: {situation}
        
        Write 1-3 lines of dialogue that this character would say in this situation.
        Maintain their unique voice and personality while expressing the specified emotion.
        Keep the language simple and appropriate for young children.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at writing authentic character dialogue for children's stories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content
    
    def get_character_suggestions(self, story_theme: str, target_age: str) -> List[Dict]:
        """Suggest appropriate characters for a story based on theme and age group"""
        prompt = f"""
        Suggest 3 characters for a children's story with these specifications:
        - Theme: {story_theme}
        - Target age: {target_age}
        
        For each character, provide:
        1. Character type (e.g., hero, mentor, friend, animal companion)
        2. Name suggestion
        3. Brief role in the story
        4. One personality trait that makes them interesting
        
        Make sure the characters are age-appropriate and would work well together in a story.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative character designer for children's stories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        # Process the response to extract character suggestions
        # This is a simplified implementation
        suggestions_text = response.choices[0].message.content
        
        # In a real implementation, you would parse this text into structured data
        # For now, we'll return a simplified version
        return [
            {'type': 'hero', 'name': 'Suggested Name 1', 'description': suggestions_text}
        ]