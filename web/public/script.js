// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('chat-form');
    const input = document.getElementById('input');
    const output = document.getElementById('output');
    const modeToggle = document.getElementById('mode-toggle');
    const sendButton = document.getElementById('send-button');
    let currentStreamId = null;

    // Initialize markdown parser
    if (typeof marked === 'undefined') {
        console.warn('Marked library not loaded, falling back to plain text');
    }

    // Format message with markdown
    function formatMessage(text) {
        try {
            return marked.parse(text);
        } catch (error) {
            console.error('Error parsing markdown:', error);
            return text.replace(/\n/g, '<br>');
        }
    };

    // Append a message to the chat
    function appendMessage(role, content) {
        const output = document.getElementById('output');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        messageDiv.innerHTML = formatMessage(content);

        // Add copy and TTS buttons for AI messages
        if (role === 'ai') {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';
            
            // Copy button
            const copyButton = document.createElement('button');
            copyButton.innerHTML = '📋';
            copyButton.title = 'Copy to clipboard';
            copyButton.onclick = () => {
                navigator.clipboard.writeText(content)
                    .then(() => {
                        copyButton.innerHTML = '✓';
                        setTimeout(() => copyButton.innerHTML = '📋', 2000);
                    })
                    .catch(err => console.error('Copy failed:', err));
            };
            
            // Text-to-Speech button
            if ('speechSynthesis' in window) {
                const ttsButton = document.createElement('button');
                ttsButton.innerHTML = '🔊';
                ttsButton.title = 'Read aloud';
                ttsButton.onclick = () => {
                    const utterance = new SpeechSynthesisUtterance(content);
                    speechSynthesis.speak(utterance);
                };
                actionsDiv.appendChild(ttsButton);
            }
            
            actionsDiv.appendChild(copyButton);
            messageDiv.appendChild(actionsDiv);
        }

        output.appendChild(messageDiv);
        output.scrollTop = output.scrollHeight;
    }

    // Handle streaming responses
    async function handleStreamingResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentMessage = '';
        let messageDiv = null;

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep the last incomplete line in the buffer

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const event = line.replace(/^data: /, '');
                            if (event === '[DONE]') {
                                return;
                            }

                            const data = JSON.parse(event);
                            if (data.streamId) {
                                currentStreamId = data.streamId;
                            } else if (data.text) {
                                currentMessage += data.text;
                                
                                // Create or update AI message
                                if (!messageDiv) {
                                    messageDiv = document.createElement('div');
                                    messageDiv.className = 'message ai-message';
                                    document.getElementById('output').appendChild(messageDiv);
                                }
                                messageDiv.innerHTML = formatMessage(currentMessage);
                                
                                // Scroll to bottom
                                const output = document.getElementById('output');
                                output.scrollTop = output.scrollHeight;
                            }
                        } catch (error) {
                            console.error('Error parsing SSE:', error, line);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Stream reading error:', error);
            throw error;
        }
    }

    // Handle regular commands (non-streaming)
    async function handleRegularCommand(command, args) {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: `${command} ${args}`.trim()
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `HTTP error ${response.status}`);
            }

            const data = await response.json();
            return data.output || data.text || '';
        } catch (error) {
            console.error('Command error:', error);
            throw error;
        }
    }

    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = input.value.trim();
        
        if (!message) return;
        
        // Clear input and show user message immediately
        input.value = '';
        appendMessage('user', message);
        
        try {
            // Send message to server
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `HTTP error ${response.status}`);
            }

            // Handle streaming response
            await handleStreamingResponse(response);
        } catch (error) {
            console.error('Command error:', error);
            appendMessage('error', `Error: ${error.message}`);
        }
    });

    // Toggle between chat and command mode
    modeToggle.addEventListener('change', function() {
        // Update input placeholder
        input.placeholder = this.checked ? 'Type your message...' : 'Enter a command...';
        
        // Clear output and show appropriate welcome message
        if (this.checked) {
            // Chat mode
            output.innerHTML = `
                <div class="message ai-message">
                    Hello! I'm your Fiber AI assistant. How can I help you today?
                </div>
            `;
        } else {
            // Command mode
            output.innerHTML = `
                <div class="welcome-message">
                    <h2>Welcome to Fiber!</h2>
                    <p>Available commands:</p>
                    <ul>
                        <li><strong>define</strong> - Get word definitions</li>
                        <li><strong>compare</strong> - Compare multiple items</li>
                        <li><strong>brainstorm</strong> - Generate creative ideas</li>
                        <li><strong>search</strong> - Search across the web</li>
                    </ul>
                    <p>Type a command followed by your query (e.g., "define happiness")</p>
                </div>
            `;
        }
    });

    // Set initial placeholder and welcome message
    input.placeholder = modeToggle.checked ? 'Type your message...' : 'Enter a command...';
    if (modeToggle.checked) {
        output.innerHTML = `
            <div class="message ai-message">
                Hello! I'm your Fiber AI assistant. How can I help you today?
            </div>
        `;
    } else {
        output.innerHTML = `
            <div class="welcome-message">
                <h2>Welcome to Fiber!</h2>
                <p>Available commands:</p>
                <ul>
                    <li><strong>define</strong> - Get word definitions</li>
                    <li><strong>compare</strong> - Compare multiple items</li>
                    <li><strong>brainstorm</strong> - Generate creative ideas</li>
                    <li><strong>search</strong> - Search across the web</li>
                </ul>
                <p>Type a command followed by your query (e.g., "define happiness")</p>
            </div>
        `;
    }
});

