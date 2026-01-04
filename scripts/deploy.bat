@echo off
REM 双语导师系统Windows部署脚本
REM Bilingual Tutor System Windows Deployment Script
REM
REM ⚠️ 重要声明: 本部署脚本仅用于个人学习系统部署
REM 严禁用于任何商业用途或企业级部署
REM 
REM 🚫 禁止商业部署: 本脚本不得用于商业系统部署
REM 🎓 仅限个人学习: 脚本仅支持个人语言学习系统部署
REM ⚖️ 法律责任: 违规使用后果自负
REM 
REM 使用本脚本即表示您同意仅将系统用于个人学习目的

setlocal enabledelayedexpansion

REM 配置变量
set APP_NAME=bilingual-tutor
set APP_DIR=C:\%APP_NAME%
set BACKUP_DIR=%APP_DIR%\backups
set LOG_DIR=%APP_DIR%\logs
set DATA_DIR=%APP_DIR%\data
set CONFIG_DIR=%APP_DIR%\config
set VENV_DIR=%APP_DIR%\venv
set SERVICE_NAME=BilingualTutor

REM 颜色定义（Windows 10+）
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM 日志函数
:log_info
echo %BLUE%[INFO]%NC% %~1
goto :eof

:log_success
echo %GREEN%[SUCCESS]%NC% %~1
goto :eof

:log_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:log_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM 检查管理员权限
:check_admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    call :log_error "此脚本需要管理员权限运行"
    echo 请右键点击脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)
goto :eof

REM 检查系统要求
:check_system_requirements
call :log_info "检查系统要求..."

REM 检查Python版本
python --version >nul 2>&1
if %errorLevel% neq 0 (
    call :log_error "Python 未安装或未添加到PATH"
    echo 请从 https://www.python.org/downloads/ 下载并安装Python 3.8+
    pause
    exit /b 1
)

REM 获取Python版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
call :log_info "Python版本: %PYTHON_VERSION%"

REM 检查pip
pip --version >nul 2>&1
if %errorLevel% neq 0 (
    call :log_error "pip 未安装"
    exit /b 1
)

REM 检查Git（可选）
git --version >nul 2>&1
if %errorLevel% neq 0 (
    call :log_warning "Git 未安装，无法从仓库部署"
) else (
    call :log_info "Git 可用"
)

call :log_success "系统要求检查完成"
goto :eof

REM 创建目录结构
:create_directories
call :log_info "创建目录结构..."

if not exist "%APP_DIR%" mkdir "%APP_DIR%"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%VENV_DIR%" mkdir "%VENV_DIR%"
if not exist "%APP_DIR%\scripts" mkdir "%APP_DIR%\scripts"

call :log_success "目录结构创建完成"
goto :eof

REM 安装Python依赖
:install_python_dependencies
call :log_info "安装Python依赖..."

REM 创建虚拟环境
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    python -m venv "%VENV_DIR%"
    call :log_info "Python虚拟环境创建完成"
)

REM 激活虚拟环境
call "%VENV_DIR%\Scripts\activate.bat"

REM 升级pip
python -m pip install --upgrade pip

REM 安装生产环境依赖
if exist "%APP_DIR%\requirements.txt" (
    pip install -r "%APP_DIR%\requirements.txt"
)

REM 安装Windows服务依赖
pip install pywin32 waitress

call :log_success "Python依赖安装完成"
goto :eof

REM 配置数据库
:setup_database
call :log_info "配置数据库..."

REM 初始化数据库（如果不存在）
if not exist "%DATA_DIR%\learning.db" (
    call :log_info "初始化数据库..."
    cd /d "%APP_DIR%"
    call "%VENV_DIR%\Scripts\activate.bat"
    python -c "from bilingual_tutor.storage.database import DatabaseManager; db = DatabaseManager('%DATA_DIR%\\learning.db'); db.initialize_database(); print('数据库初始化完成')"
)

call :log_success "数据库配置完成"
goto :eof

REM 创建Windows服务
:create_windows_service
call :log_info "创建Windows服务..."

