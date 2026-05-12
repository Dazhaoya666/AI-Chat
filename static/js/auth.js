// 认证相关功能

// 切换登录/注册标签
function switchTab(tab, event) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.form').forEach(form => form.classList.remove('active'));
    
    // 通过ID查找目标按钮，这是最可靠的方式
    const targetBtn = document.getElementById(tab + 'Tab');
    if (targetBtn) {
        targetBtn.classList.add('active');
    } else if (event && event.target) {
        // 备用方案：通过事件对象
        event.target.classList.add('active');
    }
    
    document.getElementById(tab + 'Form').classList.add('active');
    
    hideMessage();
}

// 显示消息
function showMessage(text, type) {
    const msgEl = document.getElementById('message');
    msgEl.textContent = text;
    msgEl.className = 'message ' + type;
}

function hideMessage() {
    document.getElementById('message').className = 'message';
}

// 登录
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', username);
            window.location.href = '/chat';
        } else {
            showMessage(data.detail || '登录失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误，请重试', 'error');
    }
}

// 注册
async function handleRegister(e) {
    e.preventDefault();
    
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const age = document.getElementById('registerAge').value;
    const gender = document.getElementById('registerGender').value;
    
    if (password !== confirmPassword) {
        showMessage('两次输入的密码不一致', 'error');
        return;
    }
    
    const data = { username, password };
    if (age) data.age = parseInt(age);
    if (gender) data.gender = gender;
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('注册成功！请登录', 'success');
            setTimeout(() => {
                switchTab('login');
                document.getElementById('loginUsername').value = username;
            }, 1000);
        } else {
            showMessage(result.detail || '注册失败', 'error');
        }
    } catch (error) {
        showMessage('网络错误，请重试', 'error');
    }
}

// 绑定事件
document.getElementById('loginForm').addEventListener('submit', handleLogin);
document.getElementById('registerForm').addEventListener('submit', handleRegister);

// 检查是否已登录
if (localStorage.getItem('token')) {
    window.location.href = '/chat';
}
