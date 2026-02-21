import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged, getIdToken } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";

// Firebase configuration from user
const firebaseConfig = {
    apiKey: "AIzaSyDTBl6qMs5_7dFD4uO7X3VpeNcsdQWQMB4",
    authDomain: "rag-chatbot-27cc6.firebaseapp.com",
    projectId: "rag-chatbot-27cc6",
    storageBucket: "rag-chatbot-27cc6.firebasestorage.app",
    messagingSenderId: "265973368271",
    appId: "1:265973368271:web:1c9f3e377e12a92e047eba",
    measurementId: "G-KNPDGQQX0L"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// ===== DOM Elements =====
const authModal = document.getElementById('authModal');
const googleSignInBtn = document.getElementById('googleSignInBtn');
const userProfile = document.getElementById('userProfile');
const userNameEl = document.getElementById('userName');
const userAvatarEl = document.getElementById('userAvatar');
const signOutBtn = document.getElementById('signOutBtn');

const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');

const conversationsList = document.getElementById('conversationsList');
const debugContent = document.getElementById('debugContent');

// ===== State =====
let currentUser = null;
let currentToken = null;
let currentConversationId = null;
let isLoading = false;

// ===== Auth Listeners =====

onAuthStateChanged(auth, async (user) => {
    if (user) {
        currentUser = user;
        currentToken = await getIdToken(user);

        // Update UI
        authModal.classList.add('hidden');
        userProfile.style.display = 'flex';
        userNameEl.textContent = user.displayName || user.email;
        if (user.photoURL) {
            userAvatarEl.innerHTML = `<img src="${user.photoURL}" alt="avatar" style="width:100%; height:100%; border-radius:50%;">`;
        } else {
            userAvatarEl.textContent = (user.displayName || user.email).charAt(0).toUpperCase();
        }

        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.placeholder = "Ask a question about ClearPath...";

        // Load sidebar data
        await loadConversations();
    } else {
        // User is signed out
        currentUser = null;
        currentToken = null;
        authModal.classList.remove('hidden');
        userProfile.style.display = 'none';

        messageInput.disabled = true;
        sendBtn.disabled = true;
        messageInput.placeholder = "Sign in to ask a question...";

        conversationsList.innerHTML = '';
        startNewConversation();
    }
});

// Auth Actions
googleSignInBtn.addEventListener('click', async () => {
    try {
        await signInWithPopup(auth, provider);
    } catch (error) {
        console.error("Auth error:", error);
        alert("Failed to sign in: " + error.message);
    }
});

signOutBtn.addEventListener('click', (e) => {
    e.preventDefault();
    signOut(auth);
});

// ===== Conversations API =====

async function authenticatedFetch(url, options = {}) {
    if (!currentToken && currentUser) {
        currentToken = await getIdToken(currentUser);
    }

    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${currentToken}`
    };

    return fetch(url, { ...options, headers });
}

async function loadConversations() {
    try {
        const res = await authenticatedFetch('/conversations');
        if (!res.ok) throw new Error("Failed to fetch conversations");
        const convs = await res.json();

        conversationsList.innerHTML = '';

        if (convs.length === 0) {
            startNewConversation();
            return;
        }

        convs.forEach(conv => {
            const div = document.createElement('div');
            div.className = `conv-item ${conv.id === currentConversationId ? 'active' : ''}`;

            const titleSpan = document.createElement('span');
            titleSpan.className = 'conv-title';
            titleSpan.textContent = conv.title || 'New Chat';
            div.appendChild(titleSpan);

            const actions = document.createElement('div');
            actions.className = 'conv-actions';

            const editBtn = document.createElement('button');
            editBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
            `;
            editBtn.onclick = (e) => {
                e.stopPropagation();
                titleSpan.style.display = 'none';
                actions.style.display = 'none';

                const input = document.createElement('input');
                input.className = 'conv-title-input';
                input.value = titleSpan.textContent;

                const saveTitle = async () => {
                    const newTitle = input.value.trim();
                    if (newTitle && newTitle !== conv.title) {
                        try {
                            const res = await authenticatedFetch(`/conversations/${conv.id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ title: newTitle })
                            });
                            if (!res.ok) throw new Error("Failed to rename");
                            titleSpan.textContent = newTitle;
                            conv.title = newTitle;
                        } catch (err) {
                            console.error(err);
                        }
                    }
                    input.remove();
                    titleSpan.style.display = '';
                    actions.style.display = '';
                };

                input.onblur = saveTitle;
                input.onkeydown = (e_down) => {
                    if (e_down.key === 'Enter') saveTitle();
                    if (e_down.key === 'Escape') {
                        input.remove();
                        titleSpan.style.display = '';
                        actions.style.display = '';
                    }
                };

                div.insertBefore(input, actions);
                input.focus();
                input.select();
            };

            const delBtn = document.createElement('button');
            delBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            `;
            delBtn.onclick = (e) => {
                e.stopPropagation();
                editBtn.style.display = 'none';
                delBtn.style.display = 'none';

                const confirmBtn = document.createElement('button');
                confirmBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ff4d4f" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                confirmBtn.onclick = async (e2) => {
                    e2.stopPropagation();
                    await deleteConversation(conv.id);
                };

                const cancelBtn = document.createElement('button');
                cancelBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
                cancelBtn.onclick = (e3) => {
                    e3.stopPropagation();
                    confirmBtn.remove();
                    cancelBtn.remove();
                    editBtn.style.display = '';
                    delBtn.style.display = '';
                };

                actions.appendChild(confirmBtn);
                actions.appendChild(cancelBtn);
            };

            actions.appendChild(editBtn);
            actions.appendChild(delBtn);
            div.appendChild(actions);

            div.onclick = () => selectConversation(conv.id);
            conversationsList.appendChild(div);
        });

        // Select the most recent if nothing is selected
        if (!currentConversationId && convs.length > 0) {
            selectConversation(convs[0].id);
        }

    } catch (error) {
        console.error("Load convos error:", error);
    }
}

async function selectConversation(convId) {
    if (currentConversationId === convId) return;
    currentConversationId = convId;

    // Update active class in sidebar
    document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    // (This works but is simple; we could also re-render the list or find by ID)
    loadConversations(); // lazy refresh

    // Clear chat area
    chatMessages.innerHTML = `
        <div class="message bot-message loading-message">
            <div class="message-avatar bot-avatar">CP</div>
            <div class="message-content" style="padding:4px 12px">
                <div class="loading-dots"><span></span><span></span><span></span></div>
            </div>
        </div>
    `;

    try {
        const res = await authenticatedFetch(`/conversations/${convId}`);
        if (!res.ok) throw new Error("Failed to fetch chat history");
        const history = await res.json();

        chatMessages.innerHTML = ''; // clear loading

        if (history.length === 0) {
            chatMessages.innerHTML = `
                <div class="message bot-message">
                    <div class="message-avatar bot-avatar">CP</div>
                    <div class="message-content">
                        <p>👋 Welcome to ClearPath Support! Ask me anything.</p>
                    </div>
                </div>
            `;
            return;
        }

        history.forEach(msg => {
            const isUser = msg.role === 'user';
            addMessage(msg.content, isUser ? 'user' : 'bot', [], true);
        });

        chatMessages.scrollTop = chatMessages.scrollHeight;

    } catch (error) {
        console.error(error);
        chatMessages.innerHTML = `<div class="message bot-message"><div class="message-content">Failed to load history.</div></div>`;
    }
}

function startNewConversation() {
    currentConversationId = null;
    document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-avatar bot-avatar">CP</div>
            <div class="message-content">
                <p>👋 New chat started. How can I help you today?</p>
            </div>
        </div>
    `;
}

async function renameConversation(convId, newTitle) {
    try {
        const res = await authenticatedFetch(`/conversations/${convId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });
        if (!res.ok) throw new Error("Failed to rename conversation");
        await loadConversations();
    } catch (error) {
        console.error("Rename error:", error);
        alert("Could not rename conversation.");
    }
}

