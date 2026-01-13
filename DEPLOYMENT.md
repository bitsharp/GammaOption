# 🚀 Deploy GammaOption su Vercel

Guida completa per deployare l'applicazione su Vercel.

## 📋 Prerequisiti

1. Account Vercel (gratuito): https://vercel.com/signup
2. Node.js installato (v18+)
3. Git repository (GitHub, GitLab, o Bitbucket)

## 🔧 Setup Locale

### 1. Installa dipendenze Next.js

```powershell
cd web
npm install
```

### 2. Testa in locale

```powershell
# Development
npm run dev
# Apri http://localhost:3000

# Build test
npm run build
npm start
```

## 📦 Deploy su Vercel

### Metodo 1: Deploy tramite CLI (Raccomandato)

```powershell
# Installa Vercel CLI
npm install -g vercel

# Login a Vercel
vercel login

# Deploy (dalla root del progetto)
cd C:\projects\GammaOption
vercel

# Segui le istruzioni:
# - Set up and deploy? Y
# - Which scope? [il tuo account]
# - Link to existing project? N
# - What's your project's name? gamma-option
# - In which directory is your code located? ./
# - Want to modify settings? N

# Deploy production
vercel --prod
```

### Metodo 2: Deploy tramite Git (GitHub)

1. **Crea repository GitHub**
   ```powershell
   cd C:\projects\GammaOption
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/TUO_USERNAME/gamma-option.git
   git push -u origin main
   ```

2. **Connetti a Vercel**
   - Vai su https://vercel.com/new
   - Importa il repository GitHub
   - Vercel rileverà automaticamente Next.js
   - Click "Deploy"

## ⚙️ Configurazione Vercel

### Environment Variables

Aggiungi le variabili d'ambiente nel dashboard Vercel:

1. Vai su: Project Settings → Environment Variables
2. Aggiungi:
   - `POLYGON_API_KEY` = tua_api_key (opzionale)

### Vercel Settings

```json
{
  "buildCommand": "cd web && npm install && npm run build",
  "outputDirectory": "web/.next",
  "installCommand": "cd web && npm install",
  "framework": "nextjs"
}
```

## 🔄 Deploy Automatico

Ogni push a `main` trigghera un deploy automatico:

```powershell
git add .
git commit -m "Update features"
git push origin main
# Vercel deploya automaticamente
```

## 🌐 Custom Domain (Opzionale)

1. Vai su: Project Settings → Domains
2. Aggiungi il tuo dominio
3. Configura DNS secondo le istruzioni Vercel

Esempio:
- `gamma-option.tuodominio.com`

## 📊 API Routes

Le API Python sono automaticamente deployate come Serverless Functions:

- `https://tuo-progetto.vercel.app/api/prices` - Prezzi SPX/ES
- `https://tuo-progetto.vercel.app/api/gamma` - Analisi gamma

## 🧪 Test Deployment

Dopo il deploy, testa:

```powershell
# Test API
curl https://tuo-progetto.vercel.app/api/prices
curl https://tuo-progetto.vercel.app/api/gamma

# Test frontend
# Apri browser su https://tuo-progetto.vercel.app
```

## 🔍 Monitoring

Dashboard Vercel fornisce:
- Real-time logs
- Performance metrics
- Error tracking
- Usage statistics

Accedi: https://vercel.com/dashboard

## ⚡ Performance

### Ottimizzazioni Vercel

1. **Edge Caching**: Le API responses sono cachate
2. **CDN Globale**: Frontend servito da 70+ locations
3. **Serverless Functions**: Auto-scaling
4. **Image Optimization**: Automatico con Next.js

### Limiti Piano Gratuito

- 100 GB bandwidth/mese
- 100 GB-hrs serverless function execution
- 6,000 minutes build time
- Sufficiente per >10K utenti/mese

## 🐛 Troubleshooting

### Build Fails

```powershell
# Verifica build locale
cd web
npm run build

# Check logs su Vercel dashboard
```

### API Non Funziona

1. Verifica che `api/` directory esista
2. Check `vercel.json` configuration
3. Verifica Python dependencies in `api/requirements.txt`

### Slow Response

- Le Serverless Functions hanno cold start (~1-2s)
- Prime richieste dopo inattività sono più lente
- Considera Edge Functions per latenza minore

## 📱 Preview Deployments

Ogni branch/PR ottiene un preview URL automatico:

```powershell
git checkout -b feature/new-chart
git add .
git commit -m "Add new chart"
git push origin feature/new-chart

# Vercel crea automaticamente:
# https://gamma-option-abc123.vercel.app
```

## 🔐 Sicurezza

1. **API Keys**: Solo via Environment Variables
2. **CORS**: Configurato in API handlers
3. **Rate Limiting**: Incluso con Vercel
4. **HTTPS**: Automatico

## 💰 Costi

### Piano Gratuito (Hobby)
- ✅ Perfetto per questo progetto
- ✅ Unlimited deployments
- ✅ SSL certificato
- ✅ Analytics base

### Pro Plan ($20/mese)
- Solo se superi limiti free tier
- Advanced analytics
- Password protection
- Team collaboration

## 📚 Risorse

- [Vercel Docs](https://vercel.com/docs)
- [Next.js Docs](https://nextjs.org/docs)
- [Serverless Functions](https://vercel.com/docs/functions/serverless-functions)
- [Edge Network](https://vercel.com/docs/edge-network/overview)

## ✅ Checklist Deploy

- [ ] Repository Git creato
- [ ] Dependencies installate (`npm install`)
- [ ] Build locale testato (`npm run build`)
- [ ] Account Vercel creato
- [ ] Vercel CLI installato (opzionale)
- [ ] Environment variables configurate
- [ ] Deploy eseguito
- [ ] API testate
- [ ] Frontend testato
- [ ] Custom domain configurato (opzionale)

---

**🎉 Complimenti! La tua app è live su Vercel!**

URL: https://gamma-option-[tuo-id].vercel.app
