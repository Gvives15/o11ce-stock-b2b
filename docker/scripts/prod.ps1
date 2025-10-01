# Script para ejecutar el entorno de producción
# Uso: .\prod.ps1 [up|down|build|logs|restart]

param(
    [Parameter(Position=0)]
    [ValidateSet("up", "down", "build", "logs", "restart", "status")]
    [string]$Action = "up"
)

# Obtener el directorio del script y navegar al directorio docker
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DockerDir = Split-Path -Parent $ScriptDir
Set-Location $DockerDir

$ComposeFiles = "-f docker-compose.yml -f docker-compose.prod.yml"

switch ($Action) {
    "up" {
        Write-Host "Iniciando entorno de produccion..." -ForegroundColor Green
        docker-compose $ComposeFiles.Split(' ') up -d
    }
    "down" {
        Write-Host "Deteniendo entorno de produccion..." -ForegroundColor Yellow
        docker-compose $ComposeFiles.Split(' ') down
    }
    "build" {
        Write-Host "Construyendo imagenes de produccion..." -ForegroundColor Blue
        docker-compose $ComposeFiles.Split(' ') up --build -d
    }
    "logs" {
        Write-Host "Mostrando logs del entorno de produccion..." -ForegroundColor Cyan
        docker-compose $ComposeFiles.Split(' ') logs -f
    }
    "restart" {
        Write-Host "Reiniciando entorno de produccion..." -ForegroundColor Magenta
        docker-compose $ComposeFiles.Split(' ') restart
    }
    "status" {
        Write-Host "Estado del entorno de produccion:" -ForegroundColor White
        docker-compose $ComposeFiles.Split(' ') ps
    }
}

if ($Action -eq "up" -or $Action -eq "build") {
    Write-Host ""
    Write-Host "Entorno de produccion iniciado" -ForegroundColor Green
    Write-Host "   Asegurate de configurar SSL y dominio correctamente" -ForegroundColor Yellow
}