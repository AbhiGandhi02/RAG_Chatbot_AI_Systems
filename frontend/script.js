/**
 * ClearPath Chat — Frontend Logic
 * 
 * Handles sending queries to the backend /query endpoint,
 * displaying chat messages, populating the debug panel,
 * and persisting conversation history in localStorage.
 */

const API_URL = '/query';

// DOM elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const debugContent = document.getElementById('debugContent');
const debugPanel = document.getElementById('debugPanel');

// State
let isLoading = false;

// ===== Conversation Memory =====

// Get or create a persistent conversation ID
let conversationId = localStorage.getItem('clearpath_conversation_id');
if (!conversationId) {
    conversationId = 'conv_' + Math.random().toString(36).substring(2, 14);
    localStorage.setItem('clearpath_conversation_id', conversationId);
}

// Restore chat history from localStorage on page load
function restoreChatHistory() {
    const saved = localStorage.getItem('clearpath_chat_history');
    if (!saved) return;

    try {
        const messages = JSON.parse(saved);
        // Remove the default welcome message since we'll restore from history
        if (messages.length > 0) {
            chatMessages.innerHTML = '';
        }
        messages.forEach(msg => {
            addMessage(msg.text, msg.sender, msg.flags || [], true);
        });
    } catch (e) {
        console.error('Failed to restore chat history:', e);
    }
}

// Save current chat to localStorage
function saveChatHistory() {
    const messages = [];
    chatMessages.querySelectorAll('.message').forEach(el => {
        if (el.classList.contains('loading-message')) return;
        const sender = el.classList.contains('user-message') ? 'user' : 'bot';
        const contentEl = el.querySelector('.message-content');
        // Get the raw text from the message
        const textEl = contentEl.querySelector('div:last-child');
        if (textEl) {
            messages.push({
                sender,
                text: textEl.textContent,
                flags: [] // Simplified — flags are visual only
            });
        }
    });
    localStorage.setItem('clearpath_chat_history', JSON.stringify(messages));
}

// Clear conversation (new chat)
function clearConversation() {
    localStorage.removeItem('clearpath_chat_history');
    conversationId = 'conv_' + Math.random().toString(36).substring(2, 14);
    localStorage.setItem('clearpath_conversation_id', conversationId);
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-avatar bot-avatar">CP</div>
            <div class="message-content">
                <p>👋 Welcome to ClearPath Support! I can help you with questions about our project management platform.</p>
                <p>Ask me about features, pricing, integrations, troubleshooting, and more.</p>
            </div>
        </div>
    `;
}

// ===== Event Listeners =====

sendBtn.addEventListener('click', sendMessage);
document.getElementById('newChatBtn').addEventListener('click', clearConversation);

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea
messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
});

// ===== Core Functions =====

async function sendMessage() {
    const question = messageInput.value.trim();
    if (!question || isLoading) return;

    // Add user message
    addMessage(question, 'user');
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Show loading
    isLoading = true;
    sendBtn.disabled = true;
    const loadingEl = addLoadingMessage();

    try {
        const response = await fetch('/query/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                conversation_id: conversationId
            })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        // Remove loading, create empty bot message for streaming
        loadingEl.remove();
        const botMsg = addMessage('', 'bot');
        const contentDiv = botMsg.querySelector('.message-content div:last-child');

        let fullAnswer = '';
        let streamMeta = {};

        // Read the SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = JSON.parse(line.slice(6));

                if (data.type === 'metadata') {
                    streamMeta = data;
                } else if (data.type === 'token') {
                    fullAnswer += data.content;
                    contentDiv.innerHTML = formatText(fullAnswer);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } else if (data.type === 'done') {
                    // Update debug panel with full metadata
                    updateDebugPanel({
                        metadata: {
                            model_used: streamMeta.model_used || '',
                            classification: streamMeta.classification || 'simple',
                            tokens: { input: data.tokens_input, output: data.tokens_output },
                            latency_ms: data.latency_ms,
                            chunks_retrieved: streamMeta.chunks_retrieved || 0,
                            evaluator_flags: data.evaluator_flags || []
                        },
                        sources: streamMeta.sources || []
                    });

                    // Add warning badge if flagged
                    if (data.evaluator_flags && data.evaluator_flags.length > 0) {
                        const warningBadge = document.createElement('div');
                        warningBadge.className = 'warning-badge';
                        warningBadge.textContent = `⚠️ Flagged: ${data.evaluator_flags.join(', ')}`;
                        botMsg.querySelector('.message-content').insertBefore(
                            warningBadge, contentDiv
                        );
                    }
                } else if (data.type === 'error') {
                    contentDiv.textContent = `Error: ${data.content}`;
                }
            }
        }

        // Save chat history after streaming completes
        saveChatHistory();

    } catch (error) {
        loadingEl.remove();
        addMessage(`Sorry, something went wrong: ${error.message}. Please try again.`, 'bot', ['error']);
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

function addMessage(text, sender, flags = [], isRestore = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${sender}-avatar`;
    avatar.textContent = sender === 'bot' ? 'CP' : 'You';

    const content = document.createElement('div');
    content.className = 'message-content';

    // Check for warning prefix
    if (flags.length > 0 && !flags.includes('error')) {
        const warningBadge = document.createElement('div');
        warningBadge.className = 'warning-badge';
        warningBadge.textContent = `⚠️ Flagged: ${flags.join(', ')}`;
        content.appendChild(warningBadge);
    }

    // Format the text — handle newlines and basic markdown
    const formattedText = formatText(text);
    const textDiv = document.createElement('div');
    textDiv.innerHTML = formattedText;
    content.appendChild(textDiv);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom (skip during restore for performance)
    if (!isRestore) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    return messageDiv;
}

function addLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message loading-message';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar bot-avatar';
    avatar.textContent = 'CP';

    const content = document.createElement('div');
    content.className = 'message-content';
    content.innerHTML = `
        <div class="loading-dots">
            <span></span><span></span><span></span>
        </div>
    `;

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

function formatText(text) {
    // Basic markdown-like formatting
    let html = text
        // Escape HTML
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Code
        .replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:4px;font-size:12px;">$1</code>')
        // Line breaks
        .replace(/\n/g, '<br>');

    return html;
}

// ===== Debug Panel =====

function updateDebugPanel(data) {
    const { metadata, sources } = data;

    const classificationBadge = metadata.classification === 'simple'
        ? '<span class="badge badge-simple">Simple</span>'
        : '<span class="badge badge-complex">Complex</span>';

    const flagsHtml = metadata.evaluator_flags.length > 0
        ? metadata.evaluator_flags.map(f => `<span class="badge badge-flag">${f}</span>`).join(' ')
        : '<span class="badge badge-ok">None</span>';

    const sourcesHtml = sources.length > 0
        ? sources.map(s => `
            <div class="source-item">
                <span>📄 ${s.document}</span>
                ${s.relevance_score ? `<span class="source-score">${(s.relevance_score * 100).toFixed(0)}%</span>` : ''}
            </div>
        `).join('')
        : '<div class="source-item">No sources retrieved</div>';

    debugContent.innerHTML = `
        <div class="debug-card">
            <div class="debug-card-title">Model & Routing</div>
            <div class="debug-row">
                <span class="debug-label">Classification</span>
                ${classificationBadge}
            </div>
            <div class="debug-row">
                <span class="debug-label">Model</span>
                <span class="debug-value">${shortenModelName(metadata.model_used)}</span>
            </div>
        </div>

        <div class="debug-card">
            <div class="debug-card-title">Token Usage</div>
            <div class="debug-row">
                <span class="debug-label">Input</span>
                <span class="debug-value">${metadata.tokens.input.toLocaleString()}</span>
            </div>
            <div class="debug-row">
                <span class="debug-label">Output</span>
                <span class="debug-value">${metadata.tokens.output.toLocaleString()}</span>
            </div>
            <div class="debug-row">
                <span class="debug-label">Latency</span>
                <span class="debug-value">${metadata.latency_ms}ms</span>
            </div>
        </div>

        <div class="debug-card">
            <div class="debug-card-title">Evaluator Flags</div>
            <div style="padding: 4px 0;">
                ${flagsHtml}
            </div>
        </div>

        <div class="debug-card">
            <div class="debug-card-title">Sources (${sources.length} chunks)</div>
            ${sourcesHtml}
        </div>
    `;
}

function shortenModelName(model) {
    if (model.includes('8b')) return 'Llama 3.1 8B';
    if (model.includes('70b')) return 'Llama 3.3 70B';
    return model;
}

// ===== Initialize =====
restoreChatHistory();
chatMessages.scrollTop = chatMessages.scrollHeight;