REM 创建服务启动脚本
echo @echo off > "%APP_DIR%\scripts\start_service.bat"
echo cd /d "%APP_DIR%" >> "%APP_DIR%\scripts\start_service.bat"
echo call "%VENV_DIR%\Scripts\activate.bat" >> "%APP_DIR%\scripts\start_service.bat"
echo set FLASK_ENV=production >> "%APP_DIR%\scripts\start_service.bat"
echo set PYTHONPATH=%APP_DIR% >> "%APP_DIR%\scripts\start_service.bat"
echo waitress-serve --host=127.0.0.1 --port=5000 --threads=4 bilingual_tutor.web.app:app >> "%APP_DIR%\scripts\start_service.bat"

REM 创建服务安装脚本
echo import win32serviceutil > "%APP_DIR%\scripts\service_installer.py"
echo import win32service >> "%APP_DIR%\scripts\service_installer.py"
echo import win32event >> "%APP_DIR%\scripts\service_installer.py"
echo import subprocess >> "%APP_DIR%\scripts\service_installer.py"
echo import os >> "%APP_DIR%\scripts\service_installer.py"
echo. >> "%APP_DIR%\scripts\service_installer.py"
echo class BilingualTutorService(win32serviceutil.ServiceFramework): >> "%APP_DIR%\scripts\service_installer.py"
echo     _svc_name_ = "%SERVICE_NAME%" >> "%APP_DIR%\scripts\service_installer.py"
echo     _svc_display_name_ = "双语导师系统服务" >> "%APP_DIR%\scripts\service_installer.py"
echo     _svc_description_ = "双语导师系统后台服务" >> "%APP_DIR%\scripts\service_installer.py"
echo. >> "%APP_DIR%\scripts\service_installer.py"
echo     def __init__(self, args): >> "%APP_DIR%\scripts\service_installer.py"
echo         win32serviceutil.ServiceFramework.__init__(self, args) >> "%APP_DIR%\scripts\service_installer.py"
echo         self.hWaitStop = win32event.CreateEvent(None, 0, 0, None) >> "%APP_DIR%\scripts\service_installer.py"
echo         self.process = None >> "%APP_DIR%\scripts\service_installer.py"
echo. >> "%APP_DIR%\scripts\service_installer.py"
echo     def SvcStop(self): >> "%APP_DIR%\scripts\service_installer.py"
echo         self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING) >> "%APP_DIR%\scripts\service_installer.py"
echo         if self.process: >> "%APP_DIR%\scripts\service_installer.py"
echo             self.process.terminate() >> "%APP_DIR%\scripts\service_installer.py"
echo         win32event.SetEvent(self.hWaitStop) >> "%APP_DIR%\scripts\service_installer.py"
echo. >> "%APP_DIR%\scripts\service_installer.py"
echo     def SvcDoRun(self): >> "%APP_DIR%\scripts\service_installer.py"
echo         os.chdir(r"%APP_DIR%") >> "%APP_DIR%\scripts\service_installer.py"
echo         self.process = subprocess.Popen([r"%APP_DIR%\scripts\start_service.bat"], shell=True) >> "%APP_DIR%\scripts\service_installer.py"
echo         win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE) >> "%APP_DIR%\scripts\service_installer.py"
echo. >> "%APP_DIR%\scripts\service_installer.py"
echo if __name__ == '__main__': >> "%APP_DIR%\scripts\service_installer.py"
echo     win32serviceutil.HandleCommandLine(BilingualTutorService) >> "%APP_DIR%\scripts\service_installer.py"

REM 安装服务
cd /d "%APP_DIR%\scripts"
call "%VENV_DIR%\Scripts\activate.bat"
python service_installer.py install

call :log_success "Windows服务创建完成"
goto :eof

REM 配置防火墙
:setup_firewall
call :log_info "配置Windows防火墙..."

REM 添加防火墙规则
netsh advfirewall firewall add rule name="双语导师系统-HTTP" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="双语导师系统-HTTPS" dir=in action=allow protocol=TCP localport=443
netsh advfirewall firewall add rule name="双语导师系统-应用" dir=in action=allow protocol=TCP localport=5000

call :log_success "防火墙配置完成"
goto :eof

REM 创建备份脚本
:create_backup_script
call :log_info "创建备份脚本..."

