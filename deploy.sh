#!/usr/bin/env bash
# =============================================================================
# GeoFeed Deployment Script
# Automates setup on a fresh Ubuntu 22.04+ / Debian 12+ server.
#
# Usage:
#   # Interactive (prompts for domain + API keys):
#   curl -fsSL https://raw.githubusercontent.com/foxtrotglobal/geofeed/main/deploy.sh | bash
#
#   # Non-interactive (set env vars first):
#   DOMAIN=mysite.com YOUTUBE_API_KEY=xyz bash deploy.sh
#
# Optional environment variables (all can be set or left empty):
#   DOMAIN                  Your domain name (e.g. geofeed.example.com)
#   APP_DIR                 Install path (default: /opt/geofeed)
#   APP_USER                Linux user to run the app (default: geofeed)
#   YOUTUBE_API_KEY
#   FLICKR_API_KEY
#   TWITTER_BEARER_TOKEN
#   INSTAGRAM_SESSION_COOKIE
#   SNAPCHAT_SESSION_COOKIE
#   TIKTOK_MS_TOKEN
#   TIKTOK_TTWID
#   FACEBOOK_APP_ID
#   FACEBOOK_APP_SECRET
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
header()  { echo -e "\n${BOLD}${BLUE}══ $* ══${NC}\n"; }

# ── Defaults ─────────────────────────────────────────────────────────────────
APP_DIR="${APP_DIR:-/opt/geofeed}"
APP_USER="${APP_USER:-geofeed}"
REPO_URL="https://github.com/foxtrotglobal/geofeed.git"
PYTHON_MIN="3.11"

# ── Root check ───────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  error "This script must be run as root (use sudo)."
fi

# =============================================================================
# 1. COLLECT CONFIGURATION
# =============================================================================
header "GeoFeed Deployment Setup"

if [[ -z "${DOMAIN:-}" ]]; then
  read -rp "Enter your domain name (e.g. geofeed.example.com), or press Enter to skip HTTPS: " DOMAIN
fi

if [[ -z "${YOUTUBE_API_KEY:-}" ]]; then
  read -rp "YouTube API key (Enter to skip): " YOUTUBE_API_KEY
fi
if [[ -z "${TWITTER_BEARER_TOKEN:-}" ]]; then
  read -rp "Twitter/X Bearer Token (Enter to skip): " TWITTER_BEARER_TOKEN
fi
if [[ -z "${INSTAGRAM_SESSION_COOKIE:-}" ]]; then
  read -rp "Instagram session cookie (Enter to skip): " INSTAGRAM_SESSION_COOKIE
fi
if [[ -z "${SNAPCHAT_SESSION_COOKIE:-}" ]]; then
  read -rp "Snapchat session cookie (Enter to skip): " SNAPCHAT_SESSION_COOKIE
fi

echo ""
info "Domain:   ${DOMAIN:-'(none — HTTP only)'}"
info "App dir:  $APP_DIR"
info "App user: $APP_USER"
echo ""

# =============================================================================
# 2. SYSTEM DEPENDENCIES
# =============================================================================
header "Installing system dependencies"

apt-get update -qq
apt-get install -y -qq \
  git python3 python3-pip python3-venv \
  nginx certbot python3-certbot-nginx \
  curl wget build-essential \
  libnss3 libatk-bridge2.0-0 libxcomposite1 libxdamage1 \
  libxfixes3 libxrandr2 libgbm1 libxkbcommon0 libasound2 \
  libpango-1.0-0 libcairo2 libpangocairo-1.0-0 \
  libatspi2.0-0 libgtk-3-0 2>/dev/null || true

# Verify Python version
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if python3 -c "import sys; sys.exit(0 if (sys.version_info >= (3,11)) else 1)"; then
  success "Python $PYTHON_VER found"
else
  error "Python $PYTHON_MIN+ required, found $PYTHON_VER"
fi

# =============================================================================
# 3. CREATE APP USER
# =============================================================================
header "Creating application user"

if id "$APP_USER" &>/dev/null; then
  info "User '$APP_USER' already exists"
else
  useradd --system --shell /bin/bash --create-home "$APP_USER"
  success "Created user '$APP_USER'"
fi

# =============================================================================
# 4. CLONE / UPDATE REPOSITORY
# =============================================================================
header "Deploying application code"

if [[ -d "$APP_DIR/.git" ]]; then
  info "Repository already exists — pulling latest changes..."
  sudo -u "$APP_USER" git -C "$APP_DIR" pull origin main
else
  info "Cloning repository to $APP_DIR..."
  git clone "$REPO_URL" "$APP_DIR"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi
success "Code deployed to $APP_DIR"

# =============================================================================
# 5. PYTHON VIRTUAL ENVIRONMENT
# =============================================================================
header "Setting up Python environment"

VENV="$APP_DIR/.venv"
if [[ ! -d "$VENV" ]]; then
  sudo -u "$APP_USER" python3 -m venv "$VENV"
fi

sudo -u "$APP_USER" "$VENV/bin/pip" install --quiet --upgrade pip
sudo -u "$APP_USER" "$VENV/bin/pip" install --quiet -r "$APP_DIR/requirements.txt" gunicorn

