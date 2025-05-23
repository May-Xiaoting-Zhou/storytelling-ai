from flask import Flask, request, jsonify, send_from_directory # Added send_from_directory
from flask_cors import CORS
import os # Added os
import traceback # Added for error logging
import json # Added for potential direct JSON operations, though agent handles it here
import collections # Added for defaultdict

from агенты.storyteller import StorytellerAgent
from агенты.judge import JudgeAgent
from агенты.feedback import FeedbackAgent
from агенты.intent_analyzer import IntentAnalyzerAgent
from агенты.conversation_manager import ConversationManager
from config import ITERATION_LIMIT # Import the new configuration

app = Flask(__name__, static_folder='../frontend/dist')
# Consider a more specific CORS setup for debugging if the general one causes issues
CORS(app, origins=["http://localhost:5173"], supports_credentials=True)
# Initialize agents
storyteller = StorytellerAgent()
judge = JudgeAgent()
feedback = FeedbackAgent()
intent_analyzer = IntentAnalyzerAgent()
conversation_manager = ConversationManager() # Instantiate ConversationManager

@app.route('/api/story', methods=['POST'])
def generate_story():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.json
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt in request'}), 400

        prompt = data.get('prompt')
        original_user_prompt = prompt # Save the original prompt for logging

        # Use user_id from request, fallback to 'guest_user' if not provided
        user_id = data.get('user_id', 'guest_user') 
        user_id_str = str(user_id) # Ensure user_id is a string for dictionary keys
        
        # Check if it's the user's first time based on user_profiles.json
        user_profiles_path = storyteller.memory_personalization.user_profiles_path
        # The MemoryPersonalizationAgent's __init__ should ensure user_profiles.json exists.
        current_user_profiles = storyteller.memory_personalization._load_json(user_profiles_path)

        # If user_id is not provided, generate a new one
        if user_id_str == 'guest_user':
            # user_id_str = 0
            user_id_str = storyteller.memory_personalization.get_next_user_id(current_user_profiles)
            user_id_str = 0 # for testing

        # check if user_id in last record of conversations.json
        last_conversation = conversation_manager.get_last_conversation(user_id_str)
        if last_conversation:
            last_message = last_conversation['messages'][-1]
            if last_message['role'] == 'agent' and last_message['status'] == 'new_user_profiling_required':
                # use original_user_prompt to update user profile
                user_profiles = storyteller.memory_personalization._load_json(user_profiles_path)
                user_profiles[user_id_str] = storyteller.memory_personalization.gather_user_preferences(user_id_str, original_user_prompt)
                storyteller.memory_personalization._save_json(user_profiles_path, user_profiles)

                msg = "Awowesome! Thank you for sharing that with me. I'm ready to tell you a story now. What kind of story would you like to hear?"
                user_message = {"role": "user", "content": original_user_prompt}
                agent_message = {"role": "agent", "content": msg, 'status': 'proceed'}
                # Update user_profiles in the ConversationManager
                conversation_manager.add_conversation(
                    user_id=user_id_str,
                    messages=[user_message, agent_message]
                )
                return jsonify({
                   'status': 'proceed',
                   'message': msg,
                    'user_id': user_id_str,
                   'story': None # Consistent with other responses that might include a story
                }), 200
        else:  
            # Check if user_id is new (not in user_profiles)
            is_new_user_for_profiling = user_id_str not in current_user_profiles
            if is_new_user_for_profiling:
                user_profiles = storyteller.memory_personalization.get_user_profile(user_id_str)
                storyteller.memory_personalization._save_json(user_profiles_path, user_profiles)

                msg = "Welcome! To help me tell you the best stories, please tell me a bit about yourself. For example, what is your age, gender (optional), favorite characters or types of animals, favorite kinds of stories (e.g., adventure, funny, magical), and preferred story style (e.g., simple, detailed)?"
                user_message = {"role": "user", "content": original_user_prompt}
                agent_message = {"role": "agent", "content": msg, 'status': 'new_user_profiling_required'}

                conversation_manager.add_conversation(
                        user_id=user_id_str,
                        messages=[user_message, agent_message]
                    )

                # This is the user's first interaction requiring preference gathering.
                return jsonify({
                    'status': 'new_user_profiling_required',
                    'message': msg,
                    'user_id': user_id_str,
                    'story': None # Consistent with other responses that might include a story
                }), 200

        # If user exists, proceed with normal story generation flow.
        # 1. Analyze intent
        intent_result = intent_analyzer.classify_prompt(prompt)

        # 2. Get a specific response message if the intent doesn't lead to new story generation
        # Stop, clarify, or redirect to a specific intent
        if intent_result['action'] != 'proceed':
            # If IntentAnalyzerAgent provides a direct response (e.g., for questions, updates)
            user_message = {"role": "user", "content": original_user_prompt}
            agent_message = {"role": "agent", "content": intent_result['message'], 'status': intent_result['action']}

            conversation_manager.add_conversation(
                    user_id=user_id_str,
                    messages=[user_message, agent_message]
                )
            return jsonify({
                'message': agent_message['content'],
                'status': agent_message['status'], 
                'intent': intent_result['intent']
            })
        else:
            # Proceed with story generation (intent_type is likely 'new_story' or 'change_story')
            # For MVP, we'll use default age_range and non-interactive mode unless specified.
            story_elements = intent_result.get('story_elements', {}) # Ensure story_elements is always a dict
            current_intent = intent_result.get('intent', 'new_story') # Default to new_story if not present

            # The new generate_story function handles different user_id types and intents internally
            story_details = storyteller.generate_story(
                prompt=original_user_prompt, # Use the original user prompt string
                user_id=user_id_str, # Pass user_id_str (which can be 'guest_user')
                story_elements=story_elements, 
                intent=current_intent
            )


            # Iterative improvement loop
            # TODO: Implement a more sophisticated stopping condition
            # For now, limit the number of iterations
            # LIMIT_LOOP = 3 # TODO: For now, limit the number of iterations
            for _ in range(ITERATION_LIMIT): # Use the configured limit
                evaluation = judge.evaluate_story(user_id, story_elements, generated_story_text)
                logger.debug(f"Iteration evaluation: {evaluation}")
                evaluation = {} # Initialize evaluation in case the loop doesn't run

            # 3. Evaluate story quality
            # Ensure story_details is not None and contains 'story'
            if story_details and 'story' in story_details:
                evaluation = judge.evaluate_story(story_details['story'], original_user_prompt, story_elements)
                stories_lst = collections.defaultdict(list)
                improved_story = story_details['story']
                while LIMIT_LOOP >= 0 and evaluation['score'] < 7:
                    # 4. Provide feedback if needed
                    feedback_message = feedback.provide_feedback(evaluation['feedback'], improved_story, original_user_prompt, story_elements)

                    story_elements = intent_analyzer.update_story_elements( # Changed to _update_story_elements
                        improved_story,              # improved story text
                        story_elements,              # Extracted story elements
                        original_user_prompt,        # Original user prompt
                        feedback_message,            # Summarized feedback
                        evaluation                   # Full evaluation from JudgeAgent
                    )

                    # Ensure storyteller.generate_story_from_feedback is correctly called
                    improved_story = storyteller.generate_story_from_feedback(
                        improved_story,              # improved story text
                        story_elements,              # Extracted story elements
                        original_user_prompt,        # Original user prompt
                        feedback_message,            # Summarized feedback
                        evaluation                   # Full evaluation from JudgeAgent
                    )
                    
                    if LIMIT_LOOP >= 0: # Re-evaluate if not out of loops
                        print(f"evaluation: {evaluation}") # Debug print
                        print(f"feedback_message: {feedback_message}") # Debug print
                        print(f"story_elements: {story_elements}") # Debug print
                        stories_lst[evaluation['score']].append(improved_story)
                        # Sort the scores in descending order
                        sorted_scores = sorted(stories_lst.keys(), reverse=True)
                        # Get the highest score
                        highest_score = sorted_scores[0]
                        print(f"Highest score: {highest_score}") # Debug print
                        # Get the stories associated with the highest score
                        best_stories = stories_lst[highest_score]
                        print(f"Best stories: {best_stories}") # Debug print
                        improved_story = best_stories[0]

                        evaluation = judge.evaluate_story(improved_story, original_user_prompt, story_elements)

                    LIMIT_LOOP -= 1

                # Select the first story from the best stories
                story_details['story'] = improved_story
            else:
                # Handle cases where story_details might be unexpectedly None or malformed
                app.logger.error(f"Initial story_details is None or missing 'story' key for prompt: {original_user_prompt}")
                return jsonify({'error': 'Failed to generate initial story content'}), 500


            # Record interaction if user_id is available
            if user_id and story_details and 'story' in story_details:
                story_data_for_profile = {
                    'prompt': original_user_prompt,
                    'title': story_details.get('title', 'Untitled Story'), # Assuming title might be in story_details
                    'summary': (story_details.get('story', '')[:150] + 
                                ("..." if len(story_details.get('story', '')) > 150 else "")),
                    'user_feedback': None # User feedback is typically collected later
                }
                try:
                    storyteller.memory_personalization.record_story_interaction(
                        user_id=user_id_str, # Ensure to use user_id_str
                        story_data=story_data_for_profile,
                        interaction_time=0  # Placeholder for interaction time
                    )
                except Exception as e_record:
                    app.logger.error(f"Error recording story interaction for user {user_id_str}: {str(e_record)}\n{traceback.format_exc()}")
                    # Decide if this error should be fatal to the request or just logged
            
            # Save conversation
            if story_details and 'story' in story_details:
                user_message = {"role": "user", "content": original_user_prompt}
                agent_message = {"role": "agent", "content": story_details['story'], 'status': 'success'}
                conversation_manager.add_conversation(
                    user_id=user_id_str,
                    messages=[user_message, agent_message]
                )

            # 5. Return the story
            return jsonify({
                # 'data': story_details, # This dictionary contains 'story', 'illustration_url', etc.
                'story': story_details.get('story') if story_details else "Could not generate story.",
                'status': 'success'
                # 'intent': intent_result # Include intent analysis for client-side context
            })

    except Exception as e:
        # Log the full traceback for server-side debugging
        detailed_error = traceback.format_exc()
        app.logger.error(f"Error in generate_story: {str(e)}\n{detailed_error}")
        print(f"Error in generate_story: {str(e)}\n{detailed_error}") # Also print to console for immediate visibility
        
        return jsonify({
            'error': 'Internal server error',
            'message': str(e) # For production, you might want a more generic error message to the client
        }), 500

# Serve static files from the React build directory
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)