// Typing effect function
async function typeMessage(element, text, speed = 30) {
    const formattedText = formatMessage(text);
    element.innerHTML = ''; // Clear existing content
    element.classList.add('typing'); // Add typing class for cursor
    
    // Create a temporary div to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = formattedText;
    
    // Function to type text content while preserving HTML
    async function typeContent(node) {
        for (const childNode of node.childNodes) {
            if (childNode.nodeType === Node.TEXT_NODE) {
                // Type each character of text nodes
                for (const char of childNode.textContent) {
                    const textNode = document.createTextNode(char);
                    element.lastElementChild?.appendChild(textNode) || element.appendChild(textNode);
                    await new Promise(resolve => setTimeout(resolve, speed));
                }
            } else {
                // For HTML elements, create them and continue typing their content
                const newElement = childNode.cloneNode(false);
                element.appendChild(newElement);
                await typeContent(childNode);
            }
        }
    }
    
    // Start typing the content
    await typeContent(tempDiv);
    element.classList.remove('typing'); // Remove typing class when done
}

// Utility function to escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Format markdown text
function formatMarkdown(text) {
    // Headers
    text = text.replace(/### (.*?)\n/g, '<h3>$1</h3>\n');
    text = text.replace(/## (.*?)\n/g, '<h2>$1</h2>\n');
    text = text.replace(/# (.*?)\n/g, '<h1>$1</h1>\n');
    
    // Bold
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Code blocks
    text = text.replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>');
    
    // Inline code
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Lists
    text = text.replace(/^\s*[-*]\s+(.*?)$/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    
    // Links
    text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Paragraphs
    text = text.replace(/\n\n/g, '</p><p>');
    text = '<p>' + text + '</p>';
    
    // Clean up empty paragraphs
    text = text.replace(/<p>\s*<\/p>/g, '');
    
    return text;
}

// Message action handlers
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Show temporary success message
        const tooltip = document.createElement('div');
        tooltip.className = 'action-tooltip';
        tooltip.textContent = 'Copied!';
        tooltip.style.display = 'block';
        document.body.appendChild(tooltip);
        
        setTimeout(() => {
            tooltip.remove();
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text:', err);
    });
}

function speakText(text) {
    // Stop any ongoing speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    // Get available voices and use a good English voice if available
    const voices = window.speechSynthesis.getVoices();
    const englishVoices = voices.filter(voice => voice.lang.startsWith('en-'));
    if (englishVoices.length > 0) {
        utterance.voice = englishVoices[0];
    }
    
    window.speechSynthesis.speak(utterance);
}

// Create message action buttons
function createMessageActions(messageText) {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    
    // Copy button
    const copyButton = document.createElement('button');
    copyButton.className = 'action-button';
    copyButton.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span class="action-tooltip">Copy to clipboard</span>
    `;
    copyButton.onclick = (e) => {
        e.stopPropagation();
        copyToClipboard(messageText);
    };
    
    // TTS button
    const ttsButton = document.createElement('button');
    ttsButton.className = 'action-button';
    ttsButton.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 6v12M6 12h12"></path>
            <circle cx="12" cy="12" r="10"></circle>
        </svg>
        <span class="action-tooltip">Read aloud</span>
    `;
    ttsButton.onclick = (e) => {
        e.stopPropagation();
        speakText(messageText);
    };
    
    actionsDiv.appendChild(copyButton);
    actionsDiv.appendChild(ttsButton);
    return actionsDiv;
}
