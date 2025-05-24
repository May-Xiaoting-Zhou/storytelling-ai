from typing import Dict
from datetime import datetime
from agents.story_database import StoryDatabase
import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

class FeedbackAgent:
    def __init__(self):
        self.story_db = StoryDatabase()
        self.interaction_metrics = {
            'engagement': {
                'time_spent': 0,
                'follow_up_questions': 0,
                'user_reactions': []
            },
            'story_impact': {
                'emotional_response': None,
                'comprehension': None,
                'enjoyment_level': None
            },
            'learning_outcomes': {
                'moral_understanding': None,
                'vocabulary_growth': None,
                'critical_thinking': None
            }
        }
    
    def provide_feedback(self, feedback: str, story: str, original_user_prompt: str, story_elements: Dict, story_evaluation_id: str) -> str:
        """
        Processes raw feedback into a summarized message suitable for reflection,
        recommendations, or reporting purposes.
        
        Parameters:
        - feedback (str): Raw text-based feedback from a reviewer or educator.
        - story (str): The story that was evaluated.
        - original_user_prompt (str): The user's original prompt for the story.
        - story_elements (Dict): The extracted elements from the user's prompt.

        Returns:
        - feedback_message (str): A clear, concise, actionable feedback summary.
        """

        prompt = f"""
    You are a feedback summarization assistant for children's stories.

    The following story was generated and then reviewed:

    Original User Prompt:
    {original_user_prompt}

    Extracted Story Elements:
    Characters: {story_elements.get('characters', 'N/A')}
    Setting: {story_elements.get('setting', 'N/A')}
    Conflict: {story_elements.get('conflict', 'N/A')}
    Plot Idea: {story_elements.get('plot_idea', 'N/A')}
    Theme: {story_elements.get('theme', 'N/A')}

    Generated Story:
    {story}

    Given the detailed reviewer feedback below, produce a clear and concise feedback message that:
    - Highlights the key strengths of the story, especially in relation to the user's prompt and desired elements.
    - Lists 3-4 specific, actionable suggestions for improvement, focusing on elements that would increase the story's evaluation score.
    - Prioritize improvements to story structure, age-appropriateness, and alignment with the user's prompt as these have the highest impact on evaluation scores.
    - Uses a tone that is encouraging, professional, and easy to understand by educators, writers, or parents.
    - Keep the message under 250 words.

    ### Reviewer Feedback:
    {feedback}

    Now generate the feedback message.
    """

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You summarize and structure educational feedback for children's storytelling."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        feedback_message = response.choices[0].message.content.strip()
        
        # Save the feedback to the database
        feedback_id = self.story_db.add_evaluation_feedback_log(story_evaluation_id, feedback_message)

        return {
            "feedback_message": feedback_message, 
            "feedback_id": feedback_id
            }

    def store_interaction(self, prompt: str, story: str, evaluation: Dict) -> None:
        # Store interaction data
        interaction_data = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'story': story,
            'evaluation': evaluation,
            'metrics': self.interaction_metrics.copy()
        }
        self.story_db.store_interaction(interaction_data)

    def update_metrics(self, interaction_type: str, data: Dict) -> None:
        # Update interaction metrics based on user behavior
        if interaction_type == 'engagement':
            self.interaction_metrics['engagement']['time_spent'] += data.get('time_spent', 0)
            self.interaction_metrics['engagement']['follow_up_questions'] += 1
            if 'reaction' in data:
                self.interaction_metrics['engagement']['user_reactions'].append(data['reaction'])

        elif interaction_type == 'impact':
            self.interaction_metrics['story_impact'].update({
                k: v for k, v in data.items()
                if k in self.interaction_metrics['story_impact']
            })

        elif interaction_type == 'learning':
            self.interaction_metrics['learning_outcomes'].update({
                k: v for k, v in data.items()
                if k in self.interaction_metrics['learning_outcomes']
            })

    def get_user_profile(self, user_id: str) -> Dict:
        # Retrieve and analyze user's interaction history
        interactions = self.story_db.get_user_interactions(user_id)
        
        profile = {
            'preferred_themes': self._analyze_preferences(interactions, 'theme'),
            'engagement_level': self._calculate_engagement(interactions),
            'learning_progress': self._assess_learning(interactions),
            'recommended_topics': self._generate_recommendations(interactions)
        }
        
        return profile

    def _analyze_preferences(self, interactions: list, aspect: str) -> Dict:
        # Analyze user preferences based on interaction history
        preferences = {}
        for interaction in interactions:
            if aspect in interaction:
                theme = interaction[aspect]
                preferences[theme] = preferences.get(theme, 0) + 1
        return preferences

    def _calculate_engagement(self, interactions: list) -> float:
        # Calculate user engagement score
        if not interactions:
            return 0.0
        
        total_score = 0
        for interaction in interactions:
            metrics = interaction.get('metrics', {})
            engagement = metrics.get('engagement', {})
            
            # Calculate engagement score based on multiple factors
            score = (
                engagement.get('time_spent', 0) * 0.4 +
                engagement.get('follow_up_questions', 0) * 0.3 +
                len(engagement.get('user_reactions', [])) * 0.3
            )
            total_score += score
        
        return total_score / len(interactions)

    def _assess_learning(self, interactions: list) -> Dict:
        # Assess learning progress across different dimensions
        if not interactions:
            return {}
        
        learning_scores = {
            'moral_understanding': 0,
            'vocabulary_growth': 0,
            'critical_thinking': 0
        }
        
        for interaction in interactions:
            metrics = interaction.get('metrics', {})
            learning = metrics.get('learning_outcomes', {})
            
            for aspect in learning_scores:
                if learning.get(aspect) is not None:
                    learning_scores[aspect] += learning[aspect]
        
        # Calculate averages
        for aspect in learning_scores:
            learning_scores[aspect] /= len(interactions)
        
        return learning_scores

    def _generate_recommendations(self, interactions: list) -> list:
        # Generate personalized story recommendations
        preferences = self._analyze_preferences(interactions, 'theme')
        engagement = self._calculate_engagement(interactions)
        learning = self._assess_learning(interactions)
        
        # Simple recommendation logic - can be enhanced with more sophisticated algorithms
        recommendations = []
        if engagement < 0.5:
            recommendations.append('more interactive stories')
        if learning['vocabulary_growth'] < 0.6:
            recommendations.append('stories with new vocabulary')
        if learning['critical_thinking'] < 0.7:
            recommendations.append('problem-solving stories')
        
        return recommendations