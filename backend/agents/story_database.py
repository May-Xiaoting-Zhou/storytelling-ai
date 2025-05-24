from typing import List, Dict
import json
import os
from datetime import datetime
from pathlib import Path

class StoryDatabase:
    def __init__(self):
        self.db_path = Path('database')
        self.stories_path = self.db_path / 'stories.json'
        self.interactions_path = self.db_path / 'interactions.json'
        self.conversations_path = self.db_path / 'conversations.json'
        self.user_stories_path = self.db_path / 'user_stories.json'
        self.story_evaluations_path = self.db_path / 'story_evaluations.json'
        self.story_evaluation_feedback_log_path = self.db_path / 'story_evaluation_feedback_log.json' # Added this line
        self._initialize_database()

    def _initialize_database(self) -> None:
        # Create database directory if it doesn't exist
        self.db_path.mkdir(exist_ok=True)
        
        # Initialize stories file
        if not self.stories_path.exists():
            self._save_json(self.stories_path, [])
        
        # Initialize interactions file
        if not self.interactions_path.exists():
            self._save_json(self.interactions_path, [])

        # Initialize conversations file
        if not self.conversations_path.exists():
            self._save_json(self.conversations_path, [])

        # Initialize user_stories file
        if not self.user_stories_path.exists():
            self._save_json(self.user_stories_path, [])

        # Initialize story_evaluations file
        if not self.story_evaluations_path.exists():
            self._save_json(self.story_evaluations_path, [])

        # Initialize story_evaluation_feedback_log file
        if not self.story_evaluation_feedback_log_path.exists(): # Added this block
            self._save_json(self.story_evaluation_feedback_log_path, [])

    def _load_json(self, path: Path) -> List:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _save_json(self, path: Path, data: List) -> None:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_story(self, prompt: str, story_text: str, metadata: Dict) -> int:
        stories = self._load_json(self.stories_path)
        
        story_id = len(stories) + 1
        story_data = {
            'id': story_id,
            'prompt': prompt,
            'story': story_text,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata
        }
        
        stories.append(story_data)
        self._save_json(self.stories_path, stories)
        return story_id

    def add_user_story(self, prompt: str, user_id: str, story_id: int, intent: str) -> int:
        user_stories = self._load_json(self.user_stories_path)
        
        user_story_id = len(user_stories) + 1
        user_story_data = {
            'id': user_story_id,
            'user_id': user_id,
            'story_id': story_id,
            'prompt': prompt,
            'intent': intent,
            'timestamp': datetime.now().isoformat()
        }
        
        user_stories.append(user_story_data)
        self._save_json(self.user_stories_path, user_stories)
        return user_story_id

    def add_evaluation(self, user_story_id: int, evaluation: Dict) -> int:
        evaluations = self._load_json(self.story_evaluations_path)
        
        evaluation_id = len(evaluations) + 1
        evaluation_data = {
            'id': evaluation_id,
            'user_story_id': user_story_id,
            'evaluations': evaluation, # Storing the passed evaluation dictionary directly
            'timestamp': datetime.now().isoformat()
        }
        
        evaluations.append(evaluation_data)
        self._save_json(self.story_evaluations_path, evaluations)
        return evaluation_id

    def add_evaluation_feedback_log(self, story_evaluation_id: int, feedback_message: str) -> int:
        feedback_logs = self._load_json(self.story_evaluation_feedback_log_path)
        
        feedback_id = len(feedback_logs) + 1
        feedback_data = {
            'id': feedback_id,
            'story_evaluations_id': story_evaluation_id,
            'feedbacks': feedback_message, # Assuming feedback_message is a string
            'timestamp': datetime.now().isoformat()
        }
        
        feedback_logs.append(feedback_data)
        self._save_json(self.story_evaluation_feedback_log_path, feedback_logs)
        return feedback_id

    def store_story(self, prompt: str, story: str) -> None:
        stories = self._load_json(self.stories_path)
        
        story_data = {
            'id': len(stories) + 1,
            'prompt': prompt,
            'story': story,
            'timestamp': datetime.now().isoformat(),
            'metadata': self._extract_metadata(story)
        }
        
        stories.append(story_data)
        self._save_json(self.stories_path, stories)

    def get_similar_stories(self, prompt: str, limit: int = 3) -> List[Dict]:
        stories = self._load_json(self.stories_path)
        
        # Simple similarity scoring based on prompt keywords
        # In a production environment, use proper embedding and similarity search
        prompt_keywords = set(prompt.lower().split())
        
        scored_stories = []
        for story in stories:
            story_keywords = set(story['prompt'].lower().split())
            similarity_score = len(prompt_keywords.intersection(story_keywords))
            scored_stories.append((similarity_score, story))
        
        # Sort by similarity score and return top matches
        scored_stories.sort(key=lambda x: x[0], reverse=True)
        return [story for _, story in scored_stories[:limit]]

    def store_interaction(self, interaction_data: Dict) -> None:
        interactions = self._load_json(self.interactions_path)
        
        interaction_data['id'] = len(interactions) + 1
        interactions.append(interaction_data)
        
        self._save_json(self.interactions_path, interactions)

    def get_user_interactions(self, user_id: str) -> List[Dict]:
        interactions = self._load_json(self.interactions_path)
        return [i for i in interactions if i.get('user_id') == user_id]

    def get_conversations_by_user_id(self, user_id: str) -> List[Dict]: # Added this method
        conversations = self._load_json(self.conversations_path)
        return [c for c in conversations if c.get('user_id') == user_id]

    def _extract_metadata(self, story: str) -> Dict:
        # Extract key information from the story
        # This is a simplified version - in practice, use NLP techniques
        metadata = {
            'length': len(story),
            'complexity': self._estimate_complexity(story),
            'theme': self._identify_theme(story),
            'moral': self._extract_moral(story)
        }
        return metadata

    def _estimate_complexity(self, text: str) -> float:
        # Simple complexity estimation based on average word length
        words = text.split()
        if not words:
            return 0.0
        return sum(len(word) for word in words) / len(words)

    def _identify_theme(self, story: str) -> str:
        # Simple theme identification based on keywords
        # In practice, use more sophisticated NLP techniques
        themes = {
            'adventure': ['journey', 'quest', 'explore'],
            'friendship': ['friend', 'together', 'help'],
            'family': ['family', 'parent', 'sibling'],
            'learning': ['learn', 'school', 'teach'],
            'nature': ['animal', 'forest', 'garden']
        }
        
        story_lower = story.lower()
        theme_scores = {}
        
        for theme, keywords in themes.items():
            score = sum(story_lower.count(keyword) for keyword in keywords)
            theme_scores[theme] = score
        
        return max(theme_scores.items(), key=lambda x: x[1])[0]

    def _extract_moral(self, story: str) -> str:
        # Simple moral extraction based on common phrases
        # In practice, use more sophisticated NLP techniques
        moral_indicators = [
            'learned that',
            'moral of the story',
            'realized that',
            'understood that'
        ]
        
        story_lower = story.lower()
        for indicator in moral_indicators:
            if indicator in story_lower:
                # Extract the sentence containing the moral
                sentences = story.split('.')
                for sentence in sentences:
                    if indicator in sentence.lower():
                        return sentence.strip()
        
        return 'No explicit moral found'