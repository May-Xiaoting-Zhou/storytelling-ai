document.getElementById('send-button').addEventListener('click', function() {
    const userInput = document.getElementById('user-input').value;
    if (userInput.trim() !== '') {
        const userMessage = document.createElement('div');
        userMessage.className = 'chat-message user';
        userMessage.textContent = userInput;
        document.getElementById('chat-box').appendChild(userMessage);

        // Simulate a response from the chatbot
        const botResponse = document.createElement('div');
        botResponse.className = 'chat-message bot';
        botResponse.textContent = 'This is a simulated response from the chatbot.';
        document.getElementById('chat-box').appendChild(botResponse);

        // Clear the input field
        document.getElementById('user-input').value = '';
    }
});