import openai
from typing import Dict
from config import OPENAI_API_KEY

# Configure OpenAI API key
openai.api_key = OPENAI_API_KEY

class JudgeAgent:
    def __init__(self):
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
        Evaluate the following children's bedtime story designed for readers aged 5 to 10.
        The story was generated based on the user's original prompt and extracted story elements.

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

        Please assess the story using the criteria below. Provide specific feedback for each aspect, including examples or reasoning where relevant:

        1. Correlation with User Input:
        - How well does the story align with the original user prompt?
        - Does the story effectively incorporate the extracted story elements (characters, setting, theme, etc.)?

        2. Age Appropriateness:
        - Are the themes, language, and concepts suitable for children aged 5–10?

        3. Story Structure and Completeness:
        - Does the story have a clear beginning, middle, and end?
        - Is the conflict (if any) resolved in a gentle and satisfying way?

        4. Length and Pacing:
        - Is the story an appropriate length to maintain attention (3–8 minutes), at most 300 words?
        - Does the pacing feel too slow or too rushed?

        5. Language and Clarity:
        - Are vocabulary and sentence structure age-appropriate?
        - Is the story easy to follow and understand?

        6. Educational and Emotional Value:
        - Does the story promote positive values such as kindness, empathy, or perseverance?
        - Are there opportunities for learning or emotional growth?

        7. Engagement and Imagination:
        - Is the story engaging and likely to spark curiosity or imagination?
        - Does it capture the attention of both younger (5–7) and older (8–10) children?

        8. Emotional Tone and Bedtime Suitability:
        - Does the story end on a calming or comforting note?
        - Is it appropriate for bedtime reading (non-frightening, relaxing)?

        9. Visual Support (if applicable):
        - If the story includes or implies illustrations, are they age-appropriate and supportive of the text?

        10. Suggestions for Improvement:
        - Provide specific, constructive feedback on how the story could be enhanced for this age group, considering its alignment with the user's input and general storytelling quality.

        Finally, include an overall assessment: Is this story suitable as a bedtime story for children aged 5–10, considering all the above points, especially its relevance to the user's request? Why or why not?
        """

    def evaluate_story(self, story: str, original_user_prompt: str, story_elements: Dict) -> Dict:
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

        return {
            'is_appropriate': is_appropriate_val,
            'reason': reason_val,
            'score': score_val,
            'feedback': feedback,
            'full_evaluation': evaluation_text
        }

    # Removed the first (red_flags based) _check_appropriateness method

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

        IMPORTANT (Max 3 points total for this section):
            4. Length and Pacing (Max 1.5 points):
               • Is the story an appropriate length (~300 words or 3–8 minutes)?
               • Is the pacing appropriate?
            5. Language and Clarity (Max 1.5 points):
               • Is the language easy to follow for children?

        LESS IMPORTANT (Max 1 point total for this section):
            6. Educational and Emotional Value (Max 0.25 points)
            7. Engagement and Imagination (Max 0.25 points)
            8. Emotional Tone and Bedtime Suitability (Max 0.25 points)
            9. Visual Support (optional, Max 0.15 points if applicable, otherwise 0)
            10. Suggestions for Improvement (Max 0.1 points - this is about the quality of the evaluation's suggestions, not the story itself, so perhaps less relevant for story score. Let's re-evaluate this point. For now, let's assign points to the story's qualities)
            
        Revised LESS IMPORTANT (Max 1 point total for this section):
            6. Educational and Emotional Value (Max 0.3 points)
            7. Engagement and Imagination (Max 0.3 points)
            8. Emotional Tone and Bedtime Suitability (Max 0.4 points)
            (Visual Support and Suggestions for Improvement from the evaluation itself are not directly scored for the story here)


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
            # Updated to the new OpenAI SDK syntax
            response = openai.chat.completions.create(
                model="gpt-4", # Consider gpt-3.5-turbo for cost/speed if quality is sufficient
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2, # Lowered temperature for more deterministic output
                max_tokens=150 # Increased max_tokens slightly for score and reason
            )
            output = response.choices[0].message.content.strip()
            return output
        except Exception as e:
            # Log the error for debugging
            print(f"Error calling OpenAI in _check_appropriateness: {str(e)}")
            return f"is_appropriate: ERROR\nreason: Failed to get appropriateness check due to API error: {str(e)}\nscore: 0/10"