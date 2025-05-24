import openai
from typing import Dict
from config import OPENAI_API_KEY
from agents.story_database import StoryDatabase
# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class JudgeAgent:
    def __init__(self):
        # Initialize all agent components
        self.story_db = StoryDatabase()
        self.evaluation_criteria = {
            'age_appropriate': {
                'language_complexity': 'Simple words and sentence structures',
                'content_safety': 'No violence, scary elements, or adult themes',
                'emotional_impact': 'Positive and uplifting messages'
            },
            'storytelling_quality': {
                'structure': 'Clear beginning, middle, and end',
                'engagement': 'Interesting and captivating narrative',
                'character_development': 'Relatable and well-defined characters'
            },
            'educational_value': {
                'moral_lesson': 'Clear but subtle life lessons',
                'vocabulary': 'Age-appropriate word choices',
                'critical_thinking': 'Encourages reflection and understanding'
            }
        }

    def _get_evaluation_prompt(self, story: str, original_user_prompt: str, story_elements: Dict) -> str:
        return f"""
    You are an expert in children's literature and education. Your task is to evaluate a bedtime story intended for children aged 5 to 10, based on the following:

    1. The original user prompt that inspired the story
    2. The extracted key story elements
    3. The generated story text

    Please assess the story thoroughly according to the criteria below. Your evaluation should be clear, specific, and reference concrete examples from the story where applicable.

    ---

    📝 Original User Prompt:
    {original_user_prompt}

    🧩 Extracted Story Elements:
    - Characters: {story_elements.get('characters', 'N/A')}
    - Setting: {story_elements.get('setting', 'N/A')}
    - Conflict: {story_elements.get('conflict', 'N/A')}
    - Plot Idea: {story_elements.get('plot_idea', 'N/A')}
    - Theme: {story_elements.get('theme', 'N/A')}

    📖 Generated Story:
    {story}

    ---

    🔍 Evaluation Criteria:

    1. 🎯 Correlation with User Input
    - Does the story clearly reflect the prompt and incorporate key elements like characters, setting, and theme?
    - Are proper names, colors, dates, locations, or other keywords from the user input clearly represented?

    2. 👶 Age Appropriateness (5–10 years)
    - Are the themes, concepts, and vocabulary suitable for this age group?
    - Does the story avoid inappropriate content (violence, fear, adult themes)?

    3. 🧱 Structure and Completeness
    - Does the story have a clear beginning, middle, and end?
    - Is the conflict (if present) gently and satisfyingly resolved?
    - Does the story end fully (no unfinished sentences or abrupt cutoffs)?

    4. ⏱️ Length and Pacing
    - Is the length suitable for 3–8 minutes of reading (~300 words)?
    - Does the pacing keep the reader engaged without feeling rushed?

    5. 🗣️ Language and Clarity
    - Is the vocabulary accessible to young readers?
    - Are the sentences easy to follow and age-appropriate?

    6. 🌱 Educational and Emotional Value
    - Does the story offer moral lessons or opportunities for reflection?
    - Does it promote positive traits like kindness, courage, empathy?

    7. 🌈 Engagement and Imagination
    - Is the story interesting, surprising, or imaginative?
    - Will it engage both younger (5–7) and older (8–10) readers?

    8. 🌙 Bedtime Suitability
    - Is the story calming, positive, and appropriate to read before sleep?

    9. 🖼️ Visual Support (if illustrations are implied)
    - Would illustrations enhance understanding and engagement?
    - Are visuals implied appropriate for the story and age?

    10. 🔧 Suggestions for Improvement
    - Provide constructive feedback on how the story can be improved, especially for children in this age group.

    ---

    📌 Finally:
    Please conclude with an overall assessment: Is this story suitable as a bedtime story for children aged 5–10? Why or why not? Summarize in 2–3 sentences.

    Your evaluation should be formatted clearly, with numbered headings matching the criteria above. Make it easy to parse and actionable.
    """

    def evaluate_story(self, story: str, original_user_prompt: str, story_elements: Dict, user_story_id: str) -> Dict:
        # Generate evaluation using OpenAI
        evaluation_prompt = self._get_evaluation_prompt(story, original_user_prompt, story_elements)
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in children's literature and education."},
                {"role": "user", "content": evaluation_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        evaluation_text = response.choices[0].message.content
        
        # Process evaluation results
        appropriateness_output_str = self._check_appropriateness(evaluation_text)
        feedback = self._extract_feedback(evaluation_text)
        
        is_appropriate_val = False # Default
        reason_val = "No specific reason provided."
        score_val = 0 # Default score

        try:
            # Example parsing: "is_appropriate: YES\nreason: Meets all key criteria.\nscore: 9/10"
            lines = appropriateness_output_str.strip().split('\n')
            for line in lines:
                if line.startswith("is_appropriate:"):
                    is_appropriate_val = "YES" in line
                elif line.startswith("reason:"):
                    reason_val = line.split("reason:", 1)[1].strip()
                elif line.startswith("score:"):
                    score_str = line.split("score:", 1)[1].strip().split('/')[0] # Get the '9' from '9/10'
                    try:
                        score_val = int(float(score_str))
                    except ValueError:
                        score_val = 5  # Default to middle score if parsing fails
            if "ERROR" in appropriateness_output_str: # Handle error case from _check_appropriateness
                reason_val = appropriateness_output_str
                is_appropriate_val = False
                score_val = 0

        except Exception as e:
            print(f"Error parsing _check_appropriateness output: {e}\nOutput was: {appropriateness_output_str}")
            reason_val = f"Error parsing appropriateness check: {appropriateness_output_str}"
            is_appropriate_val = False
            score_val = 0
        
        evaluation = {
            'is_appropriate': is_appropriate_val,
           'reason': reason_val,
           'score': score_val,
            'feedback': feedback,
            'full_evaluation': evaluation_text
        }
        # Save the evaluation to the database
        evaluation_id = self.story_db.add_evaluation(user_story_id, evaluation)

        return {
            "evaluation": evaluation,
            "evaluation_id": evaluation_id
        }

    def _extract_feedback(self, evaluation: str) -> str:
        # Extract actionable feedback from the evaluation
        # This is a simplified version - in practice, you might want to use
        # more sophisticated NLP techniques to extract relevant feedback
        # Consider improving this if "Potential improvements:" is not always present or if format varies.
        if 'Potential improvements:' in evaluation:
            return evaluation.split('Potential improvements:')[-1].strip()
        elif 'Suggestions for Improvement:' in evaluation: # From the _get_evaluation_prompt
             return evaluation.split('Suggestions for Improvement:')[-1].strip().split('\n\nFinally, include an overall assessment:')[0].strip()
        return "No specific improvement suggestions found in the evaluation."


    def _check_appropriateness(self, evaluation: str) -> str:
        """
        Analyze the evaluation of a children’s bedtime story and determine
        if the story is appropriate for ages 5–10, and provide a score.

        Parameters:
            evaluation (str): A structured evaluation of the story.

        Returns:
            str: A formatted result:
                - is_appropriate: YES or NO
                - reason: brief explanation
                - score: X/10
        """
        prompt = f"""
        You are a storytelling evaluation agent for children’s bedtime stories (ages 5–10).
        Your task is to analyze the story evaluation below, determine if the story is APPROPRIATE for bedtime reading, and provide a score out of 10.

        Use the following weighted criteria and scoring:

        Total Score: 10 points

        MOST IMPORTANT (Max 6 points total for this section; if any of these fail significantly, the story is NOT appropriate):
            1. Correlation with User Input (Max 2 points):
               • Does the story align with the original prompt and incorporate key elements (characters, setting, conflict, etc.)?
            2. Age Appropriateness (Max 2 points):
               • Are the themes and language suitable for ages 5–10?
            3. Story Structure and Completeness (Max 2 points):
               • Is the story complete with a clear beginning, middle, and end?
               • Is there a satisfying and gentle resolution?
               • Is the story complete? The story should end completely without leaving any half-sentences.

        IMPORTANT (Max 3 points total for this section):
            4. Length and Pacing (Max 1.5 points):
               • Is the story an appropriate length (~300 words or 3–8 minutes)?
               • Is the pacing appropriate?
            5. Language and Clarity (Max 1.5 points):
               • Is the language easy to follow for children?

        LESS IMPORTANT (Max 1 point total for this section):
            6. Educational and Emotional Value (Max 0.3 points)
            7. Engagement and Imagination (Max 0.3 points)
            8. Emotional Tone and Bedtime Suitability (Max 0.4 points)
            (Visual Support and Suggestions for Improvement from the evaluation itself are not directly scored for the story here)

        NOW IMPORTANT: If there is ANY one of the MOST IMPORTANT criteria that receives a 0 score, the story is NOT appropriate, regardless of other scores.

        Now analyze the evaluation below and decide:

        Decision Logic:
        - If one or more MOST IMPORTANT criteria clearly fail (e.g., scores 0 or very low for any of them, like off-topic, inappropriate content, or incomplete structure), the story is NOT appropriate.
        - The final score should reflect the sum of points awarded for each criterion.

        Evaluation:
        {evaluation}

        Respond ONLY in this exact format:
        is_appropriate: YES or NO
        reason: [brief explanation, max 30 words, focusing on the primary failing MOST IMPORTANT criterion if NO, or confirming criteria met if YES]
        score: [X/10, where X is the total score based on the criteria above]
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=150
            )
            output = response.choices[0].message.content.strip()
            return output
        except Exception as e:
            print(f"Error calling OpenAI in _check_appropriateness: {str(e)}")
            return f"is_appropriate: ERROR\nreason: Failed to get appropriateness check due to API error: {str(e)}\nscore: 0/10"