# 阿里云轻量化服务器部署指南

## 前置准备

### 1. 服务器配置
- **系统**：Alibaba Cloud Linux / CentOS 7+ / Ubuntu 20.04+
- **配置**：建议 2核4G 及以上
- **端口**：确保安全组开放 80/443/8000 端口

### 2. 登录服务器
```bash
ssh root@你的服务器IP
```

---

## 方案一：Docker 部署（推荐）

### 1. 安装 Docker 和 Docker Compose
```bash
# 安装 Docker（阿里云镜像加速）
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun

# 启动 Docker
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker -v
docker-compose -v
```

### 2. 克隆代码
```bash
cd /opt
git clone https://github.com/Dazhaoya666/AI-Chat.git
cd AI-Chat
```

### 3. 配置环境变量
```bash
# 复制环境变量模板
cat > .env << 'EOF'
OPENAI_API_KEY=你的阿里云百炼API_KEY
EOF
```

### 4. 启动应用
```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

### 5. 访问应用
```
http://你的服务器IP:8000
```

---

## 方案二：原生部署（不使用 Docker）

### 1. 安装 Python 3.11
```bash
# Ubuntu/Debian
apt update
apt install -y python3.11 python3.11-venv python3-pip

# CentOS/Alibaba Cloud Linux
yum install -y python311 python311-pip
```

### 2. 克隆代码
```bash
cd /opt
git clone https://github.com/Dazhaoya666/AI-Chat.git
cd AI-Chat
```

### 3. 创建虚拟环境
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 4. 安装依赖
```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### 5. 初始化数据库
```bash
python init_data.py
```

### 6. 配置环境变量
```bash
export OPENAI_API_KEY="你的阿里云百炼API_KEY"
```

### 7. 启动应用
```bash
# 测试启动
python main.py

# 后台运行
nohup python main.py > app.log 2>&1 &
```

---

## 方案三：使用 Nginx 反向代理（生产环境推荐）

### 1. 安装 Nginx
```bash
# Ubuntu/Debian
apt install -y nginx

# CentOS/Alibaba Cloud Linux
yum install -y nginx
```

### 2. 配置 Nginx
```bash
cat > /etc/nginx/conf.d/ai-chat.conf << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    location /static {
        alias /opt/AI-Chat/static;
        expires 30d;
    }
}
EOF
```

### 3. 启动 Nginx
```bash
nginx -t
systemctl start nginx
systemctl enable nginx
```

---

## 方案四：使用 systemd 服务（生产环境）

### 1. 创建服务文件
```bash
cat > /etc/systemd/system/ai-chat.service << 'EOF'
[Unit]
Description=AI Chat Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/AI-Chat
Environment="OPENAI_API_KEY=你的API_KEY"
ExecStart=/opt/AI-Chat/venv/bin/python /opt/AI-Chat/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 2. 启动服务
```bash
systemctl daemon-reload
systemctl start ai-chat
systemctl enable ai-chat

# 查看状态
systemctl status ai-chat

# 查看日志
journalctl -u ai-chat -f
```

---

## 常用运维命令

### Docker 相关
```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f ai-chat

# 更新代码并重新部署
git pull
docker-compose up -d --build
```

### 原生部署相关
```bash
# 查看进程
ps aux | grep python

# 查看日志
tail -f app.log

# 更新代码
git pull
systemctl restart ai-chat
```

---

## 防火墙配置（如果需要）

### Alibaba Cloud Linux / CentOS
```bash
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

### Ubuntu / Debian
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw reload
```

---

## 阿里云安全组配置

1. 登录阿里云控制台
2. 进入「云服务器 ECS」→ 「实例」→ 「安全组」
3. 添加入方向规则：
   - 端口范围：`80/80`  授权对象：`0.0.0.0/0`
   - 端口范围：`443/443` 授权对象：`0.0.0.0/0`
   - 端口范围：`8000/8000` 授权对象：`0.0.0.0/0`

---

## 故障排查

### 问题：端口被占用
```bash
# 查看端口占用
netstat -tulpn | grep 8000

# 杀掉进程
kill -9 进程ID
```

### 问题：权限不足
```bash
chown -R root:root /opt/AI-Chat
chmod -R 755 /opt/AI-Chat
```

### 问题：API 连接失败
检查 `.env` 文件中的 `OPENAI_API_KEY` 是否正确配置。

---

## 快速开始（一键脚本）

在服务器上执行：
```bash
bash <(curl -s https://raw.githubusercontent.com/Dazhaoya666/AI-Chat/main/deploy.sh)
```
