# 🚀 Guia de Migração: Render.com → Railway

## 📋 Preparação (FEITO ✅)

Os seguintes arquivos foram criados para facilitar a migração:

- ✅ `railway.toml` - Configuração do Railway
- ✅ `Procfile` - Comando de start da aplicação  
- ✅ `railway-deploy.sh` - Script de deployment
- ✅ Health check endpoint: `/api/health`

## 🎯 Passo-a-Passo da Migração

### 1. Criar Conta no Railway
1. Acesse https://railway.app
2. Faça login com GitHub (recomendado)
3. Conecte seu repositório do projeto

### 2. Configurar Projeto no Railway

```bash
# Instalar Railway CLI (opcional)
npm install -g @railway/cli

# Login no Railway
railway login

# Linkar projeto existente
railway link
```

### 3. Configurar Variáveis de Ambiente

No painel do Railway, adicione estas variáveis:

```env
# Database
MONGO_URL=sua_string_de_conexao_mongodb

# JWT & Security  
SECRET_KEY=sua_chave_secreta_jwt
ADMIN_EMAIL=eduardocorreia3344@gmail.com

# Stripe
STRIPE_SECRET_KEY=sua_chave_stripe
STRIPE_WEBHOOK_SECRET=seu_webhook_secret

# Google OAuth
GOOGLE_CLIENT_ID=seu_google_client_id

# Email (Resend)
RESEND_API_KEY=sua_chave_resend

# Port (Railway define automaticamente)
PORT=8001
```

### 4. Deploy no Railway

#### Opção A: Deploy via Dashboard
1. Conecte seu repositório GitHub
2. Railway fará deploy automático
3. Configure o domínio personalizado (opcional)

#### Opção B: Deploy via CLI
```bash
# Deploy direto
railway up

# Ou deploy com build específico
railway up --service backend
```

### 5. Atualizar Frontend

Após o deploy do Railway, você receberá uma URL como:
`https://seu-projeto.railway.app`

Atualize o arquivo `/app/frontend/.env`:

```env
WDS_SOCKET_PORT=443
REACT_APP_BACKEND_URL=https://seu-projeto.railway.app
REACT_APP_GOOGLE_CLIENT_ID=seu_google_client_id
```

### 6. Teste de Funcionamento

O health check estará disponível em:
`https://seu-projeto.railway.app/api/health`

Deve retornar:
```json
{
  "status": "healthy",
  "timestamp": "2024-XX-XX...",
  "service": "Mystery Box Store API", 
  "version": "2.0.0",
  "database": "connected"
}
```

## 🎁 Vantagens do Railway

- ✅ **24/7 Uptime** - Sem cold starts
- ✅ **500 horas grátis/mês** - Mais que suficiente
- ✅ **Deploy automático** do GitHub
- ✅ **Logs em tempo real**
- ✅ **Rollback fácil** para versões anteriores
- ✅ **SSL grátis** e automático
- ✅ **Environment variables** seguras

## 📞 Próximos Passos

1. **Faça backup** das variáveis de ambiente do Render
2. **Configure Railway** seguindo este guia
3. **Teste todas as funcionalidades**
4. **Atualize DNS** se usar domínio personalizado
5. **Desative Render** apenas após confirmar que tudo funciona

## 🆘 Troubleshooting

**Erro de Build:**
- Verifique se `requirements.txt` está atualizado
- Confirme variáveis de ambiente

**Erro de Database:**
- Confirme string de conexão MongoDB
- Teste conexão local primeiro

**Erro 503:**
- Verifique logs do Railway
- Confirme se health check está respondendo

---

**Status: ✅ PRONTO PARA MIGRAÇÃO**

Todos os arquivos de configuração foram preparados. 
Basta seguir o guia acima para migrar com sucesso!