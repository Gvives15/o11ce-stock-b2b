#!/bin/bash

# Script de inicialización de datos para el contenedor Docker
# Este script se ejecuta después de que Django esté listo

echo "🚀 Iniciando configuración de datos iniciales..."

# Esperar a que la base de datos esté lista
echo "⏳ Esperando a que la base de datos esté lista..."
python manage.py wait_for_db || {
    echo "❌ Error: No se pudo conectar a la base de datos"
    exit 1
}

# Ejecutar migraciones
echo "📦 Aplicando migraciones..."
python manage.py migrate || {
    echo "❌ Error: Falló la aplicación de migraciones"
    exit 1
}

# Crear roles básicos
echo "👔 Creando roles básicos..."
python manage.py seed_roles || {
    echo "❌ Error: Falló la creación de roles"
    exit 1
}

# Aplicar scopes a roles existentes
echo "🔐 Aplicando scopes a roles..."
python manage.py apply_role_scopes || {
    echo "⚠️  Advertencia: No se pudieron aplicar todos los scopes (comando puede no existir)"
}

# Crear usuario de prueba
echo "👤 Creando usuario de prueba..."
python manage.py create_test_user || {
    echo "❌ Error: Falló la creación del usuario de prueba"
    exit 1
}

# Recopilar archivos estáticos
echo "📁 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput || {
    echo "⚠️  Advertencia: Falló la recopilación de archivos estáticos"
}

echo "✅ Configuración de datos iniciales completada exitosamente!"
echo ""
echo "🎉 Sistema listo para usar:"
echo "   👤 Usuario: alejandro.vives"
echo "   🔑 Contraseña: ale12345"
echo "   👔 Rol: Encargado"
echo ""