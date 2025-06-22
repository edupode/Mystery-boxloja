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
**Status: EM PROGRESSO**

### Frontend (Vercel)
- [ ] Criar vercel.json para configuração de deploy
- [ ] Configurar variáveis de ambiente para produção
- [ ] Ajustar build scripts no package.json
- [ ] Configurar redirects e rewrites necessários

### Backend (Render.com)
- [ ] Criar render.yaml para configuração de deploy
- [ ] Configurar variáveis de ambiente para produção
- [ ] Ajustar requirements.txt se necessário
- [ ] Configurar comando de start para produção

### Configurações de URL
- [ ] Preparar URLs de produção
- [ ] Configurar CORS para domínios de produção
- [ ] Ajustar configurações de segurança

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
- [ ] Contas Vercel e Render.com
- [ ] Credenciais de acesso (se necessário)

### Resend
- [ ] Acesso ao painel Resend para verificar domínio
- [ ] Ou usar domínio alternativo

### Google OAuth
- [ ] Método de restrição preferido para utilizadores existentes
- [ ] Lista de emails autorizados (se aplicável)

### Live Chat
- [ ] Preferência: Tempo real vs Manual refresh
- [ ] Funcionalidades específicas desejadas

---

## **NOTAS TÉCNICAS**

### Backend URLs
- Atual: `https://95c49646-803a-4ef0-a8ef-b18b30f80cf6.preview.emergentagent.com`
- Produção: Será definido após deploy no Render.com

### Database
- MongoDB local atual
- Precisará de MongoDB Atlas ou similar para produção

### APIs Externas
- Stripe: Configurado para teste
- Google OAuth: Configurado
- Resend: Configurado mas domínio não verificado

---

**ÚLTIMA ATUALIZAÇÃO**: $(date)
**FASE ATUAL**: FASE 1 - Preparação para Deploy