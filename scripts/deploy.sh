#!/bin/bash

# 双语导师系统部署脚本
# Bilingual Tutor System Deployment Script
#
# ⚠️ 重要声明: 本部署脚本仅用于个人学习系统部署
# 严禁用于任何商业用途或企业级部署
# 
# 🚫 禁止商业部署: 本脚本不得用于商业系统部署
# 🎓 仅限个人学习: 脚本仅支持个人语言学习系统部署
# ⚖️ 法律责任: 违规使用后果自负
# 
# 使用本脚本即表示您同意仅将系统用于个人学习目的

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置变量
APP_NAME="bilingual-tutor"
APP_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/opt/${APP_NAME}/backups"
LOG_DIR="/opt/${APP_NAME}/logs"
DATA_DIR="/opt/${APP_NAME}/data"
CONFIG_DIR="/opt/${APP_NAME}/config"
VENV_DIR="/opt/${APP_NAME}/venv"
SERVICE_NAME="${APP_NAME}.service"
USER="bilingual-tutor"
GROUP="bilingual-tutor"

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi
}

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法确定操作系统版本"
        exit 1
    fi
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$PYTHON_VERSION < 3.8" | bc -l) -eq 1 ]]; then
        log_error "需要Python 3.8或更高版本，当前版本: $PYTHON_VERSION"
        exit 1
    fi
    
    # 检查必需的系统包
    REQUIRED_PACKAGES=("curl" "wget" "git" "sqlite3" "redis-server" "nginx")
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! command -v "$package" &> /dev/null; then
            log_warning "$package 未安装，将尝试安装..."
            apt-get update && apt-get install -y "$package"
        fi
    done
    
    log_success "系统要求检查完成"
}

# 创建用户和组
create_user() {
    log_info "创建应用用户..."
    
    if ! id "$USER" &>/dev/null; then
        useradd --system --home-dir "$APP_DIR" --shell /bin/bash "$USER"
        log_success "用户 $USER 创建成功"
    else
        log_info "用户 $USER 已存在"
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    DIRECTORIES=("$APP_DIR" "$BACKUP_DIR" "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR" "$VENV_DIR")
    
    for dir in "${DIRECTORIES[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done
    
    # 设置目录权限
    chown -R "$USER:$GROUP" "$APP_DIR"
    chmod -R 755 "$APP_DIR"
    chmod -R 750 "$LOG_DIR"
    chmod -R 750 "$DATA_DIR"
    
    log_success "目录结构创建完成"
}

# 安装Python依赖
install_python_dependencies() {
    log_info "安装Python依赖..."
    
    # 创建虚拟环境
    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
        log_info "Python虚拟环境创建完成"
    fi
    
    # 激活虚拟环境并安装依赖
    source "$VENV_DIR/bin/activate"
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装生产环境依赖
    if [[ -f "$APP_DIR/requirements.txt" ]]; then
        pip install -r "$APP_DIR/requirements.txt"
    fi
    
    # 安装生产服务器
    pip install gunicorn supervisor
    
    log_success "Python依赖安装完成"
}

# 配置数据库
setup_database() {
    log_info "配置数据库..."
    
    # 创建数据库目录
    mkdir -p "$DATA_DIR"
    
    # 初始化数据库（如果不存在）
    if [[ ! -f "$DATA_DIR/learning.db" ]]; then
        log_info "初始化数据库..."
        cd "$APP_DIR"
        source "$VENV_DIR/bin/activate"
        python -c "
from bilingual_tutor.storage.database import DatabaseManager
db = DatabaseManager('$DATA_DIR/learning.db')
db.initialize_database()
print('数据库初始化完成')
"
    fi
    
    # 设置数据库权限
    chown "$USER:$GROUP" "$DATA_DIR/learning.db"
    chmod 640 "$DATA_DIR/learning.db"
    
    log_success "数据库配置完成"
}

# 配置Redis
setup_redis() {
    log_info "配置Redis..."
    
    # 启动Redis服务
    systemctl enable redis-server
    systemctl start redis-server
    
    # 检查Redis状态
    if systemctl is-active --quiet redis-server; then
        log_success "Redis服务运行正常"
    else
        log_error "Redis服务启动失败"
        exit 1
    fi
}

