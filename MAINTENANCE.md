# GeoFeed — Production Maintenance Guide

## Post-Deployment Checklist

### Immediate (first 24 hours)

- [ ] Confirm site is reachable: `curl -I https://yourdomain.com` returns `HTTP/2 200`
- [ ] Run a test search using no-key platforms (Bluesky, Mastodon, TikTok, Reddit, Telegram)
- [ ] Check startup logs: `sudo journalctl -u geofeed -n 50`
- [ ] Verify Nginx is running: `sudo systemctl status nginx`
- [ ] Confirm SSL certificate is valid: `sudo certbot certificates`
- [ ] Test live mode (SSE) in the browser — enable 🟢 Live and confirm new results stream in
- [ ] Confirm `config.yaml` is **not** tracked by git: `git status` should not list it
- [ ] Revoke and regenerate any API keys that were exposed in plaintext during setup

---

## Ongoing Checks

### Weekly

- [ ] Check for errors in the last 7 days:
  ```bash
  sudo journalctl -u geofeed --since "7 days ago" | grep -i error
  ```
- [ ] Review disk usage (logs accumulate): `df -h`
- [ ] Check YouTube API quota in [Google Cloud Console](https://console.cloud.google.com/)
- [ ] Verify SSL certificate will auto-renew: `sudo certbot certificates`
- [ ] Pull and redeploy latest changes if available:
  ```bash
  cd /home/ubuntu/geofeed
  git pull origin main
  source .venv/bin/activate
  pip install -r requirements.txt
  sudo systemctl restart geofeed
  ```

### Monthly

- [ ] Run the full test suite on the server:
  ```bash
  source .venv/bin/activate && pytest -v
  ```
- [ ] Rotate API keys (YouTube, Flickr, Twitter) as a security precaution
- [ ] Update Python dependencies:
  ```bash
  pip install --upgrade -r requirements.txt
  sudo systemctl restart geofeed
  ```
- [ ] Manually test each platform — check which providers are returning results
- [ ] Review and prune Nginx access logs:
  ```bash
  sudo truncate -s 0 /var/log/nginx/access.log
  sudo truncate -s 0 /var/log/nginx/error.log
  ```
- [ ] Verify firewall rules are still correct: `sudo ufw status`
- [ ] Check for security updates: `sudo apt update && sudo apt upgrade -y`

### Quarterly

- [ ] Review all API keys — identify any that are no longer needed and revoke them
- [ ] Check for new versions of Python dependencies: `pip list --outdated`
- [ ] Review the [GitHub releases](https://github.com/foxtrotglobal/geofeed/releases) for any breaking changes
- [ ] Verify backups of `config.yaml` are stored securely off-server
- [ ] Re-test Instagram session cookie — it expires and must be refreshed periodically

---

## Troubleshooting

### Diagnosing common problems

| Symptom | First check |
|---|---|
| Site returns 502 Bad Gateway | Gunicorn crashed — check `sudo journalctl -u geofeed -n 20` |
| Site not loading at all | `sudo systemctl status nginx geofeed` |
| Live mode (SSE) not streaming | Ensure `proxy_buffering off` is in Nginx config |
| Platform returns no results | API key expired, or platform changed its endpoint |
| Results suddenly empty across all platforms | Check reverse geocoding: `curl "https://nominatim.openstreetmap.org/reverse?lat=40.7&lon=-74.0&format=json"` |
| High memory or CPU | Reduce Gunicorn workers: change `-w 4` to `-w 2` in systemd service |
| SSL certificate expired | `sudo certbot renew` |
| Instagram returns 401 | Session cookie expired — recapture from browser DevTools |

### Restart procedures

```bash
# Restart the app only
sudo systemctl restart geofeed

# Restart Nginx only
sudo systemctl restart nginx

# Restart both
sudo systemctl restart geofeed nginx

# Full reload after config change
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl daemon-reload && sudo systemctl restart geofeed
```

### Reading logs

```bash
# Live log stream (Ctrl+C to exit)
sudo journalctl -u geofeed -f

# Last 100 lines
sudo journalctl -u geofeed -n 100

# Errors only
sudo journalctl -u geofeed -p err

# Nginx error log
sudo tail -f /var/log/nginx/error.log

# Nginx access log
sudo tail -f /var/log/nginx/access.log
```

---

## Platform-Specific Notes

| Platform | What can break | Fix |
|---|---|---|
| **YouTube** | Daily API quota (10,000 units/day free) | Reduce `max_results`, or enable billing in Google Cloud |
| **Instagram** | Session cookie expires (~30–90 days) | Re-capture cookie from browser DevTools |
| **X / Twitter** | Bearer token revoked | Regenerate in Twitter Developer Portal |
| **Telegram** | Channel usernames change or go private | Update channel list in `config.yaml` |
| **Aparat** | API endpoint changes (undocumented) | Check `providers/aparat.py` for updated URL |
| **TikTok** | Scraping blocked by bot detection | Add `ms_token` cookie from browser to `config.yaml` |
| **Facebook** | App token expires | Regenerate in Meta Developer Portal |
| **Rubika** | API not publicly documented — may return empty | Expected behaviour; no fix needed |

---

## Security Reminders

- **Never commit `config.yaml`** — it is listed in `.gitignore` but always double-check with `git status`
- **Use environment variables** in hosted environments instead of `config.yaml`
- **Rotate keys immediately** if they are ever printed to logs, terminal output, or version control
- **Keep dependencies updated** — `pip install --upgrade -r requirements.txt` monthly
- **Restrict server access** — only ports 80 and 443 should be publicly accessible; port 5000 (Gunicorn) should be blocked by the firewall

---

## Quick Reference

```bash
sudo systemctl restart geofeed          # Restart app
sudo systemctl restart nginx            # Restart Nginx
sudo journalctl -u geofeed -f           # Live logs
sudo certbot renew --dry-run            # Test SSL auto-renewal
sudo nginx -t                           # Validate Nginx config
df -h                                   # Check disk space
sudo ufw status                         # Check firewall rules
```
