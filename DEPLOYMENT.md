# Deployment Guide

This guide covers detailed deployment instructions for the GenAI Research Tool across different cloud platforms.

## Table of Contents

- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Railway Deployment (Recommended)](#railway-deployment-recommended)
- [Render.com Deployment](#rendercom-deployment)
- [Fly.io Deployment](#flyio-deployment)
- [Docker-based Deployment](#docker-based-deployment)
- [Post-Deployment Setup](#post-deployment-setup)

## Pre-Deployment Checklist

Before deploying, ensure you have:

- [ ] All API keys ready:
  - OpenAI API key (required)
  - Tavily API key (optional)
  - SERP API key (optional)
  - SlidesGPT API key (optional)
- [ ] Generated a secure SECRET_KEY for JWT tokens
- [ ] Decided on your deployment platform
- [ ] Repository pushed to GitHub/GitLab
- [ ] Reviewed and updated CORS_ORIGINS for production

### Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using OpenSSL
openssl rand -base64 32
```

## Railway Deployment (Recommended)

Railway.app offers $5/month credit which is sufficient for running this application at no cost.

### Why Railway?

- ✅ Free $5/month credit (enough for this app)
- ✅ Simple GitHub integration
- ✅ Automatic deployments
- ✅ Built-in environment variable management
- ✅ PostgreSQL database available (if you want to upgrade from SQLite)
- ✅ Automatic HTTPS

### Step-by-Step Railway Deployment

#### 1. Deploy Backend

1. **Sign up** at [railway.app](https://railway.app)

2. **Create New Project** → "Deploy from GitHub repo"

3. **Select Repository** → Choose your repository

4. **Configure Service**:
   - Click "Add variables"
   - Add the following environment variables:
     ```
     SECRET_KEY=<your-generated-secret-key>
     ALGORITHM=HS256
     OPENAI_API_KEY=<your-openai-key>
     TAVILY_API_KEY=<your-tavily-key>
     SERP_API_KEY=<your-serp-key>
     SLIDESGPT_API_KEY=<your-slidesgpt-key>
     LOG_LEVEL=INFO
     BACKEND_BASE=${{RAILWAY_PUBLIC_DOMAIN}}
     CORS_ORIGINS=https://your-frontend-domain.com
     ENVIRONMENT=production
     ```

5. **Set Root Directory**:
   - Go to Settings → Root Directory
   - Set to: `backend`

6. **Railway will automatically**:
   - Detect the `Dockerfile`
   - Build the image
   - Deploy the backend
   - Provide a public URL (e.g., `https://your-app.up.railway.app`)

7. **Copy the backend URL** for frontend configuration

#### 2. Deploy Frontend (Option A: Vercel)

1. **Sign up** at [vercel.com](https://vercel.com)

2. **Import Project** → Connect GitHub repository

3. **Configure Build Settings**:
   - Framework Preset: Create React App
   - Root Directory: `./` (leave as project root)
   - Build Command: `npm run build`
   - Output Directory: `build`

4. **Environment Variables**:
   ```
   REACT_APP_API_BASE=https://your-backend.up.railway.app
   ```

5. **Deploy**

6. **Update Backend CORS**:
   - Go back to Railway
   - Update `CORS_ORIGINS` to include your Vercel URL:
     ```
     CORS_ORIGINS=https://your-app.vercel.app
     ```

#### 2. Deploy Frontend (Option B: Railway)

1. **Create New Service** in the same Railway project

2. **Connect same repository**

3. **Configure Service**:
   - Root Directory: `./` (project root)
   - Build Command: `npm run build`
   - Start Command: Auto-detected from Dockerfile

4. **Environment Variables**:
   ```
   REACT_APP_API_BASE=https://your-backend.up.railway.app
   ```

5. **Deploy**

### Railway with PostgreSQL (Optional Upgrade)

If you need better database performance:

1. **Add PostgreSQL** to your Railway project
   - Click "New" → "Database" → "PostgreSQL"

2. **Update Backend Environment**:
   ```
   DATABASE_URL=${{PGDATABASE_URL}}
   ```

3. **Update `backend/app/database.py`**:
   ```python
   import os
   from sqlalchemy import create_engine

   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./genai.db")
   # Railway PostgreSQL URLs start with postgres://, SQLAlchemy needs postgresql://
   if DATABASE_URL.startswith("postgres://"):
       DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

   engine = create_engine(DATABASE_URL)
   ```

## Render.com Deployment

Render offers a free tier with some limitations (services sleep after 15 min of inactivity).

### Backend Deployment

1. **Sign up** at [render.com](https://render.com)

2. **Create Web Service**:
   - New → Web Service
   - Connect repository
   - Name: `genai-backend`
   - Region: Choose closest to your users
   - Branch: `main`
   - Root Directory: `backend`
   - Runtime: Python 3
   - Build Command:
     ```bash
     pip install --use-pep517 sgmllib3k==1.0.0 && pip install -r requirements.txt
     ```
   - Start Command:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

3. **Environment Variables**:
   Add all required variables (same as Railway)

4. **Deploy**

### Frontend Deployment

1. **Create Static Site**:
   - New → Static Site
   - Connect repository
   - Build Command: `npm run build`
   - Publish Directory: `build`

2. **Environment Variables**:
   ```
   REACT_APP_API_BASE=https://your-backend.onrender.com
   ```

## Fly.io Deployment

Fly.io offers generous free tier and excellent global performance.

### Prerequisites

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login
```

### Backend Deployment

1. **Initialize Fly App**:
   ```bash
   cd backend
   flyctl launch
   # Choose app name, region
   # Say NO to PostgreSQL for now (using SQLite)
   # Say NO to deploy now
   ```

2. **Set Environment Variables**:
   ```bash
   flyctl secrets set SECRET_KEY="your-secret-key"
   flyctl secrets set OPENAI_API_KEY="your-key"
   flyctl secrets set TAVILY_API_KEY="your-key"
   flyctl secrets set SERP_API_KEY="your-key"
   flyctl secrets set SLIDESGPT_API_KEY="your-key"
   flyctl secrets set CORS_ORIGINS="https://your-frontend-domain.fly.dev"
   flyctl secrets set ENVIRONMENT="production"
   ```

3. **Deploy**:
   ```bash
   flyctl deploy
   ```

4. **Get URL**:
   ```bash
   flyctl info
   # Note the hostname
   ```

### Frontend Deployment

1. **Initialize Fly App**:
   ```bash
   cd ..  # Back to root
   flyctl launch
   ```

2. **Configure for Frontend**:
   Edit `fly.toml`:
   ```toml
   [build]
     dockerfile = "Dockerfile"

   [build.args]
     REACT_APP_API_BASE = "https://your-backend.fly.dev"
   ```

3. **Deploy**:
   ```bash
   flyctl deploy
   ```

## Docker-based Deployment

For AWS, Google Cloud, Azure, or any Docker-compatible platform.

### Using Docker Compose (VPS/EC2)

1. **Setup Server**:
   ```bash
   # SSH into your server
   ssh user@your-server-ip

   # Install Docker and Docker Compose
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo apt-get install docker-compose-plugin
   ```

2. **Clone Repository**:
   ```bash
   git clone <your-repo-url>
   cd research_tool_seethaV1
   ```

3. **Configure Environment**:
   ```bash
   cp backend/.env.example backend/.env
   nano backend/.env  # Edit with your keys
   ```

4. **Update CORS**:
   ```bash
   # In backend/.env
   CORS_ORIGINS=http://your-server-ip,https://your-domain.com
   ```

5. **Deploy**:
   ```bash
   docker-compose up -d --build
   ```

6. **Setup Nginx Reverse Proxy** (optional but recommended):
   ```nginx
   # /etc/nginx/sites-available/genai
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:80;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /api/ {
           proxy_pass http://localhost:8000/;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

7. **Setup SSL with Let's Encrypt**:
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### Google Cloud Run

1. **Build and Push**:
   ```bash
   # Backend
   gcloud builds submit --tag gcr.io/PROJECT-ID/genai-backend ./backend

   # Frontend
   gcloud builds submit --tag gcr.io/PROJECT-ID/genai-frontend .
   ```

2. **Deploy Backend**:
   ```bash
   gcloud run deploy genai-backend \
     --image gcr.io/PROJECT-ID/genai-backend \
     --platform managed \
     --set-env-vars SECRET_KEY=xxx,OPENAI_API_KEY=yyy
   ```

3. **Deploy Frontend**:
   ```bash
   gcloud run deploy genai-frontend \
     --image gcr.io/PROJECT-ID/genai-frontend \
     --platform managed \
     --set-env-vars REACT_APP_API_BASE=https://backend-url
   ```

## Post-Deployment Setup

### 1. Create First User

Once deployed, create your first user:

```bash
curl -X POST https://your-backend-url/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"secure-password"}'
```

### 2. Test the Deployment

1. **Access Frontend**: Visit your frontend URL
2. **Login**: Use the credentials you created
3. **Test API**: Check `https://your-backend-url/docs` for API documentation

### 3. Monitor Logs

#### Railway
```bash
# View logs in Railway dashboard
# Or use CLI:
railway logs
```

#### Render
- View logs in Render dashboard

#### Fly.io
```bash
flyctl logs
```

#### Docker
```bash
docker-compose logs -f
```

### 4. Setup Backups

For SQLite database:

```bash
# Backup command (add to cron)
docker exec genai-backend sqlite3 /app/genai.db ".backup '/app/backup.db'"

# Download backup
docker cp genai-backend:/app/backup.db ./backup-$(date +%Y%m%d).db
```

For PostgreSQL (if using):
- Use your cloud provider's automated backup features
- Railway: Automatic backups included
- Render: Backup from dashboard

## Troubleshooting Deployment Issues

### Issue: Build Fails on sgmllib3k

**Solution**: Ensure Dockerfile includes:
```dockerfile
RUN pip install --use-pep517 sgmllib3k==1.0.0 && \
    pip install -r requirements.txt
```

### Issue: CORS Errors in Production

**Solution**: Update `CORS_ORIGINS` environment variable:
```bash
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
```

### Issue: Database Not Persisting

**Solution for Docker**:
- Check volume mounts in docker-compose.yml
- Ensure directories have correct permissions

**Solution for Cloud**:
- Use managed database service
- Configure persistent volumes

### Issue: High Memory Usage

**Solution**:
- ChromaDB can be memory-intensive
- Increase service memory limit
- Consider using external ChromaDB service

### Issue: Slow Cold Starts

**Solution**:
- Railway/Render free tier: Services sleep after inactivity
- Upgrade to paid tier for always-on services
- Or use a keep-alive service to ping periodically

## Cost Optimization Tips

1. **Use Free Tiers**:
   - Railway: $5/month credit
   - Render: Free tier with sleep
   - Vercel: Unlimited for personal projects

2. **Optimize Images**:
   - Use multi-stage Docker builds
   - Minimize layer sizes

3. **Database**:
   - SQLite is free and sufficient for low traffic
   - Upgrade to PostgreSQL only when needed

4. **CDN**:
   - Use Vercel/Netlify for frontend (includes CDN)
   - Serve static assets from cloud storage

## Security Best Practices

1. **Always use HTTPS** in production
2. **Rotate API keys** regularly
3. **Use strong SECRET_KEY** for JWT
4. **Enable rate limiting** (consider adding to backend)
5. **Regular updates**: Keep dependencies updated
6. **Monitor logs** for suspicious activity
7. **Backup database** regularly

## Need Help?

If you encounter issues during deployment:
1. Check service logs first
2. Verify all environment variables are set
3. Test API endpoints using /docs
4. Check GitHub Issues for known problems
5. Create a new issue with deployment logs

---

**Happy Deploying! 🚀**
