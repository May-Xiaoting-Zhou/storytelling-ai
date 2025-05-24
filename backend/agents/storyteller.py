import openai
from typing import Dict, List, Optional
from agents.story_database import StoryDatabase
from agents.character_engine import CharacterEngineAgent
from agents.dialogue_manager import DialogueManagerAgent
from agents.imagination_booster import ImaginationBoosterAgent
from agents.age_filter import AgeFilterAgent
from agents.memory_personalization import MemoryPersonalizationAgent
from config import OPENAI_API_KEY
# from .kids_story_api import kids_story_api

# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class StorytellerAgent:
    def __init__(self):
        # Initialize all agent components
        self.story_db = StoryDatabase()
        self.character_engine = CharacterEngineAgent()
        self.dialogue_manager = DialogueManagerAgent()
        self.imagination_booster = ImaginationBoosterAgent()
        self.age_filter = AgeFilterAgent()
        self.memory_personalization = MemoryPersonalizationAgent()
        
        self.story_elements_defaults = { # Renamed for clarity
            'moral_values': ['kindness', 'honesty', 'friendship', 'courage', 'perseverance'],
            'themes': ['adventure', 'discovery', 'helping others', 'overcoming challenges', 'learning'],
            'characters': ['children', 'animals', 'magical creatures', 'family members', 'friends']
        }

    def _get_llm_story_prompt(self, user_prompt_str: str, story_elements: Dict, user_id: Optional[str] = None, last_story_text: Optional[str] = None, intent: str = "new_story", instruction: str = "") -> str:
        # Create a detailed prompt for the LLM
        # This internal method will be more flexible to handle different intents
        
        age_appropriateness = "Create a story suitable for children aged 5-10."
        story_guidelines = """
Guidelines:
- Keep the language simple and age-appropriate.
- Include positive messages and moral values.
- Make it engaging.
- Avoid scary or inappropriate content.
- Keep the story length to 3-5 paragraphs.

Story structure:
1. Introduction: Set up the main character and setting.
2. Challenge: Present a problem or adventure.
3. Development: Show character growth or learning.
4. Resolution: Solve the problem in a positive way.
5. Moral: Include a gentle life lesson (if appropriate for the story).
"""

        prompt_parts = [age_appropriateness]

        if intent == "new_story":
            if story_elements and any(story_elements.values()): # Check if story_elements has meaningful content
                characters = story_elements.get("characters", self.story_elements_defaults['characters'])
                setting = story_elements.get("setting", "a wonderful place")
                conflict = story_elements.get("conflict", "a mysterious challenge")
                plot_idea = story_elements.get("plot_idea", "an adventure story")
                themes = story_elements.get("themes", self.story_elements_defaults['themes'])
                
                # Ensure characters is a list of strings for joining, or handle dict structure
                if characters and isinstance(characters[0], dict):
                    char_names = " and ".join([c.get('name', 'a character') for c in characters])
                    char_descs = ", ".join([f"{c.get('name', 'A character')} who is {c.get('description', 'interesting')}" for c in characters])
                else: # Assuming list of strings or simple names
                    char_names = " and ".join(characters) if characters else "a brave hero"
                    char_descs = char_names

                prompt_parts.append(f"Tell a new story based on the user's request: '{user_prompt_str}'.")
                prompt_parts.append(f"Incorporate these elements if possible: Characters like {char_names}, in a setting like '{setting}'. The story could involve a conflict like '{conflict}' and follow a plot idea of '{plot_idea}'. Explore themes such as {', '.join(themes)}.")
            else:
                prompt_parts.append(f"Tell a new story based on this prompt: {user_prompt_str}")
        
        elif intent in ["change_story", "update_story"]:
            if not last_story_text:
                # Fallback to new story if last story is not available
                prompt_parts.append(f"The user wants to change a story, but the previous story is unavailable. Please generate a new story based on: {user_prompt_str} and instruction {instruction}")
            else:
                prompt_parts.append(f"The user wants to modify a previous story. Here is the original story:\n---BEGIN ORIGINAL STORY---\n{last_story_text}\n---END ORIGINAL STORY---")
                modification_instruction = f"Please revise the story significantly based on the user's new request and instruction {instruction}."
                if intent == "update_story":
                    modification_instruction = "Please update the story strictly following the user's new request, focusing on incorporating their specific changes."
                prompt_parts.append(f"User's new request for changes: '{instruction}'. {modification_instruction}")

        prompt_parts.append(story_guidelines)
        
        final_prompt = "\n\n".join(prompt_parts)
        
        if user_id and user_id != 'guest_user':
            # Personalize the prompt using MemoryPersonalizationAgent
            # This assumes personalize_story_prompt can take the constructed prompt and user_id
            final_prompt = self.memory_personalization.personalize_story_prompt(final_prompt, user_id)
            
        return final_prompt

    def generate_story(self, prompt: str, user_id: Optional[str], story_elements: Dict, intent: str, instruction: str) -> Dict:
        last_story_text = None
        if intent in ["change_story", "update_story"] and user_id:
            # Fetch last story for the user. 
            # This requires story_db to have a method like get_last_story_for_user(user_id)
            # For now, let's assume it returns the text or None.
            # You'll need to implement this in StoryDatabase or retrieve from conversations.json if that's where full stories are logged.
            # Based on conversations.json, the last agent message with status 'success' might be the one.
            user_conversations = self.story_db.get_conversations_by_user_id(user_id) # Assuming this method exists
            if user_conversations:
                # Find the most recent conversation with a successful story
                for conv in sorted(user_conversations, key=lambda x: x.get('timestamp'), reverse=True):
                    for message in reversed(conv.get('messages', [])):
                        if message.get('role') == 'agent' and message.get('status') == 'success' and message.get('content'):
                            last_story_text = message['content']
                            break
                    if last_story_text:
                        break
        
        # Prepare the detailed prompt for the LLM
        # The _get_llm_story_prompt will handle personalization internally if user_id is not guest
        llm_prompt = self._get_llm_story_prompt(
            user_prompt_str=prompt, 
            story_elements=story_elements, 
            user_id=user_id, 
            last_story_text=last_story_text, 
            intent=intent,
            instruction=instruction
        )

        # Call OpenAI LLM
        try:
            completion = openai.chat.completions.create(
                model="gpt-4", # Or gpt-3.5-turbo for faster/cheaper, gpt-4 for quality
                messages=[
                    {"role": "system", "content": "You are a kind and imaginative storyteller for kids aged 5-10. Follow the user's intent carefully, whether it's creating a new story, changing an existing one, or updating one with specific details."},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.7, # Adjust for creativity vs. determinism
                max_tokens=1000 # Adjust as needed for story length
            )
            generated_story_text = completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return {"story": "I had a little trouble coming up with a story right now. Please try again!", "error": str(e)}

        # For now, metadata generation is simplified. You might want to enhance this.
        story_metadata = {
            'length': len(generated_story_text),
            'complexity': 0, # Placeholder, implement complexity calculation if needed
            'theme': story_elements.get('themes', ['unknown'])[0] if story_elements.get('themes') else 'unknown',
            'moral': 'A gentle life lesson was woven into the story.' # Placeholder
        }
        
        # Save the story
        story_id = self.story_db.add_story(prompt, generated_story_text, story_metadata)
        if user_id:
            user_story_id = self.story_db.add_user_story(prompt, user_id, story_id, intent)

        return {
            'story': generated_story_text,
            'metadata': story_metadata,
            'story_id': story_id,
            'user_story_id': user_story_id
        }

        # Default age_range, can be overridden if passed as a parameter or set in class
        age_range = story_elements.get('age_range', '5-10') 

        # Placeholder for actual age filtering logic if needed here
        # For now, we assume the LLM prompt already handles age appropriateness.
        # If AgeFilterAgent needs to be called on generated_story_text, it would happen here.
        # filtered_result = self.age_filter.filter_story(generated_story_text, age_range)
        # For now, let's assume it's safe by default from the LLM generation
        is_safe_placeholder = True 

        # The 'enhanced_story' would typically be the generated_story_text, 
        # or a version further processed by other agents (e.g., imagination_booster)
        # For this direct update, let's use generated_story_text.
        enhanced_story = generated_story_text

        return {
            'story': enhanced_story, # This was generated_story_text
            'illustration_url': None,  # Placeholder for illustration URL
            # 'illustration_url': illustration.get('url'), 
            'is_appropriate': is_safe_placeholder, # Placeholder, integrate with AgeFilterAgent if needed
            'interactive_elements': None,  # Placeholder for interactive elements 
            # 'interactive_elements': interactive_elements, 
            'age_range': age_range 
        }

    # Remove or comment out the old generate_story and generate_story_from_elements
    # def generate_story_from_elements(self, elements: Dict) -> Dict:
    #     // ... existing code ...

    # def generate_story(self, prompt: str, user_id: Optional[str] = None, age_range: str = '5-10', interactive: bool = False) -> Dict:
        # Retrieve similar stories using RAG
        similar_stories = self.story_db.get_similar_stories(prompt) if hasattr(self.story_db, 'get_similar_stories') else []
            
        # Generate story using OpenAI with personalization if user_id is provided
        story_prompt = self._get_story_prompt(prompt, similar_stories, user_id)
        
        # Get character suggestions based on the prompt
        theme = self._extract_theme(prompt)
        character_suggestions = self.character_engine.get_character_suggestions(theme, age_range)
        
        # Enhance the prompt with character information
        enhanced_prompt = f"{story_prompt}\n\nInclude these characters: {character_suggestions[0]['description'] if character_suggestions else 'Create engaging characters appropriate for the story.'}"
        
        # Generate the initial story
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative storyteller for children aged 5-10."},
                {"role": "user", "content": enhanced_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        story = response.choices[0].message.content
        
        # Apply age filter to ensure content is appropriate
        filtered_result = self.age_filter.filter_story(story, age_range)
        filtered_story = filtered_result['filtered_story']
        
        # Enhance story with sensory details
        enhanced_story = self.imagination_booster.enhance_story_description(filtered_story)
        
        # Generate illustration for the story
        # illustration = self.imagination_booster.generate_illustration(self._extract_scene(enhanced_story))
        
        # If interactive mode is enabled, prepare interactive elements
        # interactive_elements = {}
        # if interactive:
        #     # Reset dialogue manager state
        #     self.dialogue_manager.reset_state()
            
        #     # Extract main character and scene
        #     main_character = self._extract_main_character(enhanced_story)
        #     main_scene = self._extract_scene(enhanced_story)
            
        #     # Update story state
        #     self.dialogue_manager.update_story_state(main_scene, [main_character])
            
        #     # Generate choices for the user
        #     choices = self.dialogue_manager.generate_story_choices(main_scene, main_character)
            
        #     interactive_elements = {
        #         'choices': choices,
        #         'main_character': main_character,
        #         'current_scene': main_scene
        #     }
        
        # Store the story in the database
        self.story_db.store_story(prompt, enhanced_story)
        
        # If user_id is provided, record the interaction
        if user_id:
            story_data = {
                'prompt': prompt,
                'title': self._extract_title(enhanced_story),
                'summary': self._extract_summary(enhanced_story)
            }
            self.memory_personalization.record_story_interaction(user_id, story_data, 0)  # 0 is placeholder for interaction time
        
        # Return the complete story package
        return {
            'story': enhanced_story,
            'illustration_url': None,  # Placeholder for illustration URL
            # 'illustration_url': illustration.get('url'),
            'is_appropriate': filtered_result['is_safe'],
            'interactive_elements': None,  # Placeholder for interactive elements
            # 'interactive_elements': interactive_elements,
            'age_range': age_range
        }

    def regenerate_story(self, prompt: str, old_story: str, story_elements: Dict, evaluation: str, feedback: str, user_id: Optional[str], intent: str) -> Dict:
        # Regenerate story incorporating feedback
        # Original prompt for context (can be part of the initial 'prompt' variable or constructed here)
        # initial_story_prompt = prompt 

        # Construct a more detailed prompt for regeneration
        updated_prompt = (
            f"Please revise the following story based on the user's intent, evaluation, and feedback.\n\n"
            f"User's Original Intent: {intent}\n\n"
            f"Original Story:\n{old_story}\n\n"
            f"Evaluation of the Original Story: {evaluation}\n\n"
            f"Specific Feedback for Improvement: {feedback}\n\n"
            f"Rewrite the story, ensuring it aligns with the original intent while addressing the evaluation and incorporating the feedback. "
            f"The story should still be based on the initial prompt: {prompt}"
        )

        # If you have specific story_elements to maintain or incorporate, you can add them here:
        # if story_elements:
        #     elements_text = ", ".join([f'{k}: {v}' for k, v in story_elements.items()])
        #     updated_prompt += f"\n\nRemember to include these elements: {elements_text}."

        # Call to the language model
        # new_story_text = self.llm.generate(updated_prompt)
        return self.generate_story(updated_prompt, user_id, story_elements, intent)
    
    def continue_interactive_story(self, user_choice: str) -> Dict:
        """Continue an interactive story based on user's choice"""
        # Use dialogue manager to continue the story
        continuation = self.dialogue_manager.continue_story(user_choice)
        
        # Extract the new scene and generate new choices
        new_scene = self.dialogue_manager.story_state['current_scene']
        main_character = self.dialogue_manager.story_state['characters'][0] if self.dialogue_manager.story_state['characters'] else 'character'
        
        # Generate new choices
        new_choices = self.dialogue_manager.generate_story_choices(new_scene, main_character)
        
        # Generate illustration for the new scene
        illustration = self.imagination_booster.generate_illustration(new_scene)
        
        return {
            'continuation': continuation,
            'illustration_url': illustration.get('url'),
            'choices': new_choices,
            'current_scene': new_scene
        }
    
    def get_story_summary(self) -> str:
        """Get a summary of the current interactive story"""
        return self.dialogue_manager.get_story_summary()
    
    def get_personalized_recommendations(self, user_id: str, num_recommendations: int = 3) -> List[str]:
        """Get personalized story recommendations for a user"""
        return self.memory_personalization.get_personalized_recommendations(user_id, num_recommendations)
    
    def _extract_theme(self, prompt: str) -> str:
        """Extract the main theme from a story prompt"""
        # Simple implementation - in a real system, this would use NLP
        for theme in self.story_elements['themes']:
            if theme.lower() in prompt.lower():
                return theme
        return 'adventure'  # Default theme
    
    def _extract_scene(self, story: str) -> str:
        """Extract the main scene from a story for illustration"""
        # Simple implementation - in a real system, this would use NLP
        paragraphs = story.split('\n\n')
        return paragraphs[0] if paragraphs else story[:200]
    
    def _extract_main_character(self, story: str) -> str:
        """Extract the main character from a story"""
        # Simple implementation - in a real system, this would use NLP
        for character_type in self.story_elements['characters']:
            if character_type.lower() in story.lower():
                return character_type
        return 'character'  # Default
    
    def _extract_title(self, story: str) -> str:
        """Extract or generate a title for the story"""
        # Simple implementation - in a real system, this would use NLP
        return "Untitled Story"
    
    def _extract_summary(self, story: str) -> str:
        """Extract or generate a summary of the story"""
        # Simple implementation - in a real system, this would use NLP
        return story[:100] + "..."