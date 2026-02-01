# 接受需要卸载的服务传入的参数ServiceName，如果没有传入将按这里的预设值
param([string]$ServiceName = "FastAPI TextRAG Service")

# 自动获取脚本所在目录作为项目根目录
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

& "$ProjectDir\nssm\nssm.exe" stop $ServiceName
& "$ProjectDir\nssm\nssm.exe" remove $ServiceName confirm

Write-Host " 服务 '$ServiceName' 已卸载。"