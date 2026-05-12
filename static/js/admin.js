// 管理后台 v3 - 独立管理员认证 + 朋友圈 + 用户管理

const adminToken = localStorage.getItem('admin_token');
if (!adminToken) {
    window.location.href = '/admin/login';
}

let characters = [];
let worldbooks = [];
let currentWbId = null;

// 页面标题映射
const pageTitles = {
    'characters': '🎭 角色管理',
    'worldbooks': '🌍 世界书',
    'experiences': '📖 经历管理',
    'moments': '📷 朋友圈',
    'users': '👥 用户管理',
    'chatlogs': '💬 聊天记录'
};

document.addEventListener('DOMContentLoaded', () => {
    loadCharacters();
    loadWorldBooks();
    loadMoments();
    loadUsers();
    
    document.getElementById('expDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('characterForm').addEventListener('submit', saveCharacter);
    document.getElementById('experienceForm').addEventListener('submit', saveExperience);
    document.getElementById('worldBookForm').addEventListener('submit', saveWorldBook);
    document.getElementById('loreEntryForm').addEventListener('submit', saveLoreEntry);
    document.getElementById('momentForm').addEventListener('submit', saveMoment);
    document.getElementById('userStatusForm').addEventListener('submit', saveUserStatus);
    document.getElementById('intimacyForm').addEventListener('submit', saveIntimacy);
    document.getElementById('userEditForm').addEventListener('submit', saveUserEdit);
    
    // 状态选择变化时显示/隐藏解封时间
    document.getElementById('userStatus').addEventListener('change', function() {
        document.getElementById('banUntilGroup').style.display = 
            this.value === 'temp_banned' ? 'block' : 'none';
    });
});

function getHeaders() {
    return { 
        'Content-Type': 'application/json', 
        'Authorization': 'Bearer ' + adminToken 
    };
}

// 移动端侧边栏切换
function toggleAdminSidebar() {
    const sidebar = document.getElementById('adminSidebar');
    const overlay = document.getElementById('adminSidebarOverlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('open');
}

function closeAdminSidebar() {
    const sidebar = document.getElementById('adminSidebar');
    const overlay = document.getElementById('adminSidebarOverlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
}

function showSection(section) {
    document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(section + 'Section').classList.add('active');
    // 可能通过点击标签页或者侧边栏调用，都更新激活状态
    const navItem = document.querySelector(`.nav-item[onclick*="${section}"]`);
    if (navItem) navItem.classList.add('active');
    // 更新页面标题
    const titleEl = document.getElementById('adminPageTitle');
    if (titleEl && pageTitles[section]) {
        titleEl.textContent = pageTitles[section];
    }
    if (section === 'experiences') loadCharacterSelects();
    if (section === 'moments') loadMoments();
    if (section === 'users') loadUsers();
    if (section === 'chatlogs') loadChatlogUserSelect();
}

function closeModal(id) { document.getElementById(id).classList.remove('active'); }
window.onclick = e => { if (e.target.classList.contains('modal')) e.target.classList.remove('active'); };

// ========== 角色管理 ==========

async function loadCharacters() {
    try {
        const r = await fetch('/api/characters', { headers: getHeaders() });
        if (r.ok) { 
            characters = await r.json(); 
            renderCharactersTable();
            updateCharacterSelects();
        } else if (r.status === 401) {
            window.location.href = '/admin/login';
        }
    } catch (e) { console.error(e); }
}

function updateCharacterSelects() {
    const opts = characters.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    document.getElementById('experienceCharacterSelect').innerHTML = '<option value="">请选择角色</option>' + opts;
    document.getElementById('expCharacterId').innerHTML = '<option value="">请选择角色</option>' + opts;
    document.getElementById('momentCharacterId').innerHTML = '<option value="">请选择角色</option>' + opts;
}

function renderCharactersTable() {
    document.getElementById('charactersTable').innerHTML = characters.map(c => `
        <tr>
            <td>${c.id}</td>
            <td><strong>${c.name}</strong></td>
            <td>${c.tags ? c.tags.split(',').slice(0,3).map(t=>'<span class="badge badge-secondary">'+t.trim()+'</span>').join(' ') : '-'}</td>
            <td><span class="badge ${c.is_active ? 'badge-success' : 'badge-secondary'}">${c.is_active ? '活跃' : '停用'}</span></td>
            <td>${c.character_version || '-'}</td>
            <td>
                <button class="btn-edit" onclick='editCharacter(${JSON.stringify(c).replace(/'/g,"&#39;")})'>编辑</button>
                <button class="btn-edit" onclick="exportCharacter(${c.id})">导出</button>
                <button class="btn-delete" onclick="deleteCharacter(${c.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

function openCharacterModal() {
    document.getElementById('characterModalTitle').textContent = '新建角色';
    document.getElementById('characterForm').reset();
    document.getElementById('characterId').value = '';
    // 重置头像预览
    document.getElementById('avatarPlaceholder').style.display = '';
    document.getElementById('avatarImage').style.display = 'none';
    document.getElementById('avatarImage').src = '';
    document.getElementById('avatarInput').value = '';
    document.getElementById('characterModal').classList.add('active');
}

function editCharacter(c) {
    document.getElementById('characterModalTitle').textContent = '编辑角色';
    document.getElementById('characterId').value = c.id;
    document.getElementById('charName').value = c.name;
    document.getElementById('charCreator').value = c.creator || '';
    document.getElementById('charTags').value = c.tags || '';
    document.getElementById('charDescription').value = c.description || '';
    document.getElementById('charPersonality').value = c.personality || '';
    document.getElementById('charScenario').value = c.scenario || '';
    document.getElementById('charSystemPrompt').value = c.system_prompt || '';
    document.getElementById('charFirstMes').value = c.first_mes || '';
    document.getElementById('charMesExample').value = c.mes_example || '';
    document.getElementById('charPostHistory').value = c.post_history_instructions || '';
    document.getElementById('charCreatorNotes').value = c.creator_notes || '';
    document.getElementById('charIsActive').checked = c.is_active;
    // 显示头像
    if (c.avatar) {
        document.getElementById('avatarPlaceholder').style.display = 'none';
        document.getElementById('avatarImage').style.display = '';
        document.getElementById('avatarImage').src = c.avatar;
    } else {
        document.getElementById('avatarPlaceholder').style.display = '';
        document.getElementById('avatarImage').style.display = 'none';
    }
    document.getElementById('avatarInput').value = '';
    document.getElementById('characterModal').classList.add('active');
}

function previewAvatar(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('avatarPlaceholder').style.display = 'none';
        document.getElementById('avatarImage').style.display = '';
        document.getElementById('avatarImage').src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function saveCharacter(e) {
    e.preventDefault();
    const id = document.getElementById('characterId').value;
    const data = {
        name: document.getElementById('charName').value,
        description: document.getElementById('charDescription').value,
        personality: document.getElementById('charPersonality').value,
        scenario: document.getElementById('charScenario').value,
        system_prompt: document.getElementById('charSystemPrompt').value,
        first_mes: document.getElementById('charFirstMes').value,
        mes_example: document.getElementById('charMesExample').value,
        post_history_instructions: document.getElementById('charPostHistory').value,
        creator_notes: document.getElementById('charCreatorNotes').value,
        creator: document.getElementById('charCreator').value,
        tags: document.getElementById('charTags').value,
        is_active: document.getElementById('charIsActive').checked,
    };
    try {
        const url = id ? `/api/characters/${id}` : '/api/characters';
        const method = id ? 'PUT' : 'POST';
        const r = await fetch(url, { method, headers: getHeaders(), body: JSON.stringify(data) });
        if (r.ok) {
            const savedChar = await r.json();
            // 如果选择了头像文件，上传头像
            const avatarFile = document.getElementById('avatarInput').files[0];
            if (avatarFile) {
                const formData = new FormData();
                formData.append('file', avatarFile);
                await fetch(`/api/characters/${savedChar.id}/avatar`, {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + adminToken },
                    body: formData
                });
            }
            closeModal('characterModal');
            loadCharacters();
        } else { const err = await r.json(); alert(err.detail || '保存失败'); }
    } catch (e) { alert('网络错误'); }
}

async function deleteCharacter(id) {
    if (!confirm('确定删除此角色？')) return;
    try {
        const r = await fetch(`/api/characters/${id}`, { method: 'DELETE', headers: getHeaders() });
        if (r.ok) loadCharacters(); else alert('删除失败');
    } catch (e) { alert('网络错误'); }
}

async function importCharacter(event) {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const r = await fetch('/api/characters/import', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + adminToken },
            body: formData
        });
        const result = await r.json();
        if (r.ok) { alert(result.message); loadCharacters(); loadWorldBooks(); }
        else alert(result.detail || '导入失败');
    } catch (e) { alert('导入失败'); }
    event.target.value = '';
}

async function exportCharacter(id) {
    try {
        const r = await fetch(`/api/characters/${id}/export`, { headers: getHeaders() });
        if (r.ok) {
            const data = await r.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = (data.data?.name || 'character') + '.json';
            a.click();
            URL.revokeObjectURL(url);
        }
    } catch (e) { alert('导出失败'); }
}

// ========== 世界书管理 ==========

async function loadWorldBooks() {
    try {
        const r = await fetch('/api/worldbooks', { headers: getHeaders() });
        if (r.ok) { worldbooks = await r.json(); renderWorldBooksTable(); }
    } catch (e) { console.error(e); }
}

function renderWorldBooksTable() {
    document.getElementById('worldbooksTable').innerHTML = worldbooks.map(wb => `
        <tr>
            <td>${wb.id}</td>
            <td><strong>${wb.name}</strong></td>
            <td>${(wb.description || '').substring(0, 40)}...</td>
            <td><span class="badge badge-secondary">${wb.entry_count} 条</span></td>
            <td>${wb.scan_depth}</td>
            <td>
                <button class="btn-edit" onclick="showLoreEntries(${wb.id})">条目</button>
                <button class="btn-edit" onclick="showWbBindings(${wb.id})">绑定</button>
                <button class="btn-edit" onclick="exportWorldBook(${wb.id})">导出</button>
                <button class="btn-delete" onclick="deleteWorldBook(${wb.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

function openWorldBookModal() {
    document.getElementById('wbModalTitle').textContent = '新建世界书';
    document.getElementById('worldBookForm').reset();
    document.getElementById('wbId').value = '';
    document.getElementById('wbScanDepth').value = '50';
    document.getElementById('wbTokenBudget').value = '2048';
    document.getElementById('wbRecursive').checked = true;
    document.getElementById('worldBookModal').classList.add('active');
}

async function saveWorldBook(e) {
    e.preventDefault();
    const id = document.getElementById('wbId').value;
    const data = {
        name: document.getElementById('wbName').value,
        description: document.getElementById('wbDescription').value,
        scan_depth: parseInt(document.getElementById('wbScanDepth').value),
        token_budget: parseInt(document.getElementById('wbTokenBudget').value),
        recursive_scanning: document.getElementById('wbRecursive').checked,
    };
    try {
        const url = id ? `/api/worldbooks/${id}` : '/api/worldbooks';
        const method = id ? 'PUT' : 'POST';
        const r = await fetch(url, { method, headers: getHeaders(), body: JSON.stringify(data) });
        if (r.ok) { closeModal('worldBookModal'); loadWorldBooks(); }
        else { const err = await r.json(); alert(err.detail || '保存失败'); }
    } catch (e) { alert('网络错误'); }
}

async function deleteWorldBook(id) {
    if (!confirm('确定删除？')) return;
    try {
        const r = await fetch(`/api/worldbooks/${id}`, { method: 'DELETE', headers: getHeaders() });
        if (r.ok) { loadWorldBooks(); document.getElementById('loreEntriesPanel').style.display = 'none'; document.getElementById('wbBindPanel').style.display = 'none'; }
        else alert('删除失败');
    } catch (e) { alert('网络错误'); }
}

async function importWorldBook(event) {
    const file = event.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const r = await fetch('/api/worldbooks/import', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + adminToken },
            body: formData
        });
        const result = await r.json();
        if (r.ok) { alert(result.message); loadWorldBooks(); }
        else alert(result.detail || '导入失败');
    } catch (e) { alert('导入失败'); }
    event.target.value = '';
}

async function exportWorldBook(id) {
    try {
        const r = await fetch(`/api/worldbooks/${id}/export`, { headers: getHeaders() });
        if (r.ok) {
            const data = await r.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = (data.name || 'worldbook') + '.json';
            a.click();
            URL.revokeObjectURL(url);
        }
    } catch (e) { alert('导出失败'); }
}

async function showLoreEntries(wbId) {
    currentWbId = wbId;
    const wb = worldbooks.find(w => w.id === wbId);
    document.getElementById('loreEntriesTitle').textContent = `${wb.name} - 条目列表`;
    document.getElementById('loreEntriesPanel').style.display = 'block';
    document.getElementById('wbBindPanel').style.display = 'none';
    try {
        const r = await fetch(`/api/worldbooks/${wbId}/entries`, { headers: getHeaders() });
        if (r.ok) {
            const entries = await r.json();
            renderLoreEntries(entries);
        }
    } catch (e) {}
}

function renderLoreEntries(entries) {
    document.getElementById('loreEntriesTable').innerHTML = entries.map(e => `
        <tr>
            <td>${e.keys}</td>
            <td>${e.secondary_keys || '-'}</td>
            <td>${(e.content || '').substring(0, 50)}...</td>
            <td>${e.constant ? '✅' : '❌'}</td>
            <td>${e.enabled ? '✅' : '❌'}</td>
            <td>${e.position}</td>
            <td>
                <button class="btn-edit" onclick='editLoreEntry(${JSON.stringify(e).replace(/'/g,"&#39;")})'>编辑</button>
                <button class="btn-delete" onclick="deleteLoreEntry(${e.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

function openLoreEntryModal(entry = null) {
    document.getElementById('loreModalTitle').textContent = entry ? '编辑条目' : '添加条目';
    document.getElementById('loreEntryId').value = entry ? entry.id : '';
    document.getElementById('loreKeys').value = entry ? entry.keys : '';
    document.getElementById('loreSecondaryKeys').value = entry ? entry.secondary_keys : '';
    document.getElementById('loreContent').value = entry ? entry.content : '';
    document.getElementById('loreComment').value = entry ? entry.comment : '';
    document.getElementById('lorePosition').value = entry ? entry.position : 'before_char';
    document.getElementById('lorePriority').value = entry ? entry.priority : 10;
    document.getElementById('loreInsertionOrder').value = entry ? entry.insertion_order : 100;
    document.getElementById('loreProbability').value = entry ? entry.probability : 100;
    document.getElementById('loreConstant').checked = entry ? entry.constant : false;
    document.getElementById('loreSelective').checked = entry ? entry.selective : false;
    document.getElementById('loreCaseSensitive').checked = entry ? entry.case_sensitive : false;
    document.getElementById('loreUseRegex').checked = entry ? entry.use_regex : false;
    document.getElementById('loreEnabled').checked = entry ? entry.enabled : true;
    document.getElementById('loreEntryModal').classList.add('active');
}

function editLoreEntry(entry) { openLoreEntryModal(entry); }

async function saveLoreEntry(e) {
    e.preventDefault();
    if (!currentWbId) { alert('请先选择世界书'); return; }
    const id = document.getElementById('loreEntryId').value;
    const data = {
        keys: document.getElementById('loreKeys').value,
        secondary_keys: document.getElementById('loreSecondaryKeys').value,
        content: document.getElementById('loreContent').value,
        comment: document.getElementById('loreComment').value,
        position: document.getElementById('lorePosition').value,
        priority: parseInt(document.getElementById('lorePriority').value),
        insertion_order: parseInt(document.getElementById('loreInsertionOrder').value),
        probability: parseInt(document.getElementById('loreProbability').value),
        constant: document.getElementById('loreConstant').checked,
        selective: document.getElementById('loreSelective').checked,
        case_sensitive: document.getElementById('loreCaseSensitive').checked,
        use_regex: document.getElementById('loreUseRegex').checked,
        enabled: document.getElementById('loreEnabled').checked,
    };
    try {
        let r;
        if (id) {
            r = await fetch(`/api/lore-entries/${id}`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify(data) });
        } else {
            r = await fetch(`/api/worldbooks/${currentWbId}/entries`, { method: 'POST', headers: getHeaders(), body: JSON.stringify(data) });
        }
        if (r.ok) { closeModal('loreEntryModal'); showLoreEntries(currentWbId); loadWorldBooks(); }
        else { const err = await r.json(); alert(err.detail || '保存失败'); }
    } catch (e) { alert('网络错误'); }
}

async function deleteLoreEntry(id) {
    if (!confirm('确定删除？')) return;
    try {
        const r = await fetch(`/api/lore-entries/${id}`, { method: 'DELETE', headers: getHeaders() });
        if (r.ok && currentWbId) { showLoreEntries(currentWbId); loadWorldBooks(); }
        else alert('删除失败');
    } catch (e) { alert('网络错误'); }
}

async function showWbBindings(wbId) {
    currentWbId = wbId;
    const wb = worldbooks.find(w => w.id === wbId);
    document.getElementById('loreEntriesPanel').style.display = 'none';
    document.getElementById('wbBindPanel').style.display = 'block';
    
    let html = '<p style="margin-bottom:10px;color:#666;">将此世界书绑定到角色</p>';
    for (const char of characters) {
        try {
            const r = await fetch(`/api/characters/${char.id}/worldbooks`, { headers: getHeaders() });
            if (r.ok) {
                const bound = await r.json();
                const isBound = bound.some(b => b.id === wbId);
                html += `
                    <div class="bind-item">
                        <div class="bind-info"><span>🎭</span><strong>${char.name}</strong></div>
                        <div class="bind-actions">
                            ${isBound 
                                ? `<button class="btn-unbind" onclick="unbindWb(${char.id}, ${wbId})">解除绑定</button>`
                                : `<button class="btn-bind" onclick="bindWb(${char.id}, ${wbId})">绑定</button>`
                            }
                        </div>
                    </div>
                `;
            }
        } catch (e) {}
    }
    document.getElementById('wbBindContent').innerHTML = html;
}

async function bindWb(charId, wbId) {
    try {
        const r = await fetch(`/api/characters/${charId}/worldbooks/${wbId}`, { method: 'POST', headers: getHeaders() });
        if (r.ok) showWbBindings(wbId);
        else alert('绑定失败');
    } catch (e) { alert('网络错误'); }
}

async function unbindWb(charId, wbId) {
    try {
        const r = await fetch(`/api/characters/${charId}/worldbooks/${wbId}`, { method: 'DELETE', headers: getHeaders() });
        if (r.ok) showWbBindings(wbId);
        else alert('解除绑定失败');
    } catch (e) { alert('网络错误'); }
}

// ========== 经历管理 ==========

async function loadCharacterSelects() {
    // 已在 loadCharacters 中更新
}

async function loadExperiences() {
    const cid = document.getElementById('experienceCharacterSelect').value;
    if (!cid) { document.getElementById('experiencesTable').innerHTML = ''; return; }
    try {
        const r = await fetch(`/api/characters/${cid}/experiences`, { headers: getHeaders() });
        if (r.ok) {
            const exps = await r.json();
            document.getElementById('experiencesTable').innerHTML = exps.map(exp => `
                <tr><td>${new Date(exp.date).toLocaleDateString()}</td><td>${exp.content}</td>
                <td><button class="btn-delete" onclick="deleteExperience(${exp.id})">删除</button></td></tr>
            `).join('');
        }
    } catch (e) {}
}

function openExperienceModal() {
    loadCharacters();
    document.getElementById('experienceForm').reset();
    document.getElementById('expDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('experienceModal').classList.add('active');
}

async function saveExperience(e) {
    e.preventDefault();
    const data = {
        character_id: parseInt(document.getElementById('expCharacterId').value),
        content: document.getElementById('expContent').value,
        date: new Date(document.getElementById('expDate').value).toISOString()
    };
    try {
        const r = await fetch('/api/experiences', { method: 'POST', headers: getHeaders(), body: JSON.stringify(data) });
        if (r.ok) { closeModal('experienceModal'); if (document.getElementById('experienceCharacterSelect').value) loadExperiences(); }
        else { const err = await r.json(); alert(err.detail || '保存失败'); }
    } catch (e) { alert('网络错误'); }
}

async function deleteExperience(id) {
    if (!confirm('确定删除？')) return;
    try {
        const r = await fetch(`/api/experiences/${id}`, { method: 'DELETE', headers: getHeaders() });
        if (r.ok) loadExperiences(); else alert('删除失败');
    } catch (e) { alert('网络错误'); }
}

// ========== 朋友圈管理 ==========

async function loadMoments() {
    try {
        const r = await fetch('/api/moments', { headers: getHeaders() });
        if (r.ok) {
            const moments = await r.json();
            renderMomentsTable(moments);
        }
    } catch (e) {}
}

function renderMomentsTable(moments) {
    document.getElementById('momentsTable').innerHTML = moments.map(m => `
        <tr>
            <td>${m.id}</td>
            <td>${m.character_name}</td>
            <td>${m.content.substring(0, 50)}${m.content.length > 50 ? '...' : ''}</td>
            <td>❤️ ${m.likes_count}</td>
            <td>${new Date(m.created_at).toLocaleString()}</td>
            <td><button class="btn-delete" onclick="deleteMoment(${m.id})">删除</button></td>
        </tr>
    `).join('');
}

function openMomentModal() {
    loadCharacters();
    document.getElementById('momentForm').reset();
    document.getElementById('imagePreview').innerHTML = '';
    document.getElementById('momentModal').classList.add('active');
    
    // 图片预览
    document.getElementById('momentImages').onchange = function(e) {
        const preview = document.getElementById('imagePreview');
        preview.innerHTML = '';
        const files = Array.from(e.target.files).slice(0, 9);
        files.forEach(file => {
            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.style.cssText = 'width:80px;height:80px;object-fit:cover;border-radius:6px;border:1px solid #ddd;';
            preview.appendChild(img);
        });
    };
}

async function saveMoment(e) {
    e.preventDefault();
    const formData = new FormData();
    formData.append('character_id', document.getElementById('momentCharacterId').value);
    formData.append('content', document.getElementById('momentContent').value);
    
    const files = document.getElementById('momentImages').files;
    for (let i = 0; i < files.length && i < 9; i++) {
        formData.append('images', files[i]);
    }
    
    try {
        const r = await fetch('/api/moments', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + adminToken },
            body: formData
        });
        if (r.ok) { closeModal('momentModal'); loadMoments(); }
        else { 
            let errMsg = '发布失败';
            try {
                const err = await r.json();
                if (typeof err.detail === 'string') {
                    errMsg = err.detail;
                } else if (Array.isArray(err.detail)) {
                    errMsg = err.detail.map(e => e.msg || JSON.stringify(e)).join(', ');
                } else {
                    errMsg = JSON.stringify(err);
                }
            } catch(e) {}
            alert(errMsg); 
        }
    } catch (e) { alert('网络错误'); }
}

async function deleteMoment(id) {
    if (!confirm('确定删除此动态？')) return;
    try {
        const r = await fetch(`/api/moments/${id}`, { method: 'DELETE', headers: getHeaders() });
        if (r.ok) loadMoments(); else alert('删除失败');
    } catch (e) { alert('网络错误'); }
}

// ========== 用户管理 ==========

async function loadUsers() {
    try {
        const r = await fetch('/api/admin/users', { headers: getHeaders() });
        if (r.ok) {
            const users = await r.json();
            renderUsersTable(users);
        }
    } catch (e) {}
}

function renderUsersTable(users) {
    document.getElementById('usersTable').innerHTML = users.map(u => {
        let statusClass = 'status-active';
        let statusText = '正常';
        if (u.status === 'temp_banned') { statusClass = 'status-temp'; statusText = '临时封禁'; }
        if (u.status === 'banned') { statusClass = 'status-banned'; statusText = '永久封禁'; }
        
        return `
        <tr>
            <td>${u.id}</td>
            <td><strong>${u.username}</strong></td>
            <td>${u.age || '-'}</td>
            <td>${u.gender || '-'}</td>
            <td>${u.intimacy.toFixed(1)}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>${new Date(u.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn-edit" onclick='openUserEditModal(${JSON.stringify(u).replace(/'/g,"&#39;")})'>编辑</button>
                <button class="btn-edit" onclick='openUserStatusModal(${JSON.stringify(u).replace(/'/g,"&#39;")})'>状态</button>
                <button class="btn-edit" onclick='openIntimacyModal(${u.id}, "${u.username}", ${u.intimacy})'>亲密度</button>
                ${u.username !== 'admin' ? `<button class="btn-delete" onclick="deleteUser(${u.id})">删除</button>` : '-'}
            </td>
        </tr>
    `}).join('');
}

function openUserStatusModal(user) {
    document.getElementById('statusUserId').value = user.id;
    document.getElementById('statusUsername').value = user.username;
    document.getElementById('userStatus').value = user.status;
    document.getElementById('banReason').value = user.ban_reason || '';
    if (user.ban_until) {
        const date = new Date(user.ban_until);
        date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
        document.getElementById('banUntil').value = date.toISOString().slice(0, 16);
    } else {
        document.getElementById('banUntil').value = '';
    }
    document.getElementById('banUntilGroup').style.display = user.status === 'temp_banned' ? 'block' : 'none';
    document.getElementById('userStatusModal').classList.add('active');
}

async function saveUserStatus(e) {
    e.preventDefault();
    const userId = document.getElementById('statusUserId').value;
    const status = document.getElementById('userStatus').value;
    const banUntilVal = document.getElementById('banUntil').value;
    const data = {
        status: status,
        ban_until: status === 'temp_banned' && banUntilVal ? new Date(banUntilVal).toISOString() : null,
        ban_reason: document.getElementById('banReason').value
    };
    try {
        const r = await fetch(`/api/admin/users/${userId}/status`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify(data) });
        if (r.ok) { closeModal('userStatusModal'); loadUsers(); }
        else { const err = await r.json(); alert(err.detail || '保存失败'); }
    } catch (e) { alert('网络错误'); }
}

function openIntimacyModal(userId, username, currentValue) {
    document.getElementById('intimacyUserId').value = userId;
    document.getElementById('intimacyUsername').value = username;
    document.getElementById('intimacyValue').value = currentValue;
    document.getElementById('intimacyModal').classList.add('active');
}

async function saveIntimacy(e) {
    e.preventDefault();
    const userId = document.getElementById('intimacyUserId').value;
    const data = { intimacy: parseFloat(document.getElementById('intimacyValue').value) };
    try {
        const r = await fetch(`/api/admin/users/${userId}/intimacy`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify(data) });
        if (r.ok) { closeModal('intimacyModal'); loadUsers(); }
        else { const err = await r.json(); alert(err.detail || '保存失败'); }
    } catch (e) { alert('网络错误'); }
}

async function deleteUser(userId) {
    if (!confirm('确定删除此用户？此操作不可恢复！')) return;
    try {
        const r = await fetch(`/api/admin/users/${userId}`, { method: 'DELETE', headers: getHeaders() });
        if (r.ok) loadUsers(); else { const err = await r.json(); alert(err.detail || '删除失败'); }
    } catch (e) { alert('网络错误'); }
}

async function loadChatlogUserSelect() {
    try {
        const r = await fetch('/api/admin/users', { headers: getHeaders() });
        if (r.ok) {
            const users = await r.json();
            const nonAdmins = users.filter(u => u.username !== 'admin');
            document.getElementById('chatlogUserSelect').innerHTML = 
                '<option value="">请选择用户</option>' + 
                nonAdmins.map(u => `<option value="${u.id}">${u.username}</option>`).join('');
        }
    } catch (e) { console.error(e); }
}

async function loadUserChatLogs() {
    const userId = document.getElementById('chatlogUserSelect').value;
    const container = document.getElementById('chatlogContainer');
    
    if (!userId) {
        container.innerHTML = '<div class="chat-log-empty">请选择用户查看聊天记录</div>';
        return;
    }
    
    try {
        const r = await fetch(`/api/admin/users/${userId}/messages`, { headers: getHeaders() });
        if (r.ok) {
            const messages = await r.json();
            if (messages.length === 0) {
                container.innerHTML = '<div class="chat-log-empty">该用户暂无聊天记录</div>';
            } else {
                container.innerHTML = messages.map(m => `
                    <div class="chat-log-item ${m.is_user ? 'chat-log-user' : 'chat-log-ai'}">
                        <div class="chat-log-content">${escapeHtml(m.content)}</div>
                        <div class="chat-log-meta">
                            ${m.is_user ? '用户' : m.character_name} · ${formatDateTime(m.created_at)}
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (e) { 
        container.innerHTML = '<div class="chat-log-empty">加载失败</div>'; 
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDateTime(dateStr) {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

function openUserEditModal(user) {
    document.getElementById('editUserId').value = user.id;
    document.getElementById('editUsername').value = user.username;
    document.getElementById('editAge').value = user.age || '';
    document.getElementById('editGender').value = user.gender || '';
    document.getElementById('userEditModal').classList.add('active');
}

async function saveUserEdit(e) {
    e.preventDefault();
    const userId = document.getElementById('editUserId').value;
    const age = document.getElementById('editAge').value;
    const gender = document.getElementById('editGender').value;
    const data = {};
    if (age) data.age = parseInt(age);
    if (gender) data.gender = gender;
    try {
        const r = await fetch(`/api/admin/users/${userId}`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify(data) });
        if (r.ok) { closeModal('userEditModal'); loadUsers(); }
        else { const err = await r.json(); alert(err.detail || '保存失败'); }
    } catch (e) { alert('网络错误'); }
}

function logout() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_username');
    window.location.href = '/admin/login';
}