echo @echo off > "%APP_DIR%\scripts\backup.bat"
echo REM 双语导师系统备份脚本 >> "%APP_DIR%\scripts\backup.bat"
echo. >> "%APP_DIR%\scripts\backup.bat"
echo set BACKUP_DIR=%BACKUP_DIR% >> "%APP_DIR%\scripts\backup.bat"
echo set DATA_DIR=%DATA_DIR% >> "%APP_DIR%\scripts\backup.bat"
echo set LOG_DIR=%LOG_DIR% >> "%APP_DIR%\scripts\backup.bat"
echo set DATE=%%date:~0,4%%%%date:~5,2%%%%date:~8,2%%_%%time:~0,2%%%%time:~3,2%%%%time:~6,2%% >> "%APP_DIR%\scripts\backup.bat"
echo set DATE=%%DATE: =0%% >> "%APP_DIR%\scripts\backup.bat"
echo. >> "%APP_DIR%\scripts\backup.bat"
echo REM 创建备份目录 >> "%APP_DIR%\scripts\backup.bat"
echo if not exist "%%BACKUP_DIR%%\database" mkdir "%%BACKUP_DIR%%\database" >> "%APP_DIR%\scripts\backup.bat"
echo if not exist "%%BACKUP_DIR%%\logs" mkdir "%%BACKUP_DIR%%\logs" >> "%APP_DIR%\scripts\backup.bat"
echo if not exist "%%BACKUP_DIR%%\config" mkdir "%%BACKUP_DIR%%\config" >> "%APP_DIR%\scripts\backup.bat"
echo. >> "%APP_DIR%\scripts\backup.bat"
echo REM 备份数据库 >> "%APP_DIR%\scripts\backup.bat"
echo if exist "%%DATA_DIR%%\learning.db" ( >> "%APP_DIR%\scripts\backup.bat"
echo     copy "%%DATA_DIR%%\learning.db" "%%BACKUP_DIR%%\database\learning_%%DATE%%.db" >> "%APP_DIR%\scripts\backup.bat"
echo     echo 数据库备份完成: learning_%%DATE%%.db >> "%APP_DIR%\scripts\backup.bat"
echo ^) >> "%APP_DIR%\scripts\backup.bat"
echo. >> "%APP_DIR%\scripts\backup.bat"
echo REM 备份日志 >> "%APP_DIR%\scripts\backup.bat"
echo xcopy "%%LOG_DIR%%\*.log" "%%BACKUP_DIR%%\logs\" /Y /Q >> "%APP_DIR%\scripts\backup.bat"
echo echo 日志备份完成 >> "%APP_DIR%\scripts\backup.bat"
echo. >> "%APP_DIR%\scripts\backup.bat"
echo REM 清理旧备份（保留30天） >> "%APP_DIR%\scripts\backup.bat"
echo forfiles /p "%%BACKUP_DIR%%" /m *.* /d -30 /c "cmd /c del @path" 2^>nul >> "%APP_DIR%\scripts\backup.bat"
echo echo 旧备份清理完成 >> "%APP_DIR%\scripts\backup.bat"
echo. >> "%APP_DIR%\scripts\backup.bat"
echo echo 备份任务完成: %%DATE%% >> "%APP_DIR%\scripts\backup.bat"

REM 创建定时任务
schtasks /create /tn "双语导师系统备份" /tr "%APP_DIR%\scripts\backup.bat" /sc daily /st 02:00 /f

call :log_success "备份脚本创建完成"
goto :eof

REM 创建监控脚本
:create_monitoring_script
call :log_info "创建监控脚本..."

