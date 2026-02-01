# 安装 Windows 服务脚本（纯文本 Embedding + Reranker）
param(
    [string]$ServiceName = "FastAPI TextRAG Service",	# 此为预设值，建议通过启动参数 -ServiceName "My Service" 自定义
    [string]$ModelName = "Embedding-Reranker",	# 仅日志标记，无实际作用
    [int]$Port = 8080		# 此为预设值，建议通过启动参数 -Port 8080 自定义
)

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonExe = "$ProjectDir\fastapi_env\Scripts\python.exe"
$StartupScript = "$ProjectDir\main.py"
$SetupScript = "$ProjectDir\setup.py"
$LogDir = "$ProjectDir\logs"
$EnvFile = "$ProjectDir\.env"
$nssm = "$ProjectDir\nssm\nssm.exe"

# ========================
# 检查 .env 是否存在
# ========================
Write-Host " 检查 .env 文件..." -ForegroundColor Cyan
if (!(Test-Path $EnvFile)) {
    Write-Host " 错误: .env 文件不存在！" -ForegroundColor Red
    Write-Host " 请先运行初始化脚本：" -ForegroundColor Yellow
    Write-Host " python `"$SetupScript`"" -ForegroundColor Green
    exit 1
}

$envContent = Get-Content $EnvFile -Raw
$requiredKeys = @("DEPLOY_EMBEDDING", "DEPLOY_RERANKER", "EMBEDDING_DEVICE", "RERANKER_DEVICE")
$missingKeys = @()
foreach ($key in $requiredKeys) {
    if ($envContent -notmatch "(?m)^\s*$key\s*=") {
        $missingKeys += $key
    }
}
if ($missingKeys.Count -gt 0) {
    Write-Host " 错误: .env 缺少必要字段: $($missingKeys -join ', ')" -ForegroundColor Red
    Write-Host " 请先运行初始化脚本：" -ForegroundColor Yellow
    Write-Host " python `"$SetupScript`"" -ForegroundColor Green
    exit 1
}

# ========================
# 端口占用检查（保持不变）
# ========================
function Test-PortInUse { param([int]$Port) 
    $listening = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    return $null -ne $listening
}
function Get-PortProcessInfo { param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($conn) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            return [PSCustomObject]@{ PID = $proc.Id; Name = $proc.ProcessName; Path = $proc.Path }
        }
    }
    return $null
}
Write-Host " 检查端口 $Port 是否被占用..."

# ========================
# 创建日志目录
# ========================
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# ========================
# 更新 .env 中的 PORT
# ========================
$envContent = Get-Content -Path $EnvFile -Raw -Encoding UTF8
if ($envContent -match "(?m)^\s*PORT\s*=") {
    $envContent = $envContent -replace "(?m)^\s*PORT\s*=.*", "PORT=$Port"
} else {
    if (-not $envContent.EndsWith("`n")) { $envContent += "`n" }
    $envContent += "PORT=$Port"
}
Set-Content -Path $EnvFile -Value $envContent -Encoding UTF8

# ========================
# 使用 NSSM 安装服务
# ========================
$AppDirectory = $ProjectDir
$AppEnvironmentExtra = "PYTHONUNBUFFERED=1`nPORT=$Port"

# 如果服务已存在，先移除
$null = & $nssm status $ServiceName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host " 停止并移除现有服务 '$ServiceName'..."
    & $nssm stop $ServiceName 2>$null
    & $nssm remove $ServiceName confirm 2>$null
}

& $nssm install $ServiceName $PythonExe $StartupScript
& $nssm set $ServiceName AppDirectory $AppDirectory
& $nssm set $ServiceName AppEnvironmentExtra $AppEnvironmentExtra
& $nssm set $ServiceName AppStdout "$LogDir\stdout.log"
& $nssm set $ServiceName AppStderr "$LogDir\stderr.log"
& $nssm set $ServiceName Start SERVICE_AUTO_START

# ========================
# 添加防火墙规则
# ========================
$firewallRule = "$ServiceName-$Port"
if (-not (Get-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $firewallRule -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow | Out-Null
    Write-Host " 已添加防火墙规则，开放端口 $Port"
}

# ========================
# 完成提示
# ========================
Write-Host ""
Write-Host " 服务 '$ServiceName' 安装成功！" -ForegroundColor Green
Write-Host " 服务名称: $ServiceName"
Write-Host " 监听端口: $Port"
Write-Host " 项目路径: $ProjectDir"
Write-Host " 日志文件: $LogDir\stdout.log / stderr.log"
Write-Host ""
Write-Host " 启动服务: net start $ServiceName"
Write-Host " 停止服务: net stop $ServiceName"
Write-Host " 卸载服务: .\uninstall_service.ps1 -ServiceName $ServiceName"
Write-Host ""
Write-Host " 注意：如遇启动失败，请检查 .env 配置及模型路径是否正确。" -ForegroundColor Yellow