import openai
from typing import Dict, List, Optional
from config import OPENAI_API_KEY
import base64
import json

# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class ImaginationBoosterAgent:
    def __init__(self):
        self.image_style_presets = {
            'cartoon': 'colorful cartoon style, child-friendly, vibrant colors',
            'watercolor': 'soft watercolor illustration, gentle colors, dreamy',
            'storybook': 'classic storybook illustration, detailed, warm colors',
            'pixel_art': 'cute pixel art style, colorful, simple shapes',
            'claymation': 'claymation style, 3D clay figures, bright colors'
        }
        self.voice_style_presets = {
            'narrator': 'warm, clear, engaging storyteller voice',
            'character': 'expressive, distinctive character voice',
            'whimsical': 'playful, magical, slightly musical voice',
            'educational': 'clear, patient, encouraging teaching voice'
        }
    
    def generate_illustration(self, scene_description: str, style: str = 'cartoon', size: str = '512x512') -> Dict:
        """Generate an illustration for a story scene"""
        style_prompt = self.image_style_presets.get(style, self.image_style_presets['cartoon'])
        
        prompt = f"""
        Create a child-friendly illustration for a children's story (ages 5-10):
        
        Scene: {scene_description}
        
        Style: {style_prompt}
        
        The image should be:
        - Appropriate for young children
        - Colorful and engaging
        - Clear and easy to understand
        - Without any text or words
        - Focused on the main elements of the scene
        """
        
        try:
            response = openai.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1,
            )
            
            # In a real implementation, you would handle the image data
            # For now, we'll return the URL and other metadata
            return {
                'url': response.data[0].url,
                'style': style,
                'scene': scene_description,
                'success': True
            }
            
        except Exception as e:
            print(f"Error generating illustration: {e}")
            return {
                'url': None,
                'style': style,
                'scene': scene_description,
                'success': False,
                'error': str(e)
            }
    
    def generate_voice_narration(self, text: str, voice_style: str = 'narrator') -> Dict:
        """Generate voice narration for story text"""
        style_description = self.voice_style_presets.get(voice_style, self.voice_style_presets['narrator'])
        
        prompt = f"""
        Create voice narration for a children's story (ages 5-10) with these specifications:
        
        Text to narrate: {text}
        
        Voice style: {style_description}
        
        The narration should be:
        - Clear and easy to understand
        - Expressive and engaging for children
        - Appropriate pace (not too fast or slow)
        - With appropriate emotional tone for the content
        """
        
        # Note: This is a placeholder for actual TTS implementation
        # In a real application, you would use a TTS service like OpenAI's TTS API,
        # Amazon Polly, Google Text-to-Speech, etc.
        
        # Simulating a response for demonstration purposes
        return {
            'audio_url': None,  # Would be a URL to the generated audio file
            'text': text,
            'voice_style': voice_style,
            'success': True,
            'message': 'Voice narration would be generated here using a TTS service'
        }
    
    def enhance_story_description(self, scene_text: str) -> str:
        """Enhance a story scene with more vivid sensory details"""
        prompt = f"""
        Enhance this scene from a children's story (ages 5-10) with more vivid sensory details:
        
        Original scene: {scene_text}
        
        Add details about:
        - Colors, shapes, and visual elements
        - Sounds in the environment
        - Textures or tactile elements
        - Smells or scents if relevant
        
        Keep the language simple and appropriate for young children.
        Maintain the same events and actions, just make them more vivid.
        The enhanced description should be about the same length or slightly longer.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative children's story enhancer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content
    
    def generate_scene_background(self, scene_description: str, mood: str) -> str:
        """Generate background music/sound suggestions for a scene"""
        prompt = f"""
        Suggest background sounds or music for this scene in a children's story (ages 5-10):
        
        Scene: {scene_description}
        Mood: {mood}
        
        Describe:
        1. What type of background music would enhance this scene
        2. Any sound effects that would make the scene more immersive
        3. How the sounds should change as the scene progresses
        
        Keep suggestions appropriate for young children and enhancing to the story experience.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative sound designer for children's stories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content