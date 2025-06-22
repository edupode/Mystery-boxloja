# PLANO DE IMPLEMENTAÇÃO - MYSTERY BOX STORE

## **CONTEXTO**
Aplicação Mystery Box Store com:
- Backend: FastAPI + MongoDB + Stripe + Resend + Google OAuth
- Frontend: React + Tailwind CSS  
- Sistema de autenticação, admin, produtos, carrinho, chat já implementados

## **OBJETIVOS DO UTILIZADOR**
- Deploy frontend no Vercel e backend no Render.com
- Corrigir OAuth e erro de domínio mysteryboxstore.com no Resend
- Remover botão criar conta, apenas Google login para utilizadores existentes
- Adicionar botão para tornar emails em admin
- Implementar live chat flutuante no canto inferior direito
- Admin ver chats por responder

---

## **FASE 1: PREPARAÇÃO PARA DEPLOY** ✅
**Status: CONCLUÍDO**

### Frontend (Vercel)
- [x] Criar vercel.json para configuração de deploy
- [x] Configurar variáveis de ambiente para produção
- [x] Ajustar build scripts no package.json
- [x] Configurar redirects e rewrites necessários

### Backend (Render.com)
- [x] Criar render.yaml para configuração de deploy
- [x] Configurar variáveis de ambiente para produção
- [x] Ajustar requirements.txt se necessário
- [x] Configurar comando de start para produção

### Configurações de URL
- [x] Preparar URLs de produção
- [x] Configurar CORS para domínios de produção
- [x] Ajustar configurações de segurança

### Arquivos Criados
- [x] `/app/frontend/vercel.json` - Configuração Vercel
- [x] `/app/backend/render.yaml` - Configuração Render.com
- [x] `/app/backend/.env.production.example` - Exemplo env backend
- [x] `/app/frontend/.env.production.example` - Exemplo env frontend
- [x] `/app/backend/requirements.production.txt` - Dependências otimizadas
- [x] `/app/DEPLOY_INSTRUCTIONS.md` - Instruções completas de deploy
- [x] `/app/deploy_helper.sh` - Script auxiliar de deploy

---

## **FASE 2: CORREÇÃO DO OAUTH E DOMÍNIO RESEND**
**Status: PENDENTE**

### Resend Domain Fix
- [ ] Verificar domínio mysteryboxstore.com no painel Resend
- [ ] Configurar DNS records necessários
- [ ] Testar envio de emails após verificação
- [ ] **REQUER**: Acesso ao painel Resend

### OAuth Configuration
- [ ] Verificar configuração Google OAuth para produção
- [ ] Ajustar redirect URLs no Google Console
- [ ] Testar autenticação em produção

---

## **FASE 3: MODIFICAÇÕES DE AUTENTICAÇÃO**
**Status: PENDENTE**

### Remover Criação de Conta
- [ ] Remover botão "Criar Conta" do componente Login
- [ ] Remover formulário de registo
- [ ] Manter apenas Google OAuth

### Restrição de Login
- [ ] Implementar verificação de utilizadores existentes
- [ ] Apenas permitir login Google para contas já registadas
- [ ] Mostrar mensagem apropriada para novos utilizadores

### Integração Admin
- [ ] Garantir que utilizadores Google aparecem na página admin
- [ ] Verificar sincronização de dados de utilizador

---

## **FASE 4: MELHORIAS DO ADMIN**
**Status: PENDENTE**

### Gestão de Admins
- [ ] Verificar funcionalidade existente de criar admins
- [ ] Melhorar interface se necessário
- [ ] Adicionar botão visível para tornar emails em admin
- [ ] Testar funcionalidade completa

### Interface Admin
- [ ] Verificar se todos os botões estão funcionais
- [ ] Melhorar UX da página admin se necessário

---

## **FASE 5: SISTEMA DE LIVE CHAT**
**Status: PENDENTE**

### Chat Widget Flutuante
- [ ] Criar componente de chat flutuante
- [ ] Adicionar ícone com headset no canto inferior direito
- [ ] Integrar com sistema de chat existente (backend já implementado)

### Versão Utilizador
- [ ] Interface simples de chat
- [ ] Histórico de conversas
- [ ] Notificações de mensagens

### Versão Admin
- [ ] Mostrar chats por responder
- [ ] Lista de sessões ativas
- [ ] Interface para gerir múltiplas conversas
- [ ] Notificações de novos chats

### Funcionalidades Avançadas
- [ ] Decidir: Tempo real (WebSocket) vs Refresh manual
- [ ] Sistema de notificações
- [ ] Guardar conversas/enviar por email

---

## **INFORMAÇÕES NECESSÁRIAS**

### Deploy
- [x] MongoDB Atlas configurado ✅
- [x] String de conexão testada ✅
- [ ] Contas Vercel e Render.com
- [ ] Credenciais de acesso (se necessário)

### Resend
- [x] API Key disponível ✅
- [ ] Acesso ao painel Resend para verificar domínio
- [ ] Ou usar domínio alternativo

### Google OAuth
- [x] Client ID e Secret disponíveis ✅
- [ ] Método de restrição preferido para utilizadores existentes
- [ ] Lista de emails autorizados (se aplicável)

### Live Chat
- [ ] Preferência: Tempo real vs Manual refresh
- [ ] Funcionalidades específicas desejadas

---

## **CONFIGURAÇÕES ATUALIZADAS**

### ✅ MongoDB Atlas
- **Status:** Configurado e Testado
- **Database:** mystery_box_store
- **Admin:** eduardocorreia3344@gmail.com
- **Categorias:** 8 categorias ativas carregadas

### ✅ APIs Disponíveis
- **Resend API:** Configurado
- **Google OAuth:** Client ID e Secret disponíveis
- **Stripe:** Chaves de teste configuradas

---

## **NOTAS TÉCNICAS**

### Backend URLs
- Atual: `https://7674d4fc-fa3c-48f4-b6dc-16e88f031003.preview.emergentagent.com`
- Produção: Será definido após deploy no Render.com

### Database
- ✅ MongoDB Atlas configurado: `cluster0.f2mbcc6.mongodb.net`
- ✅ Database: mystery_box_store
- ✅ Conexão testada e funcionando

### APIs Externas
- ✅ Stripe: Configurado para teste
- ✅ Google OAuth: Client ID e Secret disponíveis
- ✅ Resend: API Key disponível (domínio pendente verificação)

---

**ÚLTIMA ATUALIZAÇÃO**: $(date)
**FASE ATUAL**: FASE 1 - CONCLUÍDA ✅
**PRÓXIMA FASE**: FASE 2 - Correção OAuth e Domínio Resend