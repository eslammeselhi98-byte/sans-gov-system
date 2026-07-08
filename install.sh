#!/usr/bin/env bash
# ============================================================
# SANS PMS — One-Command Installation Script
# ============================================================
set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   SANS International — Project Management System          ║"
echo "║   Installation Wizard                                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ─── Check prerequisites ────────────────────────────────────

command -v docker >/dev/null 2>&1 || { echo "❌ Docker is not installed. Install from https://docs.docker.com/get-docker/"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "❌ Docker Compose v2 is required."; exit 1; }

echo "✅ Docker found: $(docker --version)"
echo ""

# ─── Setup .env ──────────────────────────────────────────────

if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env

    # Generate secure secrets automatically
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
    REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)

    # Cross-platform sed
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SED_INPLACE="sed -i ''"
    else
        SED_INPLACE="sed -i"
    fi

    $SED_INPLACE "s|CHANGE_THIS_TO_64_CHAR_RANDOM_STRING_USE_OPENSSL_RAND_HEX_32|${SECRET_KEY}|g" .env
    $SED_INPLACE "s|CHANGE_THIS_STRONG_PASSWORD|${DB_PASSWORD}|g" .env
    $SED_INPLACE "s|CHANGE_THIS_REDIS_PASSWORD|${REDIS_PASSWORD}|g" .env

    echo "✅ .env created with auto-generated secure secrets."
    echo ""
    echo "⚠️  IMPORTANT: Please now edit .env and add:"
    echo "    1. TELEGRAM_BOT_TOKEN  (from @BotFather on Telegram)"
    echo "    2. ANTHROPIC_API_KEY   (from console.anthropic.com)"
    echo "    3. SMTP credentials    (optional, for email notifications)"
    echo ""
    read -p "Press Enter once you've updated .env, or Ctrl+C to exit and edit later... "
else
    echo "✅ .env already exists, using existing configuration."
fi

# ─── Build and start ─────────────────────────────────────────

echo ""
echo "🔨 Building Docker images (this may take a few minutes)..."
docker compose build

echo ""
echo "🚀 Starting all services..."
docker compose up -d db redis
echo "⏳ Waiting for database to be ready..."
sleep 10

docker compose up -d backend
echo "⏳ Waiting for backend to initialize..."
sleep 8

docker compose up -d

echo ""
echo "📊 Checking service health..."
sleep 5
docker compose ps

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   ✅ Installation Complete!                                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Web Dashboard:    http://localhost"
echo "📚 API Docs:         http://localhost/docs"
echo "🗄️  Database Manager: http://localhost:5050  (run: docker compose --profile tools up -d pgadmin)"
echo ""
echo "🔑 Default Admin Login:"
echo "   Email:    admin@sans-intl.com"
echo "   Password: Admin@123"
echo "   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY after first login!"
echo ""
echo "🤖 Telegram Bot: Search for your bot on Telegram and send /start"
echo ""
echo "📖 Next steps:"
echo "   1. Login to the dashboard and change the admin password"
echo "   2. Go to Settings → Users to link employee Telegram accounts"
echo "   3. Create your first project"
echo "   4. Import your Primavera XER or Excel BOQ files"
echo ""
echo "📋 View logs:        docker compose logs -f"
echo "🛑 Stop everything:  docker compose down"
echo "🔄 Restart:          docker compose restart"
echo ""
