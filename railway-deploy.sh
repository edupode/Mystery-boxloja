#!/bin/bash
# Railway Deployment Script

echo "🚀 Iniciando deployment no Railway..."

# Instalar dependências do backend
echo "📦 Instalando dependências Python..."
cd backend
pip install -r requirements.txt

echo "✅ Deployment concluído!"