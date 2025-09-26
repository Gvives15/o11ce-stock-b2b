#!/usr/bin/env python3
"""
Script para probar los endpoints de autenticación y CORS.
"""

import requests
import json

# Configuración
BASE_URL = "http://localhost:8000"
AUTH_ENDPOINTS = {
    "login": f"{BASE_URL}/api/auth/login/",
    "refresh": f"{BASE_URL}/api/auth/refresh/", 
    "me": f"{BASE_URL}/api/auth/me/",
    "logout": f"{BASE_URL}/api/auth/logout/"
}

def test_cors_preflight(url, method="POST"):
    """Prueba CORS preflight para un endpoint."""
    print(f"\n🔍 Probando CORS preflight para {url}")
    
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": "Content-Type,Authorization"
    }
    
    try:
        response = requests.options(url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Headers CORS:")
        
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
            "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials")
        }
        
        for header, value in cors_headers.items():
            if value:
                print(f"     {header}: {value}")
            else:
                print(f"     {header}: ❌ No presente")
                
        return response.status_code, cors_headers
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return None, {}

def test_login_endpoint():
    """Prueba el endpoint de login."""
    print(f"\n🔐 Probando endpoint de login: {AUTH_ENDPOINTS['login']}")
    
    # Primero probar CORS
    test_cors_preflight(AUTH_ENDPOINTS['login'], "POST")
    
    # Probar login con credenciales de prueba
    login_data = {
        "username": "admin",  # Usuario por defecto de Django
        "password": "admin123"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://localhost:5173"
    }
    
    try:
        response = requests.post(
            AUTH_ENDPOINTS['login'], 
            json=login_data, 
            headers=headers,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            return data.get('access'), data.get('refresh')
        else:
            print(f"   ❌ Login falló: {response.status_code}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return None, None

def test_me_endpoint(access_token):
    """Prueba el endpoint /me con token de autorización."""
    print(f"\n👤 Probando endpoint /me: {AUTH_ENDPOINTS['me']}")
    
    if not access_token:
        print("   ❌ No hay token de acceso disponible")
        return
    
    # Primero probar CORS
    test_cors_preflight(AUTH_ENDPOINTS['me'], "GET")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Origin": "http://localhost:5173"
    }
    
    try:
        response = requests.get(
            AUTH_ENDPOINTS['me'], 
            headers=headers,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("   ✅ Endpoint /me funciona correctamente")
        else:
            print(f"   ❌ Endpoint /me falló: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")

def main():
    """Función principal para ejecutar todas las pruebas."""
    print("🚀 Iniciando pruebas de endpoints de autenticación y CORS")
    print(f"   Base URL: {BASE_URL}")
    
    # Probar todos los endpoints CORS
    print("\n" + "="*60)
    print("PRUEBAS CORS PREFLIGHT")
    print("="*60)
    
    for name, url in AUTH_ENDPOINTS.items():
        method = "GET" if name == "me" else "POST"
        test_cors_preflight(url, method)
    
    # Probar funcionalidad de autenticación
    print("\n" + "="*60)
    print("PRUEBAS DE FUNCIONALIDAD")
    print("="*60)
    
    # Probar login
    access_token, refresh_token = test_login_endpoint()
    
    # Probar /me si tenemos token
    if access_token:
        test_me_endpoint(access_token)
    
    print("\n✅ Pruebas completadas")

if __name__ == "__main__":
    main()