# 配置Nginx
setup_nginx() {
    log_info "配置Nginx..."
    
    # 创建Nginx配置文件
    cat > "/etc/nginx/sites-available/$APP_NAME" << EOF
server {
    listen 80;
    server_name _;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 静态文件
    location /static/ {
        alias $APP_DIR/bilingual_tutor/web/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # 应用代理
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # 限制请求大小
    client_max_body_size 10M;
    
    # 日志
    access_log $LOG_DIR/nginx_access.log;
    error_log $LOG_DIR/nginx_error.log;
}
EOF
    
    # 启用站点
    ln -sf "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/"
    
    # 删除默认站点
    rm -f /etc/nginx/sites-enabled/default
    
    # 测试Nginx配置
    nginx -t
    
    # 重启Nginx
    systemctl enable nginx
    systemctl restart nginx
    
    log_success "Nginx配置完成"
}

# 创建systemd服务
create_systemd_service() {
    log_info "创建systemd服务..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME" << EOF
[Unit]
Description=双语导师系统 (Bilingual Tutor System)
After=network.target redis.service
Wants=redis.service

[Service]
Type=exec
User=$USER
Group=$GROUP
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_DIR/bin
Environment=FLASK_ENV=production
Environment=PYTHONPATH=$APP_DIR
ExecStart=$VENV_DIR/bin/gunicorn \\
    --bind 127.0.0.1:5000 \\
    --workers 4 \\
    --worker-class sync \\
    --worker-connections 1000 \\
    --timeout 30 \\
    --keepalive 2 \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --access-logfile $LOG_DIR/gunicorn_access.log \\
    --error-logfile $LOG_DIR/gunicorn_error.log \\
    --log-level info \\
    --capture-output \\
    bilingual_tutor.web.app:app

ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR $LOG_DIR $DATA_DIR
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载systemd配置
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable "$SERVICE_NAME"
    
    log_success "systemd服务创建完成"
}

# 配置日志轮转
setup_log_rotation() {
    log_info "配置日志轮转..."
    
    cat > "/etc/logrotate.d/$APP_NAME" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $GROUP
    postrotate
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
    endscript
}
EOF
    
    log_success "日志轮转配置完成"
}

# 设置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    # 检查ufw是否安装
    if command -v ufw &> /dev/null; then
        # 允许SSH
        ufw allow ssh
        
        # 允许HTTP和HTTPS
        ufw allow 80/tcp
        ufw allow 443/tcp
        
        # 启用防火墙
        ufw --force enable
        
        log_success "防火墙配置完成"
    else
        log_warning "ufw未安装，跳过防火墙配置"
    fi
}

