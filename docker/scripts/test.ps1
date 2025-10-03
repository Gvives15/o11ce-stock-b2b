# Script para ejecutar tests usando Docker Compose
# Uso: .\docker\scripts\test.ps1 [test_path] [options]

param(
    [string]$TestPath = "",
    [string]$Options = "",
    [switch]$Coverage = $false,
    [switch]$Verbose = $false,
    [switch]$Setup = $false,
    [switch]$Teardown = $false,
    [switch]$Help = $false
)

# Función para mostrar ayuda
function Show-Help {
    Write-Host "Script para ejecutar tests con Docker Compose" -ForegroundColor Green
    Write-Host ""
    Write-Host "Uso:" -ForegroundColor Yellow
    Write-Host "  .\docker\scripts\test.ps1 [opciones]"
    Write-Host ""
    Write-Host "Opciones:" -ForegroundColor Yellow
    Write-Host "  -TestPath <path>    Ruta específica de tests a ejecutar"
    Write-Host "  -Options <opts>     Opciones adicionales para pytest"
    Write-Host "  -Coverage           Generar reporte de cobertura"
    Write-Host "  -Verbose            Salida verbose"
    Write-Host "  -Setup              Solo levantar servicios de test"
    Write-Host "  -Teardown           Solo bajar servicios de test"
    Write-Host "  -Help               Mostrar esta ayuda"
    Write-Host ""
    Write-Host "Ejemplos:" -ForegroundColor Yellow
    Write-Host "  .\docker\scripts\test.ps1"
    Write-Host "  .\docker\scripts\test.ps1 -TestPath tests/integration/test_stock_event_bus.py"
    Write-Host "  .\docker\scripts\test.ps1 -Coverage -Verbose"
    Write-Host "  .\docker\scripts\test.ps1 -Setup"
}

if ($Help) {
    Show-Help
    exit 0
}

# Configuración
$ComposeFile = "docker\docker-compose.test.yml"
$ProjectName = "bff-test"

# Verificar que el archivo docker-compose.test.yml existe
if (-not (Test-Path $ComposeFile)) {
    Write-Host "Error: No se encontró $ComposeFile" -ForegroundColor Red
    exit 1
}

# Función para ejecutar comandos Docker Compose
function Invoke-DockerCompose {
    param([string]$Command)
    
    $FullCommand = "docker-compose -f $ComposeFile -p $ProjectName $Command"
    Write-Host "Ejecutando: $FullCommand" -ForegroundColor Cyan
    Invoke-Expression $FullCommand
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error ejecutando comando Docker Compose" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Solo setup
if ($Setup) {
    Write-Host "Levantando servicios de test..." -ForegroundColor Green
    Invoke-DockerCompose "up -d test-db test-redis"
    Write-Host "Servicios de test listos!" -ForegroundColor Green
    exit 0
}

# Solo teardown
if ($Teardown) {
    Write-Host "Bajando servicios de test..." -ForegroundColor Green
    Invoke-DockerCompose "down -v"
    Write-Host "Servicios de test detenidos!" -ForegroundColor Green
    exit 0
}

try {
    Write-Host "=== Iniciando Tests con Docker ===" -ForegroundColor Green
    
    # Levantar servicios de test
    Write-Host "Levantando servicios de test..." -ForegroundColor Yellow
    Invoke-DockerCompose "up -d test-db test-redis"
    
    # Esperar a que los servicios estén listos
    Write-Host "Esperando a que los servicios estén listos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Construir comando de test
    $TestCommand = "python -m pytest"
    
    if ($TestPath) {
        $TestCommand += " $TestPath"
    }
    
    if ($Verbose) {
        $TestCommand += " -v"
    }
    
    if ($Coverage) {
        $TestCommand += " --cov=apps --cov-report=html --cov-report=term"
    }
    
    if ($Options) {
        $TestCommand += " $Options"
    }
    
    # Ejecutar tests
    Write-Host "Ejecutando tests..." -ForegroundColor Yellow
    Write-Host "Comando: $TestCommand" -ForegroundColor Cyan
    
    $DockerCommand = "run --rm test-runner $TestCommand"
    Invoke-DockerCompose $DockerCommand
    
    Write-Host "=== Tests completados ===" -ForegroundColor Green
    
} catch {
    Write-Host "Error durante la ejecución de tests: $_" -ForegroundColor Red
    exit 1
} finally {
    # Limpiar servicios
    Write-Host "Limpiando servicios de test..." -ForegroundColor Yellow
    Invoke-DockerCompose "down -v"
    Write-Host "Limpieza completada!" -ForegroundColor Green
}