echo @echo off > "%APP_DIR%\scripts\monitor.bat"
echo REM 双语导师系统监控脚本 >> "%APP_DIR%\scripts\monitor.bat"
echo. >> "%APP_DIR%\scripts\monitor.bat"
echo set SERVICE_NAME=%SERVICE_NAME% >> "%APP_DIR%\scripts\monitor.bat"
echo set LOG_FILE=%LOG_DIR%\monitor.log >> "%APP_DIR%\scripts\monitor.bat"
echo set APP_URL=http://localhost:5000/health >> "%APP_DIR%\scripts\monitor.bat"
echo. >> "%APP_DIR%\scripts\monitor.bat"
echo REM 检查服务状态 >> "%APP_DIR%\scripts\monitor.bat"
echo sc query "%%SERVICE_NAME%%" ^| find "RUNNING" ^>nul >> "%APP_DIR%\scripts\monitor.bat"
echo if %%errorlevel%% neq 0 ( >> "%APP_DIR%\scripts\monitor.bat"
echo     echo %%date%% %%time%% - 服务未运行，尝试启动 ^>^> "%%LOG_FILE%%" >> "%APP_DIR%\scripts\monitor.bat"
echo     net start "%%SERVICE_NAME%%" >> "%APP_DIR%\scripts\monitor.bat"
echo     timeout /t 10 /nobreak ^>nul >> "%APP_DIR%\scripts\monitor.bat"
echo ^) >> "%APP_DIR%\scripts\monitor.bat"
echo. >> "%APP_DIR%\scripts\monitor.bat"
echo REM 检查HTTP响应 >> "%APP_DIR%\scripts\monitor.bat"
echo curl -f -s "%%APP_URL%%" ^>nul >> "%APP_DIR%\scripts\monitor.bat"
echo if %%errorlevel%% neq 0 ( >> "%APP_DIR%\scripts\monitor.bat"
echo     echo %%date%% %%time%% - HTTP健康检查失败，重启服务 ^>^> "%%LOG_FILE%%" >> "%APP_DIR%\scripts\monitor.bat"
echo     net stop "%%SERVICE_NAME%%" >> "%APP_DIR%\scripts\monitor.bat"
echo     timeout /t 5 /nobreak ^>nul >> "%APP_DIR%\scripts\monitor.bat"
echo     net start "%%SERVICE_NAME%%" >> "%APP_DIR%\scripts\monitor.bat"
echo ^) else ( >> "%APP_DIR%\scripts\monitor.bat"
echo     echo %%date%% %%time%% - 系统运行正常 ^>^> "%%LOG_FILE%%" >> "%APP_DIR%\scripts\monitor.bat"
echo ^) >> "%APP_DIR%\scripts\monitor.bat"

REM 创建定时任务（每5分钟检查一次）
schtasks /create /tn "双语导师系统监控" /tr "%APP_DIR%\scripts\monitor.bat" /sc minute /mo 5 /f

call :log_success "监控脚本创建完成"
goto :eof

REM 启动服务
:start_services
call :log_info "启动服务..."

REM 启动Windows服务
net start "%SERVICE_NAME%"

REM 等待服务启动
timeout /t 10 /nobreak >nul

REM 检查服务状态
sc query "%SERVICE_NAME%" | find "RUNNING" >nul
if %errorLevel% equ 0 (
    call :log_success "应用服务启动成功"
) else (
    call :log_error "应用服务启动失败"
    sc query "%SERVICE_NAME%"
    pause
    exit /b 1
)

REM 检查HTTP响应
timeout /t 10 /nobreak >nul
curl -f -s "http://localhost:5000/health" >nul
if %errorLevel% equ 0 (
    call :log_success "HTTP健康检查通过"
) else (
    call :log_warning "HTTP健康检查失败，请检查应用状态"
)
goto :eof

REM 显示部署信息
:show_deployment_info
call :log_success "部署完成！"
echo.
echo ==========================================
echo 双语导师系统部署信息
echo ==========================================
echo 应用目录: %APP_DIR%
echo 数据目录: %DATA_DIR%
echo 日志目录: %LOG_DIR%
echo 配置目录: %CONFIG_DIR%
echo 服务名称: %SERVICE_NAME%
echo ==========================================
echo 常用命令:
echo 启动服务: net start "%SERVICE_NAME%"
echo 停止服务: net stop "%SERVICE_NAME%"
echo 查看服务: sc query "%SERVICE_NAME%"
echo 服务管理: services.msc
echo ==========================================
echo 访问地址: http://localhost:5000
echo 健康检查: http://localhost:5000/health
echo ==========================================
goto :eof

REM 主函数
:main
call :log_info "开始部署双语导师系统..."

call :check_admin
call :check_system_requirements
call :create_directories
call :install_python_dependencies
call :setup_database
call :create_windows_service
call :setup_firewall
call :create_backup_script
call :create_monitoring_script
call :start_services
call :show_deployment_info

call :log_success "双语导师系统部署完成！"
echo.
echo 按任意键退出...
pause >nul
goto :eof

REM 脚本入口
call :main %*