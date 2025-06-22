# INSTRUÇÕES DE DEPLOY - MYSTERY BOX STORE

## 📋 PRÉ-REQUISITOS

### Contas Necessárias
- [Vercel](https://vercel.com) - Para frontend
- [Render.com](https://render.com) - Para backend
- [MongoDB Atlas](https://cloud.mongodb.com) - Para database em produção

### APIs e Serviços
- Google OAuth configurado para domínios de produção
- Stripe configurado para pagamentos
- Resend configurado para emails

---

## 🚀 DEPLOY DO BACKEND (Render.com)

### 1. Preparação
1. Faça login no [Render.com](https://render.com)
2. Conecte seu repositório GitHub
3. Crie um novo "Web Service"

### 2. Configuração do Serviço
- **Name:** `mystery-box-store-backend`
- **Environment:** `Python`
- **Region:** Europe (London) ou sua preferência
- **Branch:** `main` ou sua branch principal
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`

### 3. Variáveis de Ambiente (Environment Variables)

#### Obrigatórias
```
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/
DB_NAME=mystery_box_store
JWT_SECRET=your-super-secret-jwt-key-change-in-production
ADMIN_EMAIL=your-admin@email.com
```

#### APIs Externas
```
RESEND_API_KEY=re_your_resend_api_key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_SECRET_KEY=sk_test_your_secret_key
```

#### Opcionais (com valores padrão)
```
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
FRONTEND_URL=https://your-frontend-url.vercel.app
```

### 4. Deploy
- Clique em "Create Web Service"
- Aguarde o build e deploy automático
- Anote a URL gerada (ex: `https://mystery-box-backend.onrender.com`)

---

## 🌐 DEPLOY DO FRONTEND (Vercel)

### 1. Preparação
1. Faça login no [Vercel](https://vercel.com)
2. Conecte seu repositório GitHub
3. Clique em "New Project"

### 2. Configuração do Projeto
- **Framework Preset:** Create React App
- **Root Directory:** `frontend`
- **Build Command:** `npm run build` ou `yarn build`
- **Output Directory:** `build`

### 3. Variáveis de Ambiente

#### No painel da Vercel, adicione:
```
REACT_APP_BACKEND_URL=https://mystery-box-backend.onrender.com
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id
```

### 4. Deploy
- Clique em "Deploy"
- Aguarde o build e deploy automático
- Anote a URL gerada (ex: `https://mystery-box-store.vercel.app`)

---

## 🔧 CONFIGURAÇÕES PÓS-DEPLOY

### 1. Atualizar CORS no Backend
No painel do Render.com, adicione a variável de ambiente:
```
FRONTEND_URL=https://mystery-box-store.vercel.app
```

### 2. Google OAuth Configuration
No [Google Cloud Console](https://console.cloud.google.com):
1. Vá para "APIs & Services" > "Credentials"
2. Edite seu OAuth 2.0 Client ID
3. Adicione em "Authorized JavaScript origins":
   - `https://mystery-box-store.vercel.app`
4. Adicione em "Authorized redirect URIs":
   - `https://mystery-box-store.vercel.app`

### 3. Stripe Configuration
- Se usando Stripe, mude para chaves de produção quando apropriado
- Configure webhooks se necessário

### 4. Resend Domain Verification
- No painel do Resend, adicione e verifique o domínio
- Configure DNS records conforme instruído

---

## ✅ VERIFICAÇÃO DE FUNCIONAMENTO

### Testes Essenciais
1. **Acesso ao site:** Verifique se o frontend carrega corretamente
2. **API Connection:** Teste se frontend conecta com backend
3. **Authentication:** Teste login com Google OAuth
4. **Database:** Verifique se dados são salvos/carregados
5. **Emails:** Teste envio de emails
6. **Pagamentos:** Teste checkout com Stripe (modo teste)

### URLs de Teste
- Frontend: `https://mystery-box-store.vercel.app`
- Backend API: `https://mystery-box-backend.onrender.com/api`
- Admin: `https://mystery-box-store.vercel.app/admin`

---

## 🐛 TROUBLESHOOTING

### Problemas Comuns

#### Frontend não conecta com Backend
- Verifique `REACT_APP_BACKEND_URL` no Vercel
- Verifique configuração CORS no backend
- Verifique se backend está online

#### Erro de Authentication
- Verifique configuração Google OAuth
- Verifique `JWT_SECRET` no backend
- Verifique URLs autorizadas no Google Console

#### Database Connection Error
- Verifique `MONGO_URL` no Render
- Verifique se IP do Render está na whitelist do MongoDB Atlas
- Teste conexão com MongoDB Atlas

#### Email não funciona
- Verifique `RESEND_API_KEY`
- Verifique domínio verificado no Resend
- Verifique logs no Render para erros de email

---

## 📝 NOTAS IMPORTANTES

### Segurança
- Nunca commite chaves secretas no código
- Use sempre variáveis de ambiente para dados sensíveis
- Configure JWT_SECRET forte em produção

### Performance
- Render.com free tier pode hibernar após inatividade
- Primeira requisição após hibernação pode ser lenta
- Considere upgrade para plan pago se necessário

### Monitoramento
- Use logs do Render para debug do backend
- Use Vercel analytics para monitorar frontend
- Configure alertas se necessário

---

**📞 Suporte:** Se encontrar problemas, verifique os logs dos serviços e consulte documentação oficial do Vercel e Render.com