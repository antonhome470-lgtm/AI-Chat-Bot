let currentConvId = null;

const MODEL_NAMES = {
    'gemini': '🔮 Gemini',
    'groq-llama': '🦙 LLaMA 3.3',
    'groq-mixtral': '🌀 Mixtral'
};

// ============ ОТПРАВКА ============

async function sendMessage() {
    const input = document.getElementById('userInput');
    const btn = document.getElementById('sendBtn');
    const model = document.getElementById('modelSelect').value;
    const text = input.value.trim();

    if (!text) return;

    // Убираем приветствие
    const welcome = document.getElementById('welcome');
    if (welcome) welcome.remove();

    // Сообщение пользователя
    addMessage(text, 'user');
    input.value = '';
    input.style.height = 'auto';
    btn.disabled = true;

    // Индикатор загрузки
    const typing = addMessage('Думаю... ✨', 'assistant typing');

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                model: model,
                conversation_id: currentConvId
            })
        });

        const data = await res.json();
        typing.remove();

        if (res.ok) {
            addMessage(data.reply, 'assistant', data.model);

            // Обновляем ID
            if (!currentConvId) {
                currentConvId = data.conversation_id;
                addConvToSidebar(
                    data.conversation_id,
                    text.substring(0, 50)
                );
            }
        } else {
            addMessage('⚠️ ' + (data.error || 'Ошибка'), 'assistant');
        }

    } catch (err) {
        typing.remove();
        addMessage('⚠️ Ошибка соединения', 'assistant');
    }

    btn.disabled = false;
    input.focus();
}

// ============ СООБЩЕНИЯ ============

function addMessage(text, role, model) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    // Экранируем HTML
    const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    let html = escaped;

    if (role === 'assistant' && model) {
        const name = MODEL_NAMES[model] || model;
        html += `<div class="model-tag">${name}</div>`;
    }

    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

// ============ ДИАЛОГИ ============

function newChat() {
    currentConvId = null;
    const container = document.getElementById('chatMessages');
    container.innerHTML = `
        <div class="welcome-message" id="welcome">
            <h2>✨ Новый чат</h2>
            <p>Задайте любой вопрос</p>
        </div>
    `;
    document.querySelectorAll('.conv-item')
        .forEach(el => el.classList.remove('active'));
    closeSidebar();
}

async function loadConversation(id) {
    currentConvId = id;
    const container = document.getElementById('chatMessages');
    container.innerHTML = '<div class="message assistant typing">Загрузка...</div>';

    // Активный элемент
    document.querySelectorAll('.conv-item').forEach(el => {
        el.classList.toggle('active', el.dataset.id == id);
    });

    try {
        const res = await fetch(`/api/conversations/${id}/messages`);
        const data = await res.json();
        container.innerHTML = '';

        if (data.messages && data.messages.length) {
            data.messages.forEach(msg => {
                addMessage(msg.content, msg.role, msg.model_used);
            });
        } else {
            container.innerHTML = `
                <div class="welcome-message">
                    <p>Пустой чат. Напишите что-нибудь!</p>
                </div>
            `;
        }
    } catch (err) {
        container.innerHTML = '';
        addMessage('⚠️ Ошибка загрузки', 'assistant');
    }

    closeSidebar();
}

async function deleteConv(id) {
    if (!confirm('Удалить этот чат?')) return;

    await fetch(`/api/conversations/${id}`, { method: 'DELETE' });

    const item = document.querySelector(`.conv-item[data-id="${id}"]`);
    if (item) item.remove();

    if (currentConvId === id) newChat();
}

function addConvToSidebar(id, title) {
    const list = document.getElementById('convList');
    const div = document.createElement('div');
    div.className = 'conv-item active';
    div.dataset.id = id;
    div.onclick = () => loadConversation(id);
    div.innerHTML = `
        <span class="conv-title">${title}</span>
        <button class="conv-delete"
                onclick="event.stopPropagation();
                         deleteConv(${id})">✕</button>
    `;

    document.querySelectorAll('.conv-item')
        .forEach(el => el.classList.remove('active'));
    list.prepend(div);
}

// ============ УТИЛИТЫ ============

function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function sendSuggestion(btn) {
    document.getElementById('userInput').value = btn.textContent.trim();
    sendMessage();
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
}