# 创建备份脚本
create_backup_script() {
    log_info "创建备份脚本..."
    
    cat > "$APP_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash

# 双语导师系统备份脚本

BACKUP_DIR="/opt/bilingual-tutor/backups"
DATA_DIR="/opt/bilingual-tutor/data"
LOG_DIR="/opt/bilingual-tutor/logs"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR/database" "$BACKUP_DIR/logs" "$BACKUP_DIR/config"

# 备份数据库
if [[ -f "$DATA_DIR/learning.db" ]]; then
    cp "$DATA_DIR/learning.db" "$BACKUP_DIR/database/learning_${DATE}.db"
    gzip "$BACKUP_DIR/database/learning_${DATE}.db"
    echo "数据库备份完成: learning_${DATE}.db.gz"
fi

# 备份日志（保留最近7天）
find "$LOG_DIR" -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \;
tar -czf "$BACKUP_DIR/logs/logs_${DATE}.tar.gz" -C "$BACKUP_DIR/logs" .
rm -f "$BACKUP_DIR/logs"/*.log
echo "日志备份完成: logs_${DATE}.tar.gz"

# 清理旧备份（保留30天）
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
echo "旧备份清理完成"

echo "备份任务完成: $DATE"
EOF
    
    chmod +x "$APP_DIR/scripts/backup.sh"
    
    # 添加到crontab
    (crontab -u "$USER" -l 2>/dev/null; echo "0 2 * * * $APP_DIR/scripts/backup.sh >> $LOG_DIR/backup.log 2>&1") | crontab -u "$USER" -
    
    log_success "备份脚本创建完成"
}

# 创建监控脚本
create_monitoring_script() {
    log_info "创建监控脚本..."
    
    cat > "$APP_DIR/scripts/monitor.sh" << 'EOF'
#!/bin/bash

# 双语导师系统监控脚本

SERVICE_NAME="bilingual-tutor.service"
LOG_FILE="/opt/bilingual-tutor/logs/monitor.log"
APP_URL="http://localhost/health"

# 日志函数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# 检查服务状态
check_service() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        return 0
    else
        return 1
    fi
}

# 检查HTTP响应
check_http() {
    if curl -f -s "$APP_URL" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# 重启服务
restart_service() {
    log_message "重启服务: $SERVICE_NAME"
    systemctl restart "$SERVICE_NAME"
    sleep 10
}

# 主监控逻辑
main() {
    if ! check_service; then
        log_message "服务未运行，尝试重启"
        restart_service
        
        if check_service; then
            log_message "服务重启成功"
        else
            log_message "服务重启失败"
            exit 1
        fi
    fi
    
    if ! check_http; then
        log_message "HTTP健康检查失败，尝试重启服务"
        restart_service
        
        sleep 10
        if check_http; then
            log_message "HTTP健康检查恢复正常"
        else
            log_message "HTTP健康检查仍然失败"
            exit 1
        fi
    fi
    
    log_message "系统运行正常"
}

main "$@"
EOF
    
    chmod +x "$APP_DIR/scripts/monitor.sh"
    
    # 添加到crontab（每5分钟检查一次）
    (crontab -u "$USER" -l 2>/dev/null; echo "*/5 * * * * $APP_DIR/scripts/monitor.sh") | crontab -u "$USER" -
    
    log_success "监控脚本创建完成"
}

# 部署应用代码
deploy_application() {
    log_info "部署应用代码..."
    
    # 如果是从Git部署
    if [[ -n "$GIT_REPO" ]]; then
        if [[ -d "$APP_DIR/.git" ]]; then
            cd "$APP_DIR"
            git pull origin main
        else
            git clone "$GIT_REPO" "$APP_DIR"
        fi
    fi
    
    # 设置文件权限
    chown -R "$USER:$GROUP" "$APP_DIR"
    find "$APP_DIR" -type f -name "*.py" -exec chmod 644 {} \;
    find "$APP_DIR" -type f -name "*.sh" -exec chmod 755 {} \;
    
    log_success "应用代码部署完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动应用服务
    systemctl start "$SERVICE_NAME"
    
    # 检查服务状态
    sleep 5
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "应用服务启动成功"
    else
        log_error "应用服务启动失败"
        systemctl status "$SERVICE_NAME"
        exit 1
    fi
    
    # 检查HTTP响应
    sleep 10
    if curl -f -s "http://localhost/health" > /dev/null; then
        log_success "HTTP健康检查通过"
    else
        log_warning "HTTP健康检查失败，请检查应用状态"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo
    echo "=========================================="
    echo "双语导师系统部署信息"
    echo "=========================================="
    echo "应用目录: $APP_DIR"
    echo "数据目录: $DATA_DIR"
    echo "日志目录: $LOG_DIR"
    echo "配置目录: $CONFIG_DIR"
    echo "服务名称: $SERVICE_NAME"
    echo "用户: $USER"
    echo "=========================================="
    echo "常用命令:"
    echo "启动服务: systemctl start $SERVICE_NAME"
    echo "停止服务: systemctl stop $SERVICE_NAME"
    echo "重启服务: systemctl restart $SERVICE_NAME"
    echo "查看状态: systemctl status $SERVICE_NAME"
    echo "查看日志: journalctl -u $SERVICE_NAME -f"
    echo "=========================================="
    echo "访问地址: http://$(hostname -I | awk '{print $1}')"
    echo "健康检查: http://$(hostname -I | awk '{print $1}')/health"
    echo "=========================================="
}

# 主函数
main() {
    log_info "开始部署双语导师系统..."
    
    check_root
    check_system_requirements
    create_user
    create_directories
    deploy_application
    install_python_dependencies
    setup_database
    setup_redis
    setup_nginx
    create_systemd_service
    setup_log_rotation
    setup_firewall
    create_backup_script
    create_monitoring_script
    start_services
    show_deployment_info
    
    log_success "双语导师系统部署完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi