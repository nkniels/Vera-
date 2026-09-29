(function() {
    // Verdant brand colors
    const BRAND_COLOR = '#1B4332';
    const BRAND_LIGHT = '#2D6A4F';
    const BRAND_ACCENT = '#40916C';
    const TEXT_COLOR = '#ffffff';
    
    // Create widget container
    const widgetContainer = document.createElement('div');
    widgetContainer.id = 'vera-widget-container';
    widgetContainer.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    `;
    
    // Create chat bubble button
    const chatButton = document.createElement('button');
    chatButton.id = 'vera-chat-button';
    chatButton.innerHTML = '💬';
    chatButton.style.cssText = `
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: ${BRAND_COLOR};
        border: none;
        cursor: pointer;
        font-size: 24px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.3s ease, background-color 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    chatButton.addEventListener('mouseenter', () => {
        chatButton.style.transform = 'scale(1.1)';
        chatButton.style.backgroundColor = BRAND_LIGHT;
    });
    
    chatButton.addEventListener('mouseleave', () => {
        chatButton.style.transform = 'scale(1)';
        chatButton.style.backgroundColor = BRAND_COLOR;
    });
    
    // Create chat window
    const chatWindow = document.createElement('div');
    chatWindow.id = 'vera-chat-window';
    chatWindow.style.cssText = `
        position: absolute;
        bottom: 80px;
        right: 0;
        width: 350px;
        height: 500px;
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        display: none;
        flex-direction: column;
        overflow: hidden;
    `;
    
    // Create header
    const header = document.createElement('div');
    header.style.cssText = `
        background-color: ${BRAND_COLOR};
        color: ${TEXT_COLOR};
        padding: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    `;
    
    const headerTitle = document.createElement('h3');
    headerTitle.textContent = 'Vera - Verdant Skin Co.';
    headerTitle.style.cssText = `
        margin: 0;
        font-size: 16px;
        font-weight: 600;
    `;
    
    const closeButton = document.createElement('button');
    closeButton.innerHTML = '×';
    closeButton.style.cssText = `
        background: none;
        border: none;
        color: ${TEXT_COLOR};
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    // Create messages container
    const messagesContainer = document.createElement('div');
    messagesContainer.id = 'vera-messages';
    messagesContainer.style.cssText = `
        flex: 1;
        padding: 16px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background-color: #f8f9fa;
    `;
    
    // Create input area
    const inputArea = document.createElement('div');
    inputArea.style.cssText = `
        padding: 16px;
        border-top: 1px solid #e0e0e0;
        display: flex;
        gap: 8px;
        background-color: white;
    `;
    
    const messageInput = document.createElement('input');
    messageInput.type = 'text';
    messageInput.placeholder = 'Type your message...';
    messageInput.id = 'vera-message-input';
    messageInput.style.cssText = `
        flex: 1;
        padding: 10px 14px;
        border: 1px solid #e0e0e0;
        border-radius: 20px;
        font-size: 14px;
        outline: none;
    `;
    
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    const sendButton = document.createElement('button');
    sendButton.innerHTML = 'Send';
    sendButton.style.cssText = `
        background-color: ${BRAND_COLOR};
        color: ${TEXT_COLOR};
        border: none;
        padding: 10px 20px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: background-color 0.3s ease;
    `;
    
    sendButton.addEventListener('mouseenter', () => {
        sendButton.style.backgroundColor = BRAND_LIGHT;
    });
    
    sendButton.addEventListener('mouseleave', () => {
        sendButton.style.backgroundColor = BRAND_COLOR;
    });
    
    // Assemble chat window
    header.appendChild(headerTitle);
    header.appendChild(closeButton);
    chatWindow.appendChild(header);
    chatWindow.appendChild(messagesContainer);
    inputArea.appendChild(messageInput);
    inputArea.appendChild(sendButton);
    chatWindow.appendChild(inputArea);
    
    // Toggle chat window
    chatButton.addEventListener('click', () => {
        if (chatWindow.style.display === 'none') {
            chatWindow.style.display = 'flex';
            if (messagesContainer.children.length === 0) {
                addMessage('Hi! I\'m Vera, your assistant from Verdant Skin Co. How can I help you today?', 'bot');
            }
        } else {
            chatWindow.style.display = 'none';
        }
    });
    
    closeButton.addEventListener('click', () => {
        chatWindow.style.display = 'none';
    });
    
    // Add message to chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.4;
            word-wrap: break-word;
        `;
        
        if (sender === 'bot') {
            messageDiv.style.backgroundColor = BRAND_COLOR;
            messageDiv.style.color = TEXT_COLOR;
            messageDiv.style.alignSelf = 'flex-start';
        } else {
            messageDiv.style.backgroundColor = BRAND_ACCENT;
            messageDiv.style.color = TEXT_COLOR;
            messageDiv.style.alignSelf = 'flex-end';
        }
        
        messageDiv.textContent = text;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Send message to Vera
    async function sendMessage() {
        const text = messageInput.value.trim();
        if (!text) return;
        
        addMessage(text, 'user');
        messageInput.value = '';
        
        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.id = 'vera-typing';
        typingDiv.style.cssText = `
            align-self: flex-start;
            background-color: ${BRAND_COLOR};
            color: ${TEXT_COLOR};
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
        `;
        typingDiv.textContent = 'Typing...';
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: text,
                    channel: 'shopify'
                })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            const typingIndicator = document.getElementById('vera-typing');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            
            addMessage(data.response, 'bot');
        } catch (error) {
            console.error('Error sending message:', error);
            
            // Remove typing indicator
            const typingIndicator = document.getElementById('vera-typing');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            
            addMessage('Sorry, I\'m having trouble connecting. Please try again.', 'bot');
        }
    }
    
    sendButton.addEventListener('click', sendMessage);
    
    // Assemble widget
    widgetContainer.appendChild(chatWindow);
    widgetContainer.appendChild(chatButton);
    
    // Add to page
    document.body.appendChild(widgetContainer);
})();
