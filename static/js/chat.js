// 聊天页面功能 - 用户版（无管理功能、无亲密度显示）

let currentCharacter = null;
let isLoading = false;

// 检查登录状态
const token = localStorage.getItem('token');
if (!token) {
    window.location.href = '/';
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadUserInfo();
    loadCharacters();
});

// 获取请求头
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    };
}

// 加载用户信息
async function loadUserInfo() {
    const username = localStorage.getItem('username') || 'User';
    const el = document.getElementById('username');
    if (el) el.textContent = username;
}

// 加载角色列表
async function loadCharacters() {
    try {
        const response = await fetch('/api/characters/active', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (response.ok) {
            const characters = await response.json();
            renderCharacterList(characters);
            
            // 自动选择第一个活跃角色
            if (characters.length > 0 && !currentCharacter) {
                selectCharacter(characters[0]);
            }
        } else if (response.status === 401) {
            window.location.href = '/';
        }
    } catch (error) {
        console.error('加载角色列表失败:', error);
    }
}

// 获取角色头像HTML
function getAvatarHtml(avatar, fallback) {
    if (avatar) {
        return `<img src="${avatar}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" alt="">`;
    }
    return fallback || '🎭';
}

// 渲染角色列表
function renderCharacterList(characters) {
    const container = document.getElementById('characterList');
    if (!container) return;
    container.innerHTML = characters.map(char => `
        <div class="character-item ${currentCharacter?.id === char.id ? 'active' : ''}" 
             onclick='selectCharacter(${JSON.stringify(char).replace(/'/g, "&#39;")})'>
            <div class="avatar">${getAvatarHtml(char.avatar, '🎭')}</div>
            <div class="info">
                <div class="name">${escapeHtml(char.name)}</div>
            </div>
        </div>
    `).join('');
}

// 选择角色
function selectCharacter(character) {
    currentCharacter = character;
    
    // 更新UI
    const nameEl = document.getElementById('characterName');
    const descEl = document.getElementById('characterDesc');
    const avatarEl = document.getElementById('characterAvatar');
    if (nameEl) nameEl.textContent = character.name;
    if (descEl) descEl.textContent = '点击头像去朋友圈看看吧~';
    if (avatarEl) avatarEl.innerHTML = getAvatarHtml(character.avatar, '🎭');
    
    // 更新角色列表选中状态
    document.querySelectorAll('.character-item').forEach(el => el.classList.remove('active'));
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
    
    // 加载历史消息
    loadMessages();
}

// 加载历史消息
async function loadMessages() {
    if (!currentCharacter) return;
    
    try {
        const response = await fetch(`/api/messages?character_id=${currentCharacter.id}&limit=50`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (response.ok) {
            const messages = await response.json();
            renderMessages(messages);
        }
    } catch (error) {
        console.error('加载消息失败:', error);
    }
}

// 渲染消息
function renderMessages(messages) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    if (messages.length === 0) {
        container.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-content">
                    <h2>👋 开始和 ${escapeHtml(currentCharacter?.name || 'AI')} 聊天吧</h2>
                    <p>发送消息开始你们的对话~</p>
                </div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = messages.map(msg => createMessageHTML(msg)).join('');
    scrollToBottom();
}

// 创建消息HTML
function createMessageHTML(msg) {
    const isUser = msg.is_user;
    const time = new Date(msg.created_at).toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    return `
        <div class="message-item ${isUser ? 'user' : 'ai'}">
            <div class="message-avatar">${isUser ? '👤' : getAvatarHtml(currentCharacter?.avatar, '🎭')}</div>
            <div>
                <div class="message-content">${escapeHtml(msg.content)}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
}

// 发送消息
async function sendMessage() {
    if (isLoading) return;
    
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    if (!currentCharacter) {
        alert('请先选择一个角色');
        return;
    }
    
    isLoading = true;
    input.value = '';
    
    // 立即显示用户消息
    const container = document.getElementById('chatMessages');
    if (container.querySelector('.welcome-message')) {
        container.innerHTML = '';
    }
    
    const tempUserMsg = {
        content: message,
        is_user: true,
        created_at: new Date().toISOString()
    };
    container.insertAdjacentHTML('beforeend', createMessageHTML(tempUserMsg));
    scrollToBottom();
    
    // 显示加载中
    const loadingId = 'loading-' + Date.now();
    container.insertAdjacentHTML('beforeend', `
        <div class="message-item ai" id="${loadingId}">
            <div class="message-avatar">${getAvatarHtml(currentCharacter?.avatar, '🎭')}</div>
            <div>
                <div class="message-content">
                    <span class="loading"></span> 正在输入...
                </div>
            </div>
        </div>
    `);
    scrollToBottom();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({
                message: message,
                character_id: currentCharacter.id
            })
        });
        
        // 移除加载中
        document.getElementById(loadingId)?.remove();
        
        if (response.ok) {
            const data = await response.json();
            
            // 显示AI回复
            container.insertAdjacentHTML('beforeend', createMessageHTML(data.ai_message));
            scrollToBottom();
        } else if (response.status === 403) {
            const error = await response.json();
            alert(error.detail || '账号已被封禁');
            window.location.href = '/';
        } else {
            const error = await response.json();
            alert(error.detail || '发送失败');
        }
    } catch (error) {
        document.getElementById(loadingId)?.remove();
        alert('网络错误，请重试');
    } finally {
        isLoading = false;
    }
}

// 处理键盘事件
function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

// 滚动到底部
function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    if (container) container.scrollTop = container.scrollHeight;
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 跳转到朋友圈
function goToMoments() {
    window.location.href = '/moments';
}

// 退出登录
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    window.location.href = '/';
}
