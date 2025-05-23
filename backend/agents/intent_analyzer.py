from typing import Dict, Any
import openai
import re
import json
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

SYSTEM_PROMPT = """
You are a story analysis agent. Given a short prompt or idea, extract the following narrative elements:
1. Characters: Name and describe each main character.
2. Setting: Describe where and when the story likely takes place.
3. Conflict: Identify the main problem or challenge.
4. Plot Idea: Provide a one-sentence summary of the possible plot.
5. Theme: List the core themes or lessons (e.g., friendship, courage).

If not explicitly stated, make creative inferences. Return results in JSON format as shown below:

{
  "characters": [
    { "name": "Alice", "description": "a curious girl" },
    { "name": "Bob", "description": "her best friend, a talking cat" }
  ],
  "setting": "a peaceful village near a magical forest",
  "conflict": "They must find a hidden artifact to save their village",
  "plot_idea": "Alice and Bob journey through an enchanted forest to find a lost treasure that holds the key to their village's future.",
  "theme": ["friendship", "bravery", "teamwork"]
}
"""

class IntentAnalyzerAgent:
    def __init__(self):
        self.story_keywords = ['story', 'tale', 'fairy tale', 'once upon', 'character', 'plot', 'adventure']
        self.intent_keywords = {
            'new_story': ['tell me a story', 'new story', 'create a story', 'story about', 'start a story'],
            'change_story': ['change the story', 'another story', 'different version', 'modify story'],
            'update_story': ['add', 'continue', 'next', 'what happens next', 'extend the story', 'add one', 'include']
        }

    def analyze_intent(self, prompt: str) -> Dict[str, Any]:
        prompt_lower = prompt.lower()

        # First, detect if this is even a storytelling request
        if not any(keyword in prompt_lower for keyword in self.story_keywords):
            return {
                'intent_type': 'non_story',
                'message': "I’m a storytelling assistant, happy to tell you a story!"
            }

        # Detect intent
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    return {
                        'intent_type': intent,
                        'confidence': 0.9,
                        'detected_keyword': keyword
                    }

        # Default to new story if unclear
        return {
            'intent_type': 'new_story',
            'confidence': 0.5,
            'detected_keyword': None
        }

    def analyze_story_prompt(self, user_prompt: str) -> Dict[str, Any]:
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except Exception as e:
            return {"error": str(e)}

    def classify_prompt(self, user_prompt: str) -> Dict[str, Any]:
        intent_result = self.analyze_intent(user_prompt)

        # Non-story prompts
        if intent_result['intent_type'] == 'non_story':
            return {
                "intent": "non_story",
                "message": intent_result["message"],
                "action": "stop"
            }

        # Story-related prompts: analyze elements
        story_elements = self.analyze_story_prompt(user_prompt)

        # If parsing failed
        if "error" in story_elements:
            return {
                "intent": intent_result['intent_type'],
                "message": "Oops! I couldn’t quite understand that. Could you rephrase your story idea?",
                "error": story_elements["error"],
                "action": "stop"
            }

        # Check if basic story info exists
        has_essentials = bool(
            story_elements.get("characters") or
            story_elements.get("setting") or
            story_elements.get("conflict") or
            story_elements.get("plot_idea")
        )

        if not has_essentials:
            return {
                "intent": "new_story",
                "message": "What kind of story would you like? For example, a magical adventure, a mystery in space, or a story about friendship?",
                "action": "clarify"
            }

        # Everything looks good
        return {
            "intent": intent_result["intent_type"],
            "story_elements": story_elements,
            "action": "proceed"
        }

    def extract_story_input_for_generation(self, elements: Dict[str, Any]) -> Dict:
        if "error" in elements:
            return {"error": elements["error"]}
        return {
            "characters": [
                {
                    "name": c["name"],
                    "description": c["description"]
                } for c in elements.get("characters", [])
            ],
            "setting": elements.get("setting", ""),
            "conflict": elements.get("conflict", ""),
            "plot_idea": elements.get("plot_idea", ""),
            "themes": elements.get("theme", [])
        }

    def update_story_elements(self, story: str, original_user_prompt: str, original_story_elements: Dict[str, Any], feedback_message: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates story elements based on the story, feedback, and evaluation to guide improvement.
        """
        update_prompt_template = """
You are a story refinement agent. Given an original story, its extracted elements, user prompt, feedback, and evaluation, your task is to update the story elements to address the feedback and improve the story.

Original Story:
{story}

Original User Prompt:
{original_user_prompt}

Original Story Elements:
{original_story_elements_json}

Feedback Message (summary of issues/suggestions):
{feedback_message}

Full Evaluation (detailed assessment, including 'feedback' and 'reason' for score):
{evaluation_json}

Current Evaluation Score: {score}/10

Based on all the above, revise the 'Original Story Elements' to guide the generation of an improved story.
The revised elements should directly address the feedback and evaluation to increase the story's score.

Focus on changes to characters, setting, conflict, plot idea, and themes that would lead to a better story.
Pay special attention to:
1. Alignment with the original user prompt (highest impact on score)
2. Age-appropriateness for children 5-10 (highest impact on score)
3. Story structure and completeness (highest impact on score)
4. Length, pacing, and language clarity (medium impact on score)
5. Educational value, engagement, and emotional tone (lower impact on score)

Return the updated story elements in the following JSON format:

{{
  "characters": [
    {{ "name": "...", "description": "..." }}
  ],
  "setting": "...",
  "conflict": "...",
  "plot_idea": "...",
  "theme": ["...", "..."]
}}

If an element does not need changes, keep it as is. If new elements are suggested by the feedback, incorporate them.
Ensure the output is a valid JSON object.
"""
        
        try:
            # Prepare the inputs for the prompt
            original_story_elements_json = json.dumps(original_story_elements, indent=2)
            evaluation_json = json.dumps(evaluation, indent=2)
            score = evaluation.get('score', 0)

            prompt_content = update_prompt_template.format(
                story=story,
                original_user_prompt=original_user_prompt,
                original_story_elements_json=original_story_elements_json,
                feedback_message=feedback_message,
                evaluation_json=evaluation_json,
                score=score
            )

            response = openai.chat.completions.create(
                model="gpt-4", # Upgraded to GPT-4 for better story element refinement
                messages=[
                    {"role": "system", "content": "You are an expert in refining story elements based on feedback. Respond in JSON format."},
                    {"role": "user", "content": prompt_content}
                ],
                response_format={"type": "json_object"}, # Ensure JSON output if using compatible models
                temperature=0.5,
            )
            
            content = response.choices[0].message.content.strip()
            updated_elements = json.loads(content)
            return updated_elements

        except Exception as e:
            print(f"Error updating story elements: {e}") # Log the error
            # Fallback to original elements if update fails
            return original_story_elements