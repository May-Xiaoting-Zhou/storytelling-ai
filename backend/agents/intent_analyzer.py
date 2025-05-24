from typing import Dict, Any, Optional, List
import openai
import re # Not used, can be removed
import json
from config import OPENAI_API_KEY
from .story_database import StoryDatabase # Assuming story_database.py is in the same directory

# openai.api_key = OPENAI_API_KEY # Handled by OpenAI client initialization

class IntentAnalyzer:
    def __init__(self):
        self.story_db = StoryDatabase()
        # Ensure OPENAI_API_KEY is loaded correctly, e.g., from environment or config file
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def _get_last_story_and_conversation(self, user_id: str) -> Dict[str, Any]:
        """Helper to fetch last story and conversation for context."""
        # This is a placeholder. You'll need to implement robust data fetching.
        # Potentially using methods from your StoryDatabase class.
        # This method seems largely okay for fetching context.
        # Ensure paths like self.story_db.user_stories_path are correctly defined in StoryDatabase
        last_story_text = ""
        conversation_history = []
        last_user_story_prompt = ""
        previous_story_elements = {}

        try:
            user_stories_path = self.story_db.user_stories_path
            user_stories = self.story_db._load_json(user_stories_path)
            
            user_specific_stories = [us for us in user_stories if us.get('user_id') == user_id]
            if user_specific_stories:
                user_specific_stories.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                last_user_story_entry = user_specific_stories[0]
                last_story_id = last_user_story_entry.get('story_id')
                last_user_story_prompt = last_user_story_entry.get('prompt', '')
                # Attempt to get previous story elements if available with the user_story entry
                # This assumes story_elements might have been saved with user_stories or can be inferred
                # For now, we'll rely on the LLM to re-extract if changing/updating.

                stories_path = self.story_db.stories_path
                all_stories = self.story_db._load_json(stories_path)
                last_story_data = next((s for s in all_stories if s.get('id') == last_story_id), None)
                if last_story_data:
                    last_story_text = last_story_data.get('story', '')
                    # Potentially load metadata if it contains structured story elements from the past
                    # previous_story_elements = last_story_data.get('metadata', {}).get('story_elements', {})

            conversations_path = self.story_db.conversations_path
            all_conversations = self.story_db._load_json(conversations_path)
            user_conversations = [c for c in all_conversations if c.get('user_id') == user_id]
            if user_conversations:
                user_conversations.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
                if user_conversations[0].get('messages'):
                    conversation_history = user_conversations[0].get('messages', [])

        except Exception as e:
            print(f"Error fetching context in IntentAnalyzer: {e}")

        return {
            "last_story_text": last_story_text,
            "conversation_history": conversation_history,
            "last_user_story_prompt": last_user_story_prompt,
            "previous_story_elements": previous_story_elements # Added for potential future use
        }

    def classify_prompt(self, user_prompt: str, user_id: str) -> Dict[str, Any]:
        historical_context = self._get_last_story_and_conversation(user_id)
        last_story_text = historical_context.get("last_story_text", "")
        conversation_history_messages = historical_context.get("conversation_history", [])
        last_user_story_prompt = historical_context.get("last_user_story_prompt", "")
        # previous_story_elements = historical_context.get("previous_story_elements", {})

        formatted_conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history_messages[-5:]])

        llm_prompt = f"""
Analyze the user's prompt for a storytelling application. User ID: {user_id}

CONTEXT:
1. Previous Conversation (last 5 turns):
{formatted_conversation}

2. Last Story Prompt from User: "{last_user_story_prompt}"

3. Last Story Text Generated:
\"\"\"{last_story_text}\"\"\"

CURRENT USER PROMPT: "{user_prompt}"

TASK:
Determine the user's intent and extract relevant information. Possible intents are 'new_story', 'change_story', 'update_story', 'non_story'.

INTENT-SPECIFIC INSTRUCTIONS:

- If 'new_story':
  - "introduction_context": Briefly summarize the new story request from the CURRENT USER PROMPT.
  - "story_elements": Extract key elements (characters, setting, plot_idea, theme, conflict, moral_lesson, tone, length_preference, target_age_group) for the new story SOLELY from the CURRENT USER PROMPT. If an element is not mentioned, omit it.

- If 'change_story': (User wants significant alterations to the *previous* story or a variation on its theme)
  - "introduction_context": Clearly describe what major aspects of the *previous story* (CONTEXT item 3) the user wants to change, based on the CURRENT USER PROMPT. Example: "User wants to change the main character and the ending of the previous story."
  - "story_elements": Based on the CURRENT USER PROMPT, identify the *new or significantly modified* story elements. If the user says "change the setting to a castle", the setting element should be "castle". Carry over elements from the previous story ONLY if they are clearly intended to remain and are compatible with the requested changes. Prioritize elements explicitly mentioned for change.

- If 'update_story': (User wants minor modifications, additions, or clarifications to the *previous* story, or is providing feedback)
  - "introduction_context": Detail the specific minor changes, additions, or clarifications requested for the *previous story* (CONTEXT item 3), based on the CURRENT USER PROMPT. Example: "User wants to add a friendly dog to the story and make the ending happier."
  - "story_elements": Identify story elements that need to be updated or added. These are usually minor adjustments. For example, if the user says "add a character named Sparky", the characters element should reflect this addition. Elements not mentioned for update can be assumed to carry over from the previous story, but focus on extracting what's new or changed in the CURRENT USER PROMPT.

- If 'non_story': (Prompt is not related to storytelling, e.g., greeting, off-topic)
  - "introduction_context": Use the user's prompt itself or a generic message like "User's input is not story-related."
  - "story_elements": Should be an empty object {{}}.

OUTPUT FORMAT:
Return your analysis as a SINGLE VALID JSON object with these fields:
- "intent_type": (string) 'new_story', 'change_story', 'update_story', or 'non_story'.
- "introduction_context": (string) As per instructions above.
- "story_elements": (object) Extracted/regenerated story elements as per instructions. Example: {{"characters": ["dragon", "princess"], "setting": "magical forest"}}. Omit unmentioned elements.
- "error_message": (string, optional) If you cannot reliably determine the intent or parse elements.
"""
        try:
            # Using response_format for structured JSON output if available and supported by the model version
            response_params = {
                "model": "gpt-3.5-turbo-0125", # Or a model that supports JSON mode like gpt-4-turbo-preview
                "messages": [
                    {"role": "system", "content": "You are an expert intent analysis assistant for a children's storytelling app. Analyze the user's prompt and context carefully and return a valid JSON object according to the specified format and instructions."},
                    {"role": "user", "content": llm_prompt}
                ]
            }
            # Check if the model supports response_format, newer models do.
            # For gpt-3.5-turbo-0125 and later, or gpt-4-turbo-preview and later:
            if "0125" in response_params["model"] or "turbo-preview" in response_params["model"] or "gpt-4" in response_params["model"]:
                 response_params["response_format"] = { "type": "json_object" }

            completion = self.openai_client.chat.completions.create(**response_params)
            llm_analysis_str = completion.choices[0].message.content
            
            # Basic validation and parsing
            try:
                llm_analysis = json.loads(llm_analysis_str)
            except json.JSONDecodeError as json_e:
                print(f"LLM output was not valid JSON: {llm_analysis_str}. Error: {json_e}")
                # Fallback or re-try logic could be added here
                # For now, return an error state
                return {
                    "intent": "error", 
                    "message": "Failed to parse AI understanding.", 
                    "action": "stop", 
                    "context": "LLM output was not valid JSON.",
                    "story_elements": {}
                }

            intent_type = llm_analysis.get("intent_type", "non_story")
            introduction_context = llm_analysis.get("introduction_context", "Could not determine context.")
            story_elements = llm_analysis.get("story_elements", {})
            if not isinstance(story_elements, dict):
                print(f"Warning: story_elements from LLM was not a dict: {story_elements}")
                story_elements = {} # Ensure it's a dict
            error_message_from_llm = llm_analysis.get("error_message")

        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return {
                "intent": "error",
                "message": "Sorry, I had trouble understanding your request due to an internal error.",
                "action": "stop",
                "context": str(e),
                "story_elements": {}
            }

        # 4. Process LLM response and determine action/message
        action = "continue"
        message = "Got it!"

        if error_message_from_llm:
            intent_type = llm_analysis.get("intent_type", "error") # Use LLM's intent if error is specific
            message = error_message_from_llm
            action = "stop"
        elif intent_type == 'non_story':
            message = introduction_context # Or a predefined non-story message
            action = "stop"
        elif intent_type in ['new_story', 'change_story']:
            has_essentials = bool(
                story_elements.get("characters") or
                story_elements.get("setting") or
                story_elements.get("plot_idea")
            )
            if not has_essentials:
                action = "request_more_info"
                message = "That's an interesting idea! Could you tell me a bit more about the characters, setting, or what happens in the story?"
            else:
                message = "Great, I'll get started on that story!"
        elif intent_type == 'update_story':
            # For updates, context is key. Assume essentials are less critical if context is clear.
            message = "Okay, I'll update the story with those changes."
        else: # Should not happen if LLM follows intent list
            intent_type = "error"
            message = "I'm not quite sure how to handle that request."
            action = "stop"

        final_response = {
            "intent": intent_type,
            "message": message,
            "action": action,
            "context": introduction_context,
            "story_elements": story_elements
        }
        if error_message_from_llm: # Ensure error from LLM is passed if it exists
            final_response["error_message_from_llm"] = error_message_from_llm

        return final_response

    def extract_story_elements(self, prompt: str) -> Dict[str, Any]:
        # This is a placeholder for extracting elements without LLM if needed
        # For now, we rely on the LLM in classify_prompt
        return {}

    def analyze_feedback(self, feedback: str) -> Dict[str, Any]:
        # This is a placeholder for analyzing feedback specifically
        # For now, feedback is handled within the 'update_story' intent via LLM
        return {}

    def parse_story_elements(self, llm_output: Dict[str, Any]) -> Dict[str, Any]:
        # This is a placeholder for parsing LLM output if needed separately
        # For now, we assume the LLM directly provides the 'story_elements' object
        return llm_output.get("story_elements", {})

    def determine_action(self, intent_type: str, story_elements: Dict[str, Any]) -> str:
        # This is a placeholder for determining action if needed separately
        # For now, action is determined within classify_prompt
        if intent_type in ['new_story', 'change_story'] and not story_elements:
            return "request_more_info"
        elif intent_type == 'non_story':
            return "stop"
        else:
            return "continue"

    def get_introduction_context(self, intent_type: str, user_prompt: str, llm_analysis: Dict[str, Any]) -> str:
        # This is a placeholder for getting introduction context if needed separately
        # For now, introduction_context is provided by the LLM
        return llm_analysis.get("introduction_context", user_prompt)

    def get_original_story_elements(self, user_id: str, story_id: str) -> Dict[str, Any]:
        """Fetches the original story elements used to generate a specific story."""
        try:
            user_stories_path = self.story_db.user_stories_path
            user_stories = self.story_db._load_json(user_stories_path)
            
            user_story_entry = next((us for us in user_stories if us.get('user_id') == user_id and us.get('story_id') == story_id), None)
            
            if user_story_entry:
                # Assuming the original prompt contains the elements or they are stored elsewhere
                # For now, let's return the prompt and assume elements can be re-extracted or were stored.
                # A more robust implementation would store elements with the user_story entry.
                return {"prompt": user_story_entry.get('prompt', ''), "intent": user_story_entry.get('intent', '')}
            else:
                return {}
        except Exception as e:
            print(f"Error fetching original story elements: {e}")
            return {}

    def get_story_evaluation_and_feedback(self, user_story_id: str) -> Dict[str, Any]:
        """Fetches the latest evaluation and feedback for a given user_story_id."""
        evaluation = None
        feedback = []
        try:
            # Fetch evaluation
            evaluations_path = self.story_db.story_evaluations_path
            all_evaluations = self.story_db._load_json(evaluations_path)
            user_story_evaluations = [e for e in all_evaluations if e.get('user_story_id') == user_story_id]
            if user_story_evaluations:
                # Assuming the latest evaluation is the one we need
                evaluation = user_story_evaluations[-1].get('evaluation') # Get the evaluation dictionary

            # Fetch feedback logs
            feedback_log_path = self.story_db.story_evaluation_feedback_log_path
            all_feedback_logs = self.story_db._load_json(feedback_log_path)
            user_story_feedback_logs = [f for f in all_feedback_logs if f.get('story_evaluations_id') == user_story_id] # Assuming story_evaluations_id links to user_story_id
            if user_story_feedback_logs:
                # Collect all feedback messages
                feedback = [log.get('feedback_message') for log in user_story_feedback_logs]

        except Exception as e:
            print(f"Error fetching evaluation and feedback: {e}")

        return {
            "evaluation": evaluation,
            "feedback": feedback
        }

    def get_story_elements_for_regeneration(self, user_id: str, user_story_id: str) -> Dict[str, Any]:
        """Combines original story elements, evaluation, and feedback for regeneration."""
        # 1. Get original story elements (prompt, intent)
        original_elements = self.get_original_story_elements(user_id, user_story_id)
        original_prompt = original_elements.get('prompt', '')
        original_intent = original_elements.get('intent', '')

        # 2. Get evaluation and feedback
        evaluation_feedback = self.get_story_evaluation_and_feedback(user_story_id)
        evaluation = evaluation_feedback.get('evaluation')
        feedback = evaluation_feedback.get('feedback')

        # 3. Combine information
        # This part needs refinement based on how you want to use evaluation/feedback
        # For now, let's return all relevant info
        combined_elements = {
            "original_prompt": original_prompt,
            "original_intent": original_intent,
            "evaluation": evaluation,
            "feedback": feedback
        }

        # You might want to re-run intent analysis or element extraction on the original prompt
        # or use the evaluation/feedback to modify the original elements.
        # For simplicity, let's just return the collected data.
        return combined_elements

    def get_story_elements_from_prompt(self, user_prompt: str) -> Dict[str, Any]:
        """Extracts story elements directly from a user prompt using LLM."""
        # This method is similar to the element extraction part of classify_prompt
        # It can be used when the intent is already known (e.g., 'new_story')

        llm_prompt = f"""
Extract key story elements from the following user prompt for a new story:

User prompt: "{user_prompt}"

Extract the following elements: characters, setting, plot_idea, theme, conflict, moral_lesson, tone, length_preference, target_age_group.
If an element is not mentioned, omit it.

Return your analysis as a JSON object with the following fields:
- "story_elements": (object) Extracted story elements. Example: {{"characters": ["dragon", "princess"], "setting": "magical forest"}}
- "error_message": (string, optional) If you cannot reliably extract elements.
"""

        try:
            llm_analysis_str = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[{"role": "system", "content": "You are a story element extraction assistant."},
                            {"role": "user", "content": llm_prompt}],
                # response_format={ "type": "json_object" } # If using newer APIs that support JSON mode
            ).choices[0].message.content
            
            llm_analysis = json.loads(llm_analysis_str)
            story_elements = llm_analysis.get("story_elements", {})
            error_message = llm_analysis.get("error_message")

            if error_message:
                 print(f"LLM element extraction failed: {error_message}")
                 return {}

            return story_elements

        except Exception as e:
            print(f"LLM element extraction failed: {e}")
            return {}

    def get_story_elements_for_change_or_update(self, user_id: str, user_story_id: str, user_prompt: str) -> Dict[str, Any]:
        """Extracts story elements for changing or updating an existing story."""
        # This method combines the original story elements with the new prompt
        # and uses an LLM to determine the changes/updates.

        # 1. Get original story elements
        original_elements = self.get_original_story_elements(user_id, user_story_id)
        original_prompt = original_elements.get('prompt', '')

        # 2. Construct prompt for LLM to identify changes/updates
        llm_prompt = f"""
Analyze the following user prompt in the context of the original story request.
Identify what aspects of the original story the user wants to change or update.

Original story request: "{original_prompt}"
User prompt for change/update: "{user_prompt}"

Identify the specific changes or updates requested for the story elements (characters, setting, plot_idea, theme, conflict, moral_lesson, tone, length_preference, target_age_group).
If an element is not mentioned for change, omit it.

Return your analysis as a JSON object with the following fields:
- "changes": (object) Dictionary of elements to change/update with their new values. Example: {{"characters": ["brave knight"], "setting": "dark castle"}}
- "introduction_context": (string) A summary of the requested changes/updates.
- "error_message": (string, optional) If you cannot reliably identify changes.
"""

        try:
            llm_analysis_str = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[{"role": "system", "content": "You are a story change/update analysis assistant."},
                            {"role": "user", "content": llm_prompt}],
                # response_format={ "type": "json_object" } # If using newer APIs that support JSON mode
            ).choices[0].message.content
            
            llm_analysis = json.loads(llm_analysis_str)
            changes = llm_analysis.get("changes", {})
            introduction_context = llm_analysis.get("introduction_context", "Could not determine changes.")
            error_message = llm_analysis.get("error_message")

            if error_message:
                 print(f"LLM change/update analysis failed: {error_message}")
                 return {}

            # Combine original elements with requested changes
            # This is a simplified approach; a more complex one might merge or replace.
            # For now, let's just return the identified changes and context.
            return {
                "story_elements": changes, # Returning changes under 'story_elements' key for consistency
                "introduction_context": introduction_context
            }

        except Exception as e:
            print(f"LLM change/update analysis failed: {e}")
            return {}

    def get_story_elements_for_regeneration_from_evaluation(self, user_id: str, user_story_id: str, evaluation: Dict[str, Any], feedback) -> Dict[str, Any]:
        """Extracts story elements for regeneration based on evaluation and feedback."""
        # This method uses evaluation and feedback to guide the regeneration.

        # 1. Get original story elements (prompt, intent)
        original_elements = self.get_original_story_elements(user_id, user_story_id)
        original_prompt = original_elements.get('prompt', '')
        original_intent = original_elements.get('intent', '')

        # 2. Format evaluation and feedback
        formatted_evaluation = json.dumps(evaluation, indent=2) if evaluation else "No evaluation provided."
        # Ensure feedback is a list of strings
        if isinstance(feedback, str):
            feedback_list = [feedback]
        elif hasattr(feedback, '__iter__') and not isinstance(feedback, dict):
            feedback_list = list(feedback)
        else:
            feedback_list = []
        formatted_feedback = "\n".join([f"- {f}" for f in feedback_list]) if feedback_list else "No feedback provided."

        # 3. Construct prompt for LLM to guide regeneration
        llm_prompt = f"""
Based on the original story request, the user's evaluation, and feedback, identify how to regenerate the story to address the feedback and improve the evaluation.

Original story request: "{original_prompt}"
Original intent: "{original_intent}"

User Evaluation:
{formatted_evaluation}

User Feedback:
{formatted_feedback}

Identify the key aspects of the story that need to be changed or emphasized during regeneration based on the evaluation and feedback. Focus on how to improve the story according to the user's input.

Return your analysis as a JSON object with the following fields:
- "regeneration_guidance": (string) Specific instructions or focus areas for regenerating the story.
- "story_elements_to_adjust": (object) Specific story elements that need adjustment based on feedback (e.g., {{"tone": "more adventurous", "plot_idea": "add a twist"}}).
- "error_message": (string, optional) If you cannot reliably determine regeneration guidance.
"""

        try:
            llm_analysis_str = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[{"role": "system", "content": "You are a story regeneration guidance assistant."},
                            {"role": "user", "content": llm_prompt}],
                # response_format={ "type": "json_object" } # If using newer APIs that support JSON mode
            ).choices[0].message.content
            
            llm_analysis = json.loads(llm_analysis_str)
            regeneration_guidance = llm_analysis.get("regeneration_guidance", "Regenerate the story.")
            story_elements_to_adjust = llm_analysis.get("story_elements_to_adjust", {})
            error_message = llm_analysis.get("error_message")

            if error_message:
                 print(f"LLM regeneration guidance failed: {error_message}")
                 return {}

            # Combine guidance and elements to adjust
            return {
                "regeneration_guidance": regeneration_guidance,
                "story_elements_to_adjust": story_elements_to_adjust
            }
        except Exception as e:
            print(f"LLM element extraction failed: {e}")
            return {}

    def get_story_elements_for_continuation(self, user_id: str, user_story_id: str, user_prompt: str) -> Dict[str, Any]:
        """Extracts elements for continuing an existing story based on user prompt."""
        # This method is for when the user wants to add to the end of the last story.

        # 1. Get the last story text
        historical_context = self._get_last_story_and_conversation(user_id)
        last_story_text = historical_context.get("last_story_text", "")

        # 2. Construct prompt for LLM to determine continuation
        llm_prompt = f"""
Based on the end of the previous story and the user's prompt, determine how to continue the story.

End of previous story:
\"\"\"{last_story_text[-500:]}\"\"\" # Use the last 500 characters as context

User prompt for continuation: "{user_prompt}"

Identify the key elements or plot points the user wants to introduce to continue the story. What should happen next?

Return your analysis as a JSON object with the following fields:
- "continuation_elements": (object) Dictionary of elements or plot points for continuation. Example: {{"new_character": "a wise owl", "next_event": "they find a hidden path"}}
- "introduction_context": (string) A summary of how the story should continue.
- "error_message": (string, optional) If you cannot reliably determine continuation.
"""

        try:
            llm_analysis_str = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[{"role": "system", "content": "You are a story continuation assistant."},
                            {"role": "user", "content": llm_prompt}],
                # response_format={ "type": "json_object" } # If using newer APIs that support JSON mode
            ).choices[0].message.content
            
            llm_analysis = json.loads(llm_analysis_str)
            continuation_elements = llm_analysis.get("continuation_elements", {})
            introduction_context = llm_analysis.get("introduction_context", "Could not determine continuation.")
            error_message = llm_analysis.get("error_message")

            if error_message:
                 print(f"LLM continuation analysis failed: {error_message}")
                 return {}

            return {
                "story_elements": continuation_elements, # Returning continuation elements under 'story_elements' key
                "introduction_context": introduction_context
            }
        except Exception as e:
            print(f"LLM element extraction failed: {e}")
            return {}

    def get_story_elements_for_branching(self, user_id: str, user_story_id: str, user_prompt: str) -> Dict[str, Any]:
        """Extracts elements for branching an existing story based on user prompt."""
        # This method is for when the user wants to take the story in a new direction from a specific point.

        # 1. Get the last story text
        historical_context = self._get_last_story_and_conversation(user_id)
        last_story_text = historical_context.get("last_story_text", "")

        # 2. Construct prompt for LLM to determine branching point and new direction
        llm_prompt = f"""
Based on the previous story and the user's prompt, determine a point in the story to branch from and the new direction the user wants to take.

Previous story:
\"\"\"{last_story_text}\"\"\"

User prompt for branching: "{user_prompt}"

Identify the approximate point in the story where the branch should occur (e.g., after the hero meets the dragon) and the key elements or plot points for the new branch.

Return your analysis as a JSON object with the following fields:
- "branching_point_context": (string) Description of the point in the story to branch from.
- "branching_elements": (object) Dictionary of elements or plot points for the new branch. Example: {{"new_path": "instead of fighting the dragon, they become friends"}}
- "introduction_context": (string) A summary of the new direction for the story.
- "error_message": (string, optional) If you cannot reliably determine branching.
"""

        try:
            llm_analysis_str = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[{"role": "system", "content": "You are a story branching assistant."},
                            {"role": "user", "content": llm_prompt}],
                # response_format={ "type": "json_object" } # If using newer APIs that support JSON mode
            ).choices[0].message.content
            
            llm_analysis = json.loads(llm_analysis_str)
            branching_point_context = llm_analysis.get("branching_point_context", "")
            branching_elements = llm_analysis.get("branching_elements", {})
            introduction_context = llm_analysis.get("introduction_context", "Could not determine branching.")
            error_message = llm_analysis.get("error_message")

            if error_message:
                 print(f"LLM branching analysis failed: {error_message}")
                 return {}

            return {
                "branching_point_context": branching_point_context,
                "story_elements": branching_elements, # Returning branching elements under 'story_elements' key
                "introduction_context": introduction_context
            }
        except Exception as e:
            print(f"LLM element extraction failed: {e}")
            return {}

    def get_story_elements_for_ending(self, user_id: str, user_story_id: str, user_prompt: str) -> Dict[str, Any]:
        """Extracts elements for ending an existing story based on user prompt."""
        # This method is for when the user wants to conclude the last story.

        # 1. Get the last story text
        historical_context = self._get_last_story_and_conversation(user_id)
        last_story_text = historical_context.get("last_story_text", "")

        # 2. Construct prompt for LLM to determine the ending
        llm_prompt = f"""
Based on the previous story and the user's prompt, determine how to end the story.

Previous story:
\"\"\"{last_story_text}\"\"\"

User prompt for ending: "{user_prompt}"

Identify the key elements or plot points needed to bring the story to a conclusion according to the user's request.

Return your analysis as a JSON object with the following fields:
- "ending_elements": (object) Dictionary of elements or plot points for the ending. Example: {{"resolution": "the hero defeats the villain", "moral": "friendship is important"}}
- "introduction_context": (string) A summary of how the story should end.
- "error_message": (string, optional) If you cannot reliably determine the ending.
"""

        try:
            llm_analysis_str = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[{"role": "system", "content": "You are a story ending assistant."},
                            {"role": "user", "content": llm_prompt}],
                # response_format={ "type": "json_object" } # If using newer APIs that support JSON mode
            ).choices[0].message.content
            
            llm_analysis = json.loads(llm_analysis_str)
            ending_elements = llm_analysis.get("ending_elements", {})
            introduction_context = llm_analysis.get("introduction_context", "Could not determine ending.")
            error_message = llm_analysis.get("error_message")

            if error_message:
                 print(f"LLM ending analysis failed: {error_message}")
                 return {}

            return {
                "story_elements": ending_elements, # Returning ending elements under 'story_elements' key
                "introduction_context": introduction_context
            }
        except Exception as e:
            print(f"LLM element extraction failed: {e}")
            return {}
            
    def get_story_elements_for_summary(self, user_id: str, user_story_id: str) -> Dict[str, Any]:
        """Extracts elements for summarizing an existing story."""
        # This method is for when the user asks for a summary of the last story.

        # 1. Get the last story text
        historical_context = self._get_last_story_and_conversation(user_id)
        last_story_text = historical_context.get("last_story_text", "")

        # 2. Construct prompt for LLM to generate a summary
        llm_prompt = f"""
Summarize the following story:

Story:
\"\"\"{last_story_text}\"\"\"

Provide a concise summary of the main plot points, characters, and outcome.

Return your analysis as a JSON object with the following fields:
- "summary": (string) The generated summary.
- "error_message": (string, optional) If you cannot reliably generate a summary.
"""

        try:
            llm_analysis_str = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model
                messages=[{"role": "system", "content": "You are a story summarization assistant."},
                            {"role": "user", "content": llm_prompt}],
                # response_format={ "type": "json_object" } # If using newer APIs that support JSON mode
            ).choices[0].message.content
            
            llm_analysis = json.loads(llm_analysis_str)
            summary = llm_analysis.get("summary", "Could not generate summary.")
            error_message = llm_analysis.get("error_message")

            if error_message:
                 print(f"LLM summarization failed: {error_message}")
                 return {}

            return {
                "summary": summary
            }
        except Exception as e:
            print(f"LLM element extraction failed: {e}")
            return {}

    def get_story_elements_for_analysis(self, user_id: str, user_prompt: str) -> Dict[str, Any]:
        """
        Analyzes the user's prompt to extract key story elements using an LLM.
        Potentially uses user_id for context if needed in more advanced versions,
        but primarily focuses on the current user_prompt.

        Args:
            user_id (str): The ID of the user.
            user_prompt (str): The user's input/prompt.

        Returns:
            Dict[str, Any]: A dictionary containing extracted story elements
                            (e.g., characters, setting, plot_points, theme).
                            Returns an empty dict on failure.
        """
        if not user_prompt:
            return {}

        # You can fetch last story or conversation history if needed for more context
        # context = self._get_last_story_and_conversation(user_id)
        # last_story_text = context.get("last_story_text", "")
        # conversation_history_summary = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context.get("conversation_history", [])[-5:]]) # Last 5 messages

        llm_prompt = f"""
        Analyze the following user prompt for a story and extract key story elements.
        User Prompt: "{user_prompt}"

        Please identify and list the following elements if present:
        - Characters: (Names, brief descriptions)
        - Setting: (Location, time period, atmosphere)
        - Plot Points: (Key events or actions suggested)
        - Theme: (Underlying message or idea)
        - Genre: (e.g., fantasy, sci-fi, mystery)
        - Desired Tone: (e.g., humorous, serious, adventurous)

        If an element is not clearly present, indicate that or omit it.
        Return the analysis as a JSON object with keys: "characters", "setting", "plot_points", "theme", "genre", "desired_tone".
        Each key should have a string or list of strings as its value.
        Example for characters: ["Character A: A brave knight", "Character B: A wise wizard"]
        Example for plot_points: ["The knight embarks on a quest", "The wizard offers guidance"]

        JSON Output:
        """

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Or your preferred model, consider gpt-4 for better extraction
                messages=[
                    {"role": "system", "content": "You are an expert story analyst. Your task is to extract structured story elements from user prompts. Respond in JSON format."},
                    {"role": "user", "content": llm_prompt}
                ],
                # For newer OpenAI library versions that support JSON mode explicitly:
                # response_format={ "type": "json_object" } 
            )
            llm_response_content = response.choices[0].message.content
            
            if llm_response_content:
                # Attempt to parse the JSON from the LLM response
                # The LLM might sometimes include explanations before/after the JSON block.
                # A more robust parsing might be needed if the LLM is inconsistent.
                try:
                    # Try to find JSON block if there's surrounding text
                    json_match = re.search(r'\{.*\}', llm_response_content, re.DOTALL)
                    if json_match:
                        story_elements = json.loads(json_match.group(0))
                    else:
                        # Fallback if no clear JSON block is found but content exists
                        story_elements = json.loads(llm_response_content) 
                except json.JSONDecodeError as je:
                    print(f"Failed to decode JSON from LLM response for story elements: {je}")
                    print(f"LLM Raw Response: {llm_response_content}")
                    # Fallback: return the raw text if it's not parsable as JSON, or an error structure
                    return {"error": "Failed to parse story elements from LLM", "raw_response": llm_response_content}
                
                # Basic validation or cleaning can be done here
                # For example, ensuring expected keys exist or have correct types.
                return story_elements
            else:
                print("LLM returned empty content for story elements.")
                return {}

        except Exception as e:
            print(f"Error during LLM call for story element extraction: {e}")
            return {}