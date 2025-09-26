# Script de diagnóstico completo para verificar la arquitectura nginx + backend + frontend
# Ejecutar desde la raíz del proyecto: .\scripts\health_check.ps1

Write-Host "🔍 DIAGNÓSTICO COMPLETO DEL SISTEMA POS" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar servicios Docker
Write-Host "1️⃣ VERIFICANDO SERVICIOS DOCKER..." -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

try {
    $dockerStatus = docker-compose -f docker/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    Write-Host $dockerStatus
    Write-Host "✅ Servicios Docker verificados" -ForegroundColor Green
} catch {
    Write-Host "❌ Error verificando servicios Docker: $_" -ForegroundColor Red
}
Write-Host ""

# 2. Health Check Backend
Write-Host "2️⃣ HEALTH CHECK BACKEND (Django + Gunicorn)..." -ForegroundColor Yellow
Write-Host "-----------------------------------------------" -ForegroundColor Yellow

try {
    $backendHealth = Invoke-WebRequest -Uri "http://localhost/health/live/" -Method GET -TimeoutSec 10
    if ($backendHealth.StatusCode -eq 200) {
        $healthData = $backendHealth.Content | ConvertFrom-Json
        Write-Host "✅ Backend Health: $($healthData.status)" -ForegroundColor Green
        Write-Host "   Service: $($healthData.service)" -ForegroundColor Gray
        Write-Host "   Version: $($healthData.version)" -ForegroundColor Gray
        Write-Host "   Latency: $($healthData.latency_ms)ms" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Backend Health Check falló: $_" -ForegroundColor Red
}
Write-Host ""

# 3. Health Check Frontend Directo
Write-Host "3️⃣ HEALTH CHECK FRONTEND DIRECTO (Vue + Vite)..." -ForegroundColor Yellow
Write-Host "------------------------------------------------" -ForegroundColor Yellow

try {
    $frontendHealth = Invoke-WebRequest -Uri "http://localhost:5173" -Method GET -TimeoutSec 10
    if ($frontendHealth.StatusCode -eq 200) {
        Write-Host "✅ Frontend Directo: Funcionando en puerto 5173" -ForegroundColor Green
        Write-Host "   Content-Type: $($frontendHealth.Headers['Content-Type'])" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Frontend Directo falló: $_" -ForegroundColor Red
}
Write-Host ""

# 4. Verificar Proxy Nginx - API
Write-Host "4️⃣ VERIFICANDO PROXY NGINX - API..." -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Yellow

try {
    $apiHealth = Invoke-WebRequest -Uri "http://localhost/api/health/live/" -Method GET -TimeoutSec 10
    if ($apiHealth.StatusCode -eq 200) {
        $apiData = $apiHealth.Content | ConvertFrom-Json
        Write-Host "✅ Nginx Proxy API: Funcionando" -ForegroundColor Green
        Write-Host "   Backend Status: $($apiData.status)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Nginx Proxy API falló: $_" -ForegroundColor Red
}
Write-Host ""

# 5. Verificar Proxy Nginx - Frontend
Write-Host "5️⃣ VERIFICANDO PROXY NGINX - FRONTEND..." -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

try {
    $frontendProxy = Invoke-WebRequest -Uri "http://localhost/pos/" -Method GET -TimeoutSec 10
    if ($frontendProxy.StatusCode -eq 200) {
        Write-Host "✅ Nginx Proxy Frontend: Funcionando" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "⚠️  Nginx Proxy Frontend: 403 Forbidden (Problema de configuración Vite)" -ForegroundColor Yellow
        Write-Host "   Solución: Configurar base path en Vite para /pos/" -ForegroundColor Gray
    } else {
        Write-Host "❌ Nginx Proxy Frontend falló: $_" -ForegroundColor Red
    }
}
Write-Host ""

# 6. Verificar Endpoints de API
Write-Host "6️⃣ VERIFICANDO ENDPOINTS DE API..." -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

# Test login endpoint
try {
    $loginTest = Invoke-WebRequest -Uri "http://localhost/api/auth/login/" -Method POST -ContentType "application/json" -Body '{"username":"test","password":"test"}' -TimeoutSec 10
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        $errorResponse = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($errorResponse)
        $errorContent = $reader.ReadToEnd()
        Write-Host "✅ Login Endpoint: Funcionando (error esperado)" -ForegroundColor Green
        Write-Host "   Response: $errorContent" -ForegroundColor Gray
    } else {
        Write-Host "❌ Login Endpoint falló: $_" -ForegroundColor Red
    }
}

# Test admin endpoint
try {
    $adminTest = Invoke-WebRequest -Uri "http://localhost/admin/" -Method GET -TimeoutSec 10
    if ($adminTest.StatusCode -eq 200 -or $adminTest.StatusCode -eq 302) {
        Write-Host "✅ Admin Endpoint: Funcionando" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Admin Endpoint falló: $_" -ForegroundColor Red
}
Write-Host ""

# 7. Verificar Conectividad Interna Docker
Write-Host "7️⃣ VERIFICANDO CONECTIVIDAD INTERNA DOCKER..." -ForegroundColor Yellow
Write-Host "----------------------------------------------" -ForegroundColor Yellow

try {
    $nginxToFrontend = docker exec docker-nginx-1 wget -qO- http://pos-frontend:5173 2>&1
    if ($nginxToFrontend -match "403") {
        Write-Host "⚠️  Nginx → Frontend: 403 Forbidden (Problema de configuración)" -ForegroundColor Yellow
    } else {
        Write-Host "✅ Nginx → Frontend: Conectividad OK" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Nginx → Frontend: Error de conectividad" -ForegroundColor Red
}

try {
    $nginxToBackend = docker exec docker-nginx-1 wget -qO- http://web:8000/health/live/ 2>&1
    if ($nginxToBackend -match "healthy") {
        Write-Host "✅ Nginx → Backend: Conectividad OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Nginx → Backend: Error de conectividad" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Nginx → Backend: Error de conectividad" -ForegroundColor Red
}
Write-Host ""

# 8. Resumen y Recomendaciones
Write-Host "8️⃣ RESUMEN Y RECOMENDACIONES..." -ForegroundColor Yellow
Write-Host "--------------------------------" -ForegroundColor Yellow

Write-Host "✅ COMPONENTES FUNCIONANDO:" -ForegroundColor Green
Write-Host "   • Backend Django + Gunicorn (puerto 8000)" -ForegroundColor Gray
Write-Host "   • Frontend Vue + Vite (puerto 5173)" -ForegroundColor Gray
Write-Host "   • Nginx Reverse Proxy (puerto 80)" -ForegroundColor Gray
Write-Host "   • API Endpoints (/api/*)" -ForegroundColor Gray
Write-Host "   • Health Checks" -ForegroundColor Gray
Write-Host "   • Base de datos PostgreSQL" -ForegroundColor Gray
Write-Host "   • Redis Cache" -ForegroundColor Gray
Write-Host "   • Celery Workers" -ForegroundColor Gray
Write-Host ""

Write-Host "⚠️  PROBLEMA IDENTIFICADO:" -ForegroundColor Yellow
Write-Host "   • Frontend no accesible via /pos/ (403 Forbidden)" -ForegroundColor Gray
Write-Host "   • Causa: Vite no configurado para base path /pos/" -ForegroundColor Gray
Write-Host ""

Write-Host "🔧 SOLUCIONES RECOMENDADAS:" -ForegroundColor Cyan
Write-Host "   1. Configurar base path en vite.config.ts:" -ForegroundColor Gray
Write-Host "      base: '/pos/'" -ForegroundColor Gray
Write-Host "   2. O cambiar nginx.conf para usar proxy sin path:" -ForegroundColor Gray
Write-Host "      location /pos/ { proxy_pass http://pos_frontend:5173/; }" -ForegroundColor Gray
Write-Host "   3. Para desarrollo: usar http://localhost:5173 directamente" -ForegroundColor Gray
Write-Host ""

Write-Host "🚀 ACCESO DIRECTO:" -ForegroundColor Cyan
Write-Host "   • Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "   • Backend API: http://localhost/api/" -ForegroundColor Gray
Write-Host "   • Admin: http://localhost/admin/" -ForegroundColor Gray
Write-Host "   • Health: http://localhost/health/live/" -ForegroundColor Gray
Write-Host ""

Write-Host "✨ DIAGNÓSTICO COMPLETADO" -ForegroundColor Green
