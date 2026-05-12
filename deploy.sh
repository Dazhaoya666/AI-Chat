#!/bin/bash
# AI Chat 一键部署脚本
# 适用于阿里云轻量化服务器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 打印信息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用 root 用户运行此脚本"
        exit 1
    fi
}

# 检测系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        print_error "无法检测操作系统"
        exit 1
    fi
    print_info "检测到系统: $OS $VERSION"
}

# 安装 Docker
install_docker() {
    if command -v docker &> /dev/null; then
        print_info "Docker 已安装，版本: $(docker -v)"
    else
        print_info "正在安装 Docker..."
        curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
        systemctl start docker
        systemctl enable docker
        print_info "Docker 安装完成"
    fi
}

# 安装 Docker Compose
install_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        print_info "Docker Compose 已安装"
    else
        print_info "正在安装 Docker Compose..."
        ARCH=$(uname -m)
        if [ "$ARCH" = "aarch64" ]; then
            ARCH="arm64"
        fi
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-${ARCH}" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        print_info "Docker Compose 安装完成"
    fi
}

# 克隆代码
clone_repo() {
    if [ -d "/opt/AI-Chat" ]; then
        print_warn "目录 /opt/AI-Chat 已存在，正在拉取最新代码..."
        cd /opt/AI-Chat
        git pull
    else
        print_info "正在克隆代码仓库..."
        cd /opt
        git clone https://github.com/Dazhaoya666/AI-Chat.git
        cd AI-Chat
    fi
}

# 配置环境变量
configure_env() {
    print_info "正在配置环境变量..."

    if [ -f ".env" ]; then
        print_warn ".env 文件已存在，跳过配置"
        return
    fi

    read -p "请输入阿里云百炼 API Key: " api_key

    cat > .env << EOF
OPENAI_API_KEY=${api_key}
EOF

    print_info "环境变量配置完成"
}

# 启动应用
start_app() {
    print_info "正在构建并启动应用..."
    docker-compose up -d --build

    print_info "等待应用启动..."
    sleep 10

    if docker-compose ps | grep -q "healthy"; then
        print_info "应用启动成功！"
        echo ""
        echo "=========================================="
        echo "  访问地址: http://$(curl -s ifconfig.me):8000"
        echo "  查看日志: docker-compose logs -f"
        echo "=========================================="
    else
        print_error "应用启动失败，请查看日志"
        docker-compose logs
        exit 1
    fi
}

# 主函数
main() {
    print_info "=========================================="
    print_info "  AI Chat 一键部署脚本"
    print_info "=========================================="

    check_root
    detect_os
    install_docker
    install_docker_compose
    clone_repo
    configure_env
    start_app

    print_info "部署完成！"
}

main
