import openai
from typing import Dict, List, Optional
from config import OPENAI_API_KEY

# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class DialogueManagerAgent:
    def __init__(self):
        self.conversation_history = []
        self.story_state = {
            'current_scene': None,
            'characters': [],
            'choices_made': [],
            'user_inputs': [],
            'story_path': []
        }
        self.choice_templates = [
            "What should {character} do next?",
            "How should {character} respond to {situation}?",
            "Should {character} {option_a} or {option_b}?",
            "Where should {character} go to find {object}?"
        ]
    
    def reset_state(self):
        """Reset the story state for a new story"""
        self.conversation_history = []
        self.story_state = {
            'current_scene': None,
            'characters': [],
            'choices_made': [],
            'user_inputs': [],
            'story_path': []
        }
    
    def add_user_input(self, user_input: str):
        """Add user input to the conversation history and story state"""
        self.conversation_history.append({"role": "user", "content": user_input})
        self.story_state['user_inputs'].append(user_input)
    
    def add_system_response(self, response: str):
        """Add system response to the conversation history"""
        self.conversation_history.append({"role": "assistant", "content": response})
    
    def update_story_state(self, scene: str, characters: List[str], choice: Optional[str] = None):
        """Update the current story state"""
        self.story_state['current_scene'] = scene
        self.story_state['characters'] = characters
        if choice:
            self.story_state['choices_made'].append(choice)
            self.story_state['story_path'].append({
                'scene': scene,
                'choice': choice
            })
    
    def generate_story_choices(self, scene: str, character: str, num_choices: int = 2) -> List[str]:
        """Generate choices for the user to direct the story"""
        prompt = f"""
        Generate {num_choices} interesting choices for a children's story (ages 5-10) based on this scene:
        
        Scene: {scene}
        Main character involved: {character}
        
        Each choice should:
        1. Be clear and simple for children to understand
        2. Lead to different possible story directions
        3. Be age-appropriate and positive
        4. Be presented as a complete sentence describing what could happen next
        
        Format each choice as a numbered option.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an interactive storytelling assistant for children."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        choices_text = response.choices[0].message.content
        
        # In a real implementation, you would parse this text into a list of choices
        # For simplicity, we'll split by newlines and filter for numbered items
        choices = [line.strip() for line in choices_text.split('\n') if line.strip()]
        choices = [line for line in choices if any(line.startswith(str(i)) for i in range(1, 10))]
        
        return choices[:num_choices]  # Return only the requested number of choices
    
    def continue_story(self, user_choice: str) -> str:
        """Continue the story based on the user's choice"""
        # Add the user's choice to the state
        self.add_user_input(user_choice)
        
        # Create a prompt that includes the conversation history and user's choice
        story_context = f"""
        Current scene: {self.story_state['current_scene']}
        Characters: {', '.join(self.story_state['characters'])}
        User's choice: {user_choice}
        
        Previous story path: {self.story_state['story_path']}
        """
        
        prompt = f"""
        Continue this children's story (ages 5-10) based on the user's choice.
        
        {story_context}
        
        Write the next part of the story (2-3 paragraphs) that follows from the user's choice.
        Keep the language simple, engaging, and appropriate for young children.
        End with a new situation where the child can make another choice.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an interactive storytelling assistant for children."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        continuation = response.choices[0].message.content
        
        # Add the continuation to the conversation history
        self.add_system_response(continuation)
        
        # Extract the new scene from the continuation (simplified implementation)
        new_scene = continuation.split('\n\n')[0] if '\n\n' in continuation else continuation
        
        # Update the story state with the new scene
        self.update_story_state(new_scene, self.story_state['characters'], user_choice)
        
        return continuation
    
    def get_story_summary(self) -> str:
        """Generate a summary of the story so far"""
        if not self.story_state['story_path']:
            return "The story hasn't started yet."
        
        prompt = f"""
        Create a brief summary of this children's story so far:
        
        Story path: {self.story_state['story_path']}
        Characters: {', '.join(self.story_state['characters'])}
        Choices made: {self.story_state['choices_made']}
        
        Write a 2-3 sentence summary that captures the key events and choices.
        Use simple language appropriate for children ages 5-10.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a storytelling assistant for children."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content