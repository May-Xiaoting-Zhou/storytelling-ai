import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


DATABASE_DIR = Path('database')
CONVERSATIONS_FILE = os.path.join(DATABASE_DIR, 'conversations.json')

class ConversationManager:
    def __init__(self, file_path: str = CONVERSATIONS_FILE):
        self.file_path = file_path
        if not os.path.exists(DATABASE_DIR):
            os.makedirs(DATABASE_DIR)
        if not os.path.exists(self.file_path):
            self._save_conversations([])

    def _load_conversations(self) -> List[Dict[str, Any]]:
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_conversations(self, conversations: List[Dict[str, Any]]) -> None:
        with open(self.file_path, 'w') as f:
            json.dump(conversations, f, indent=2)

    def _generate_id(self, conversations: List[Dict[str, Any]]) -> int:
        return max([conv.get('id', 0) for conv in conversations], default=0) + 1

    def add_conversation(self, user_id: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Adds a new conversation.
        A message is a dict with 'role' (e.g., 'user', 'agent') and 'content'.
        """
        conversations = self._load_conversations()
        new_conversation = {
            "id": self._generate_id(conversations),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "messages": messages, # List of {"role": "user/agent", "content": "message text"}
            "last_updated": datetime.utcnow().isoformat()
        }
        conversations.append(new_conversation)
        self._save_conversations(conversations)
        return new_conversation

    def get_conversation_by_id(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        conversations = self._load_conversations()
        for conv in conversations:
            if conv.get('id') == conversation_id:
                return conv
        return None

    def get_conversations_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        conversations = self._load_conversations()
        return [conv for conv in conversations if conv.get('user_id') == user_id]

    def update_conversation(self, conversation_id: int, new_message: Optional[Dict[str, str]] = None, updated_messages: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
        """
        Updates a conversation by adding a new message or replacing all messages.
        """
        conversations = self._load_conversations()
        for conv in conversations:
            if conv.get('id') == conversation_id:
                if new_message:
                    conv.setdefault('messages', []).append(new_message)
                if updated_messages is not None: # Allow replacing all messages
                    conv['messages'] = updated_messages
                conv['last_updated'] = datetime.utcnow().isoformat()
                self._save_conversations(conversations)
                return conv
        return None

    def delete_conversation(self, conversation_id: int) -> bool:
        conversations = self._load_conversations()
        initial_len = len(conversations)
        conversations = [conv for conv in conversations if conv.get('id') != conversation_id]
        if len(conversations) < initial_len:
            self._save_conversations(conversations)
            return True
        return False

    def get_all_conversations(self) -> List[Dict[str, Any]]:
        return self._load_conversations()

    def get_last_conversation(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the last conversation for a given user_id, sorted by last_updated timestamp.
        """
        user_conversations = self.get_conversations_by_user_id(user_id)
        if not user_conversations:
            return None
        
        # Sort conversations by 'last_updated' in descending order
        # The 'last_updated' field is an ISO format string, direct string comparison works for sorting
        sorted_conversations = sorted(user_conversations, key=lambda conv: conv.get('last_updated', ''), reverse=True)
        
        return sorted_conversations[0]