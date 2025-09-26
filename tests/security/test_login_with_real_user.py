#!/usr/bin/env python3
"""
Script para probar el login con usuarios reales de la base de datos
"""
import requests
import json

BASE_URL = "http://localhost:8000"
ORIGIN = "http://localhost:5173"

def test_login_with_user(username, password):
    """Prueba el login con un usuario específico"""
    print(f"\n🔐 Probando login con usuario: {username}")
    
    url = f"{BASE_URL}/api/auth/login/"
    headers = {
        "Content-Type": "application/json",
        "Origin": ORIGIN,
        "Referer": ORIGIN
    }
    
    data = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Login exitoso!")
            print(f"   Access Token: {result.get('access_token', 'N/A')[:50]}...")
            print(f"   Refresh Token: {result.get('refresh_token', 'N/A')[:50]}...")
            return result
        else:
            print(f"   ❌ Login falló: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error text: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return None

def main():
    print("=" * 60)
    print("PRUEBAS DE LOGIN CON USUARIOS REALES")
    print("=" * 60)
    
    # Lista de usuarios conocidos para probar
    test_users = [
        ("admin", "admin"),
        ("admin", "admin123"),
        ("german", "german"),
        ("german", "password"),
        ("test_user", "test"),
        ("test_user", "password"),
        ("vendedor", "vendedor"),
        ("vendedor", "password"),
    ]
    
    successful_logins = []
    
    for username, password in test_users:
        result = test_login_with_user(username, password)
        if result:
            successful_logins.append((username, password, result))
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    if successful_logins:
        print(f"✅ {len(successful_logins)} login(s) exitoso(s):")
        for username, password, result in successful_logins:
            print(f"   - {username} con password '{password}'")
    else:
        print("❌ No se pudo hacer login con ningún usuario")
        print("\nPosibles causas:")
        print("1. Las contraseñas no son las esperadas")
        print("2. Hay algún problema con la autenticación")
        print("3. Los usuarios están inactivos")

if __name__ == "__main__":
    main()