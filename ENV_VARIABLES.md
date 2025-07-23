# VARIÁVEIS DE AMBIENTE NECESSÁRIAS

## 🔧 BACKEND (Railway/Render)

### Obrigatórias:
```env
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/database_name?retryWrites=true&w=majority
JWT_SECRET=seu_jwt_secret_super_seguro_aqui_123456789
DB_NAME=crm_database
```

### Opcionais (para integrações):
```env
GOOGLE_CLIENT_ID=seu_google_client_id
GOOGLE_CLIENT_SECRET=seu_google_client_secret
TWILIO_ACCOUNT_SID=seu_twilio_sid
TWILIO_AUTH_TOKEN=seu_twilio_token
```

## 🌐 FRONTEND (Vercel)

```env
REACT_APP_BACKEND_URL=https://seu-backend.railway.app/api
```

## 📝 COMO OBTER CADA VARIÁVEL:

### MongoDB Atlas:
1. Crie cluster gratuito em cloud.mongodb.com
2. Conecte → Connect to application
3. Copie a connection string
4. Substitua <password> pela sua senha

### JWT_SECRET:
- Gere uma string aleatória segura (mínimo 32 caracteres)
- Pode usar: https://generate-secret.vercel.app/32

### Google Calendar (opcional):
1. Google Cloud Console → APIs & Services
2. Crie projeto → Ative Calendar API
3. Credentials → Create OAuth 2.0 client
4. Copie Client ID e Secret

### Twilio WhatsApp (opcional):
1. Crie conta em twilio.com
2. Console → Account SID e Auth Token
3. Ative WhatsApp sandbox