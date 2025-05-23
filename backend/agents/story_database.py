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

    def _load_json(self, path: Path) -> List:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _save_json(self, path: Path, data: List) -> None:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

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