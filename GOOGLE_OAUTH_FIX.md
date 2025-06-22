# 🔧 GOOGLE OAUTH - CORREÇÃO PARA VERCEL

## ❌ **PROBLEMA IDENTIFICADO**
O Google OAuth está falhando porque o domínio `mystery-box-loja.vercel.app` não está autorizado no Google Cloud Console.

## ✅ **SOLUÇÃO: CONFIGURAR GOOGLE CLOUD CONSOLE**

### 1. Acesse o Google Cloud Console
1. Vá para [Google Cloud Console](https://console.cloud.google.com)
2. Selecione seu projeto (ou crie um se necessário)

### 2. Configure OAuth Consent Screen
1. **APIs & Services > OAuth consent screen**
2. Verifique se está configurado como:
   - **User Type:** External (para permitir qualquer usuário)
   - **Application name:** Mystery Box Store
   - **Authorized domains:** Adicione `vercel.app`

### 3. Configure OAuth 2.0 Client IDs
1. **APIs & Services > Credentials**
2. Encontre o Client ID: `231244828407-jqacf8ombm44aeh5scn544nvokvbkqis.apps.googleusercontent.com`
3. **Clique para editar**

### 4. Adicione URLs Autorizadas

#### **Authorized JavaScript origins:**
```
https://mystery-box-loja.vercel.app
http://localhost:3000
https://localhost:3000
```

#### **Authorized redirect URIs:**
```
https://mystery-box-loja.vercel.app
https://mystery-box-loja.vercel.app/
http://localhost:3000
https://localhost:3000
```

### 5. Salve as Configurações
Clique em **"Save"** no Google Cloud Console.

## 🔍 **VERIFICAÇÃO ADICIONAL**

### Se o Client ID não existir:
1. **Crie um novo OAuth 2.0 Client ID:**
   - Application type: **Web application**
   - Name: **Mystery Box Store**
   - Authorized JavaScript origins: (URLs acima)
   - Authorized redirect URIs: (URLs acima)

2. **Copie o novo Client ID e atualize no Vercel:**
   - Vá para Vercel Dashboard > Settings > Environment Variables
   - Atualize `REACT_APP_GOOGLE_CLIENT_ID` com o novo valor

## 🚀 **TESTAR APÓS CONFIGURAÇÃO**

1. **Aguarde alguns minutos** (as mudanças podem demorar para propagar)
2. **Teste o login** em `https://mystery-box-loja.vercel.app`
3. **Verifique o console do browser** para ver se há erros específicos

## 🐛 **DEBUG ADICIONAL**

Se ainda não funcionar, verifique:

### No Console do Browser:
```javascript
// Verifique se as variáveis estão corretas
console.log('Backend URL:', process.env.REACT_APP_BACKEND_URL);
console.log('Google Client ID:', process.env.REACT_APP_GOOGLE_CLIENT_ID);
```

### Possíveis erros e soluções:
- **"redirect_uri_mismatch"** → Verificar URLs no Google Console
- **"unauthorized_client"** → Verificar se Client ID está correto
- **"access_denied"** → Usuário negou acesso (normal)

## 📝 **RESUMO DAS MUDANÇAS NECESSÁRIAS**

### No Google Cloud Console:
1. ✅ Adicionar `vercel.app` aos domínios autorizados
2. ✅ Adicionar `https://mystery-box-loja.vercel.app` às origins
3. ✅ Adicionar URLs de redirect

### No Vercel (já configurado):
- ✅ `REACT_APP_BACKEND_URL` = `https://mystery-boxloja.onrender.com`
- ✅ `REACT_APP_GOOGLE_CLIENT_ID` = `231244828407-jqacf8ombm44aeh5scn544nvokvbkqis.apps.googleusercontent.com`

**Após configurar o Google Cloud Console, o OAuth funcionará perfeitamente!** 🎉