success "Python dependencies installed"

# =============================================================================
# 6. PLAYWRIGHT + CHROMIUM (for Snapchat)
# =============================================================================
header "Installing Playwright + Chromium (for Snapchat)"

sudo -u "$APP_USER" "$VENV/bin/pip" install --quiet playwright
PLAYWRIGHT_BROWSERS_PATH=/opt/playwright \
  sudo -u "$APP_USER" "$VENV/bin/playwright" install chromium --with-deps 2>/dev/null || {
  warn "Playwright Chromium install failed — Snapchat provider will be disabled"
}
success "Playwright ready"

# =============================================================================
# 7. WRITE config.yaml
# =============================================================================
header "Writing configuration"

CONFIG="$APP_DIR/config.yaml"
if [[ -f "$CONFIG" ]]; then
  warn "config.yaml already exists — skipping (edit manually if needed)"
else
  cat > "$CONFIG" <<YAML
# GeoFeed Configuration — generated by deploy.sh
# Edit this file to add or update credentials.

youtube:
  api_key: "${YOUTUBE_API_KEY:-}"

flickr:
  api_key: "${FLICKR_API_KEY:-}"

instagram:
  session_cookie: "${INSTAGRAM_SESSION_COOKIE:-}"

twitter:
  bearer_token: "${TWITTER_BEARER_TOKEN:-}"

tiktok:
  ms_token: "${TIKTOK_MS_TOKEN:-}"
  ttwid: "${TIKTOK_TTWID:-}"

bluesky:
  identifier: ""
  app_password: ""

mastodon:
  instance: "mastodon.social"
  access_token: ""

snapchat:
  session_cookie: "${SNAPCHAT_SESSION_COOKIE:-}"

facebook:
  app_id: "${FACEBOOK_APP_ID:-}"
  app_secret: "${FACEBOOK_APP_SECRET:-}"

telegram:
  bot_token: ""

aparat:
rubika:
reddit:
  subreddits: ""
YAML
  chown "$APP_USER:$APP_USER" "$CONFIG"
  chmod 600 "$CONFIG"
  success "config.yaml written"
fi

# =============================================================================
# 8. SYSTEMD SERVICE
# =============================================================================
header "Creating systemd service"

SERVICE_FILE="/etc/systemd/system/geofeed.service"
GUNICORN="$VENV/bin/gunicorn"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=GeoFeed — Social Media Geo Search
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
ExecStart=${GUNICORN} -w 4 -b 127.0.0.1:5000 --timeout 120 server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable geofeed
systemctl restart geofeed
sleep 2

if systemctl is-active --quiet geofeed; then
  success "geofeed service is running"
else
  error "geofeed service failed to start. Check: journalctl -u geofeed -n 30"
fi

# =============================================================================
# 9. NGINX
# =============================================================================
header "Configuring Nginx"

NGINX_CONF="/etc/nginx/sites-available/geofeed"
SERVER_NAME="${DOMAIN:-_}"

cat > "$NGINX_CONF" <<NGINX
server {
    listen 80;
    server_name ${SERVER_NAME};

    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_set_header X-Accel-Buffering no;
    }
}
NGINX

ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/geofeed
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
success "Nginx configured"

# =============================================================================
# 10. HTTPS (optional)
# =============================================================================
if [[ -n "${DOMAIN:-}" && "$DOMAIN" != "_" ]]; then
  header "Obtaining SSL certificate for $DOMAIN"
  read -rp "Enter email for Let's Encrypt certificate (or Enter to skip HTTPS): " LE_EMAIL
  if [[ -n "$LE_EMAIL" ]]; then
    certbot --nginx -d "$DOMAIN" --email "$LE_EMAIL" --agree-tos --non-interactive --redirect && \
      success "SSL certificate obtained — HTTPS enabled" || \
      warn "Certbot failed — running on HTTP only"
  fi
fi

# =============================================================================
# 11. FIREWALL
# =============================================================================
header "Configuring firewall"

if command -v ufw &>/dev/null; then
  ufw allow 'Nginx Full' 2>/dev/null || true
  ufw delete allow 5000 2>/dev/null || true
  success "Firewall updated"
fi

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   GeoFeed deployment complete! ✓     ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

if [[ -n "${DOMAIN:-}" && "$DOMAIN" != "_" ]]; then
  echo -e "  ${BOLD}URL:${NC}     https://${DOMAIN}"
else
  SERVER_IP=$(hostname -I | awk '{print $1}')
  echo -e "  ${BOLD}URL:${NC}     http://${SERVER_IP}"
fi

echo -e "  ${BOLD}Config:${NC}  ${APP_DIR}/config.yaml"
echo -e "  ${BOLD}Logs:${NC}    sudo journalctl -u geofeed -f"
echo -e "  ${BOLD}Restart:${NC} sudo systemctl restart geofeed"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo -e "  1. Edit ${APP_DIR}/config.yaml to add any missing API keys"
echo -e "  2. sudo systemctl restart geofeed"
echo -e "  3. See MAINTENANCE.md for ongoing maintenance tasks"
echo ""
