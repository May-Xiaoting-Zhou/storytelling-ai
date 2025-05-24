import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import openai
from config import OPENAI_API_KEY

# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class MemoryPersonalizationAgent:
    def __init__(self):
        self.db_path = Path('database')
        self.user_profiles_path = self.db_path / 'user_profiles.json'
        self._initialize_database()
        self.preference_categories = {
            'characters': [],
            'themes': [],
            'story_types': [],
            'interaction_patterns': []
        }
    
    def _initialize_database(self) -> None:
        # Create database directory if it doesn't exist
        self.db_path.mkdir(exist_ok=True)
        
        # Initialize user profiles file
        if not self.user_profiles_path.exists():
            self._save_json(self.user_profiles_path, {})
    
    def _load_json(self, path: Path) -> Dict:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    
    def _save_json(self, path: Path, data: Dict) -> None:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_next_user_id(self, current_profiles):
        if not current_profiles:
            return "1"
        # Convert existing IDs to integers where possible and find max
        existing_ids = []
        for user_id in current_profiles.keys():
            try:
                existing_ids.append(int(user_id))
            except ValueError:
                continue
        return str(max(existing_ids) + 1) if existing_ids else "1"

    def get_user_profile(self, user_id: str) -> Dict:
        """Get a user's profile or create a new one if it doesn't exist"""
        profiles = self._load_json(self.user_profiles_path)
        
        if user_id not in profiles:
            # Create a new profile
            profiles[user_id] = {
                'user_id': user_id,
                'age': None,
                'gender': None,
                'created_at': datetime.now().isoformat(),
                'last_interaction': datetime.now().isoformat(),
                'story_history': [],
                'preferences': {
                    'favorite_characters': [],
                    'favorite_themes': [],
                    'favorite_story_types': [],
                    'reading_level': 'beginner',
                    'interaction_style': 'guided'
                },
                'metrics': {
                    'stories_completed': 0,
                    'total_interactions': 0,
                    'average_engagement_time': 0
                }
            }
            self._save_json(self.user_profiles_path, profiles)
        
        return profiles[user_id]
    
    def update_user_profile(self, user_id: str, profile_updates: Dict) -> Dict:
        """Update a user's profile with new information"""
        profiles = self._load_json(self.user_profiles_path)
        
        if user_id not in profiles:
            # Create a new profile if it doesn't exist
            # Ensure it's created with the new structure if it was missing
            user_profile = self.get_user_profile(user_id) 
            profiles[user_id] = user_profile # Add to profiles dict to be saved later
        else:
            user_profile = profiles[user_id]
        
        # Update last interaction time
        user_profile['last_interaction'] = datetime.now().isoformat()

        # Update top-level age and gender if provided directly in profile_updates
        if 'age' in profile_updates:
            user_profile['age'] = profile_updates['age']
        if 'gender' in profile_updates:
            user_profile['gender'] = profile_updates['gender']
        
        # Update preferences if provided
        if 'preferences' in profile_updates:
            for key, value in profile_updates['preferences'].items():
                # Ensure the key exists in the profile's preferences to avoid adding new arbitrary keys
                if key in user_profile.get('preferences', {}):
                    user_profile['preferences'][key] = value
        
        # Update metrics if provided
        if 'metrics' in profile_updates:
            for key, value in profile_updates['metrics'].items():
                if key in user_profile['metrics']:
                    user_profile['metrics'][key] = value
        
        # Add story to history if provided
        if 'story' in profile_updates:
            user_profile['story_history'].append({
                'timestamp': datetime.now().isoformat(),
                'prompt': profile_updates['story'].get('prompt', ''),
                'title': profile_updates['story'].get('title', 'Untitled Story'),
                'summary': profile_updates['story'].get('summary', ''),
                'user_feedback': profile_updates['story'].get('user_feedback', None)
            })
            user_profile['metrics']['stories_completed'] += 1
        
        # Increment total interactions
        user_profile['metrics']['total_interactions'] += 1
        
        # Save updated profiles
        self._save_json(self.user_profiles_path, profiles)
        
        return user_profile
    
    def gather_user_preferences(self, user_id: str, user_prompt: str) -> Dict:
        """
        Gathers initial user preferences from a prompt (e.g., "5 years old girl, likes Snow White")
        and updates the user profile.
        """
        # Prepare a prompt for the LLM to extract preferences
        extraction_prompt = f"""
        Analyze the following user description to extract preferences for children's stories.
        User description: "{user_prompt}"

        Extract the following information if available:
        1. Age (integer, e.g., 5)
        2. Gender (string, e.g., "female", "male", "girl, "boy", "other", or null if not specified)
        3. Favorite characters (list of strings, e.g., ["Snow White", "dinosaurs"])
        4. Favorite themes (list of strings, e.g., ["adventure", "magic"])
        5. Favorite story types (list of strings, e.g., ["fairy tales", "animal stories"])
        6. Reading level (string, e.g., "beginner", "intermediate", "advanced", or null if not specified)
        7. Interaction style (string, e.g., "guided", "exploratory", or null if not specified)

        Format your response as a JSON object with the keys: "age", "gender", "favorite_characters", 
        "favorite_themes", "favorite_story_types", "reading_level", "interaction_style".
        If a piece of information is not found or cannot be reliably extracted, use null for single string values 
        (age, gender, reading_level, interaction_style) or an empty list for list values.
        For age, if a specific number is mentioned (e.g., "5 years old"), extract the number.
        """

        extracted_preferences = {}
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo", 
                messages=[
                    {"role": "system", "content": "You are an expert in extracting user preferences from text for personalizing children's stories. Respond in JSON format."},
                    {"role": "user", "content": extraction_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=300
            )
            
            extracted_info_str = response.choices[0].message.content
            extracted_preferences = json.loads(extracted_info_str)

        except Exception as e:
            # Log error, and fall back to an empty set of preferences or handle error appropriately
            print(f"Error extracting preferences using LLM: {e}") # Basic logging for now
            # Fallback to empty, so profile_updates might be empty if LLM fails

        # Prepare profile_updates dictionary
        # Age and gender will be top-level, other preferences will be under 'preferences' key
        profile_updates = {} 
        preferences_specific_updates = {}

        age_val = extracted_preferences.get('age')
        if age_val is not None:
            try:
                profile_updates['age'] = int(age_val)
            except (ValueError, TypeError):
                current_profile = self.get_user_profile(user_id) 
                if current_profile.get('age') is None: # Check top-level age
                     profile_updates['age'] = None

        gender_val = extracted_preferences.get('gender')
        if gender_val and isinstance(gender_val, str): 
            profile_updates['gender'] = gender_val
        
        for key in ['favorite_characters', 'favorite_themes', 'favorite_story_types']:
            value = extracted_preferences.get(key)
            if isinstance(value, list) and value: 
                preferences_specific_updates[key] = value
        
        reading_level = extracted_preferences.get('reading_level')
        if reading_level and isinstance(reading_level, str):
            preferences_specific_updates['reading_level'] = reading_level
            
        interaction_style = extracted_preferences.get('interaction_style')
        if interaction_style and isinstance(interaction_style, str):
            preferences_specific_updates['interaction_style'] = interaction_style

        if preferences_specific_updates:
            profile_updates['preferences'] = preferences_specific_updates

        if profile_updates: # Check if there are any updates (top-level or preferences)
            return self.update_user_profile(user_id, profile_updates)
        else:
            return self.get_user_profile(user_id)

    def analyze_preferences(self, user_id: str) -> Dict:
        """Analyze user preferences based on their history"""
        user_profile = self.get_user_profile(user_id)
        
        # Age and gender are now top-level
        # The returned structure here is for the LLM analysis, not the direct profile structure
        # So, we can keep its output structure as is, or adjust if needed for consumers of this method.
        # For now, let's assume its output structure is fine.
        # It mainly uses preferences like reading_level and interaction_style from the preferences dict.
        if not user_profile['story_history']:
            return {
                'favorite_characters': user_profile['preferences'].get('favorite_characters', []),
                'favorite_themes': user_profile['preferences'].get('favorite_themes', []),
                'favorite_story_types': user_profile['preferences'].get('favorite_story_types', []),
                'reading_level': user_profile['preferences'].get('reading_level', 'beginner'),
                'interaction_style': user_profile['preferences'].get('interaction_style', 'guided'),
                'age': user_profile.get('age'), # Include age from top-level
                'gender': user_profile.get('gender') # Include gender from top-level
            }
        
        if not user_profile['story_history']:
            return {
                'favorite_characters': [],
                'favorite_themes': [],
                'favorite_story_types': [],
                'reading_level': user_profile['preferences']['reading_level'],
                'interaction_style': user_profile['preferences']['interaction_style']
            }
        
        # Prepare story history for analysis
        story_history = []
        for story in user_profile['story_history']:
            story_history.append(f"Prompt: {story['prompt']}\nTitle: {story['title']}\nSummary: {story['summary']}")
        
        story_history_text = "\n\n".join(story_history)
        
        prompt = f"""
        Analyze this user's story history to identify their preferences:
        
        {story_history_text}
        
        Based on this history, identify:
        1. Favorite character types or specific characters
        2. Favorite themes or topics
        3. Favorite story types (adventure, fantasy, educational, etc.)
        4. Appropriate reading level (beginner, intermediate, advanced)
        5. Preferred interaction style (guided, exploratory, educational)
        
        Format your response as a structured analysis of preferences.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in analyzing user preferences for children's stories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        analysis = response.choices[0].message.content
        
        # In a real implementation, you would parse this text into structured data
        # For now, we'll return a simplified version
        return {
            'analysis': analysis,
            'reading_level': user_profile['preferences'].get('reading_level', 'beginner'),
            'interaction_style': user_profile['preferences'].get('interaction_style', 'guided'),
            'age': user_profile.get('age'), # Include age from top-level
            'gender': user_profile.get('gender') # Include gender from top-level
        }
    
    def personalize_story_prompt(self, base_prompt: str, user_id: str) -> str:
        """Personalize a story prompt based on user preferences to generate a RAG prompt."""
        user_profile = self.get_user_profile(user_id)
        if not user_profile:
            # Fallback if user profile doesn't exist or couldn't be loaded
            return f"Base Prompt: {base_prompt}\n\nUser Profile: Not available. Please generate a story based on the base prompt."

        preferences = user_profile.get('preferences', {})
        age = user_profile.get('age')
        gender = user_profile.get('gender')
        story_history = user_profile.get('story_history', [])

        # Construct the RAG prompt
        rag_prompt_parts = [
            "You are a creative storyteller AI. Your task is to generate a compelling and age-appropriate story.",
            "Please use the following base prompt and user profile information to tailor the story.",
            "--- BASE PROMPT ---",
            base_prompt,
            "--- USER PROFILE ---"
        ]

        if age is not None:
            rag_prompt_parts.append(f"- Target Age: {age}")
        if gender:
            rag_prompt_parts.append(f"- User Gender: {gender}")
        
        fav_chars = preferences.get('favorite_characters', [])
        if fav_chars:
            rag_prompt_parts.append(f"- Favorite Characters to consider including or taking inspiration from: {', '.join(fav_chars)}")
        
        fav_themes = preferences.get('favorite_themes', [])
        if fav_themes:
            rag_prompt_parts.append(f"- Favorite Themes to weave into the story: {', '.join(fav_themes)}")

        fav_story_types = preferences.get('favorite_story_types', [])
        if fav_story_types:
            rag_prompt_parts.append(f"- Preferred Story Types/Genres: {', '.join(fav_story_types)}")

        reading_level = preferences.get('reading_level')
        if reading_level:
            rag_prompt_parts.append(f"- Preferred Reading Level: {reading_level} (e.g., simple vocabulary, complex sentences)")

        interaction_style = preferences.get('interaction_style')
        if interaction_style:
            rag_prompt_parts.append(f"- Preferred Interaction Style for story (if applicable): {interaction_style}")

        if story_history:
            rag_prompt_parts.append("--- RECENT STORY HISTORY (for context, avoid direct repetition unless a sequel is implied by the base_prompt) ---")
            for i, history_item in enumerate(story_history[-3:], 1):
                # Assuming history_item is a string or has a 'title' or 'summary' attribute
                if isinstance(history_item, dict) and 'prompt' in history_item:
                    rag_prompt_parts.append(f"  {i}. Previous Prompt: {history_item['prompt'][:100]}...")
                elif isinstance(history_item, str):
                    rag_prompt_parts.append(f"  {i}. {history_item[:150]}...")
                # Add more sophisticated history formatting if needed
        else:
            rag_prompt_parts.append("- No significant story history available for this user.")
        
        rag_prompt_parts.extend([
            "--- STORY GENERATION INSTRUCTIONS ---",
            "Based on all the above, generate a new, original story that aligns with the base prompt and incorporates the user's preferences.",
            "Ensure the story is engaging, coherent, and suitable for the user's age and reading level.",
            "Focus on creating a positive and imaginative experience."
        ])
        
        return "\n\n".join(rag_prompt_parts)
    
    def record_story_interaction(self, user_id: str, story_data: Dict, interaction_time: int) -> None:
        """Record a story interaction in the user's profile"""
        # Update user profile with story data
        profile_updates = {
            'story': story_data,
            'metrics': {
                'average_engagement_time': interaction_time
            }
        }
        
        self.update_user_profile(user_id, profile_updates)
    
    def get_personalized_recommendations(self, user_id: str, num_recommendations: int = 3) -> List[str]:
        """Generate personalized story recommendations based on user preferences"""
        user_profile = self.get_user_profile(user_id)
        preferences = user_profile['preferences']
        age = user_profile.get('age')
        gender = user_profile.get('gender')
        
        prompt = f"""
        Generate {num_recommendations} personalized story ideas for a child based on these preferences:
        
        - Age: {age if age is not None else 'Not specified'}
        - Gender: {gender if gender else 'Not specified'}
        - Favorite characters: {', '.join(preferences.get('favorite_characters', [])) if preferences.get('favorite_characters') else 'Various characters'}
        - Favorite themes: {', '.join(preferences.get('favorite_themes', [])) if preferences.get('favorite_themes') else 'Various themes'}
        - Favorite story types: {', '.join(preferences.get('favorite_story_types', [])) if preferences.get('favorite_story_types') else 'Various types'}
        - Reading level: {preferences.get('reading_level', 'beginner')}
        
        For each recommendation, provide:
        1. A story title
        2. A brief premise (1-2 sentences)
        3. Why this might appeal to the child based on their preferences
        
        Make sure all recommendations are appropriate for children aged 5-10.
        """
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in recommending children's stories based on preferences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        recommendations = response.choices[0].message.content
        
        # In a real implementation, you would parse this text into structured data
        # For now, we'll return the raw text
        return recommendations