async function deleteConversation(convId) {
    try {
        const res = await authenticatedFetch(`/conversations/${convId}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error("Failed to delete conversation");

        if (currentConversationId === convId) {
            startNewConversation();
        }
        await loadConversations();
    } catch (error) {
        console.error("Delete error:", error);
        alert("Could not delete conversation.");
    }
}

newChatBtn.addEventListener('click', startNewConversation);

// ===== Chat Interface =====

sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
});

async function sendMessage() {
    const question = messageInput.value.trim();
    if (!question || isLoading || !currentUser) return;

    // Add user message to UI
    addMessage(question, 'user');
    messageInput.value = '';
    messageInput.style.height = 'auto';

    isLoading = true;
    sendBtn.disabled = true;
    const loadingEl = addLoadingMessage();

    try {
        if (!currentToken) currentToken = await getIdToken(currentUser);

        const response = await fetch('/query/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentToken}`
            },
            body: JSON.stringify({
                question,
                conversation_id: currentConversationId
            })
        });

        if (!response.ok) {
            if (response.status === 401) {
                // Token expired, refresh and retry could go here, for now just enforce login
                signOut(auth);
                throw new Error("Session expired. Please log in again.");
            }
            throw new Error(`Server error: ${response.status}`);
        }

        loadingEl.remove();
        const botMsg = addMessage('', 'bot');
        const contentDiv = botMsg.querySelector('.message-content div:last-child');

        let fullAnswer = '';
        let streamMeta = {};

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = JSON.parse(line.slice(6));

                if (data.type === 'metadata') {
                    streamMeta = data;
                    // If this was a new conversation, the server created an ID for us.
                    if (!currentConversationId && data.conversation_id) {
                        currentConversationId = data.conversation_id;
                        // Refresh the sidebar to show the new chat title
                        loadConversations();
                    }
                } else if (data.type === 'token') {
                    fullAnswer += data.content;
                    contentDiv.innerHTML = formatText(fullAnswer);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } else if (data.type === 'done') {
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

                    if (data.evaluator_flags && data.evaluator_flags.length > 0) {
                        const warningBadge = document.createElement('div');
                        warningBadge.className = 'warning-badge';
                        warningBadge.textContent = `⚠️ Flagged: ${data.evaluator_flags.join(', ')}`;
                        botMsg.querySelector('.message-content').insertBefore(warningBadge, contentDiv);
                    }
                } else if (data.type === 'error') {
                    contentDiv.textContent = `Error: ${data.content}`;
                }
            }
        }
    } catch (error) {
        if (loadingEl) loadingEl.remove();
        addMessage(`Sorry, something went wrong: ${error.message}`, 'bot', ['error']);
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

function addMessage(text, sender, flags = [], skipScroll = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${sender === 'bot' ? 'bot-avatar' : 'user-avatar-msg'}`;

    // Use Google profile picture if user, otherwise text
    if (sender === 'bot') {
        avatar.textContent = 'CP';
    } else if (currentUser && currentUser.photoURL) {
        avatar.innerHTML = `<img src="${currentUser.photoURL}" alt="U" style="width:100%; height:100%; border-radius:50%;">`;
    } else {
        avatar.textContent = 'You';
    }

    const content = document.createElement('div');
    content.className = 'message-content';

    if (flags.length > 0 && !flags.includes('error')) {
        const warningBadge = document.createElement('div');
        warningBadge.className = 'warning-badge';
        warningBadge.textContent = `⚠️ Flagged: ${flags.join(', ')}`;
        content.appendChild(warningBadge);
    }

    const textDiv = document.createElement('div');
    textDiv.innerHTML = formatText(text);
    content.appendChild(textDiv);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);

    if (!skipScroll) chatMessages.scrollTop = chatMessages.scrollHeight;
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
    content.innerHTML = `<div class="loading-dots"><span></span><span></span><span></span></div>`;

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

function formatText(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:4px;font-size:12px;">$1</code>')
        .replace(/\n/g, '<br>');
}

function updateDebugPanel(data) {
    const { metadata, sources } = data;
    const classificationBadge = metadata.classification === 'simple'
        ? '<span class="badge badge-simple">Simple</span>'
        : '<span class="badge badge-complex">Complex</span>';

    const flagsHtml = metadata.evaluator_flags.length > 0
        ? metadata.evaluator_flags.map(f => `<span class="badge badge-flag">${f}</span>`).join(' ')
        : '<span class="badge badge-ok">None</span>';

    const sourcesHtml = sources.length > 0
        ? sources.map(s => `<div class="source-item"><span>📄 ${s.document}</span>${s.relevance_score ? `<span class="source-score">${(s.relevance_score * 100).toFixed(0)}%</span>` : ''}</div>`).join('')
        : '<div class="source-item">No sources retrieved</div>';

    debugContent.innerHTML = `
        <div class="debug-card">
            <div class="debug-card-title">Model & Routing</div>
            <div class="debug-row"><span class="debug-label">Classification</span>${classificationBadge}</div>
            <div class="debug-row"><span class="debug-label">Model</span><span class="debug-value">${shortenModelName(metadata.model_used)}</span></div>
        </div>
        <div class="debug-card">
            <div class="debug-card-title">Token Usage</div>
            <div class="debug-row"><span class="debug-label">Input</span><span class="debug-value">${metadata.tokens.input.toLocaleString()}</span></div>
            <div class="debug-row"><span class="debug-label">Output</span><span class="debug-value">${metadata.tokens.output.toLocaleString()}</span></div>
            <div class="debug-row"><span class="debug-label">Latency</span><span class="debug-value">${metadata.latency_ms}ms</span></div>
        </div>
        <div class="debug-card">
            <div class="debug-card-title">Evaluator Flags</div>
            <div style="padding: 4px 0;">${flagsHtml}</div>
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
