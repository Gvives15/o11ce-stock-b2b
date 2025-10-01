# Script para ejecutar el entorno de desarrollo
# Uso: .\dev.ps1 [up|down|build|logs|restart]

param(
    [Parameter(Position=0)]
    [ValidateSet("up", "down", "build", "logs", "restart", "status")]
    [string]$Action = "up"
)

# Obtener el directorio del script y navegar al directorio docker
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DockerDir = Split-Path -Parent $ScriptDir
Set-Location $DockerDir

$ComposeFiles = "-f docker-compose.yml -f docker-compose.dev.yml"

switch ($Action) {
    "up" {
        Write-Host "Iniciando entorno de desarrollo..." -ForegroundColor Green
        docker-compose $ComposeFiles.Split(' ') up -d
    }
    "down" {
        Write-Host "Deteniendo entorno de desarrollo..." -ForegroundColor Yellow
        docker-compose $ComposeFiles.Split(' ') down
    }
    "build" {
        Write-Host "Construyendo imagenes de desarrollo..." -ForegroundColor Blue
        docker-compose $ComposeFiles.Split(' ') up --build -d
    }
    "logs" {
        Write-Host "Mostrando logs del entorno de desarrollo..." -ForegroundColor Cyan
        docker-compose $ComposeFiles.Split(' ') logs -f
    }
    "restart" {
        Write-Host "Reiniciando entorno de desarrollo..." -ForegroundColor Magenta
        docker-compose $ComposeFiles.Split(' ') restart
    }
    "status" {
        Write-Host "Estado del entorno de desarrollo:" -ForegroundColor White
        docker-compose $ComposeFiles.Split(' ') ps
    }
}

if ($Action -eq "up" -or $Action -eq "build") {
    Write-Host ""
    Write-Host "Entorno de desarrollo disponible en:" -ForegroundColor Green
    Write-Host "   Aplicacion POS: http://localhost/pos/" -ForegroundColor White
    Write-Host "   API Django: http://localhost/api/" -ForegroundColor White
    Write-Host "   MailHog: http://localhost:8025/" -ForegroundColor White
    Write-Host "   Frontend directo: http://localhost:5173/" -ForegroundColor White
}