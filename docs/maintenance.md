# Maintenance

See the full [MAINTENANCE.md](https://github.com/foxtrotglobal/geofeed/blob/main/MAINTENANCE.md) for the complete post-deployment operations guide.

## Quick reference

```bash
sudo systemctl restart geofeed          # Restart app
sudo systemctl restart nginx            # Restart Nginx
sudo journalctl -u geofeed -f           # Live logs
sudo certbot renew --dry-run            # Test SSL auto-renewal
sudo nginx -t                           # Validate Nginx config
df -h                                   # Check disk space
sudo ufw status                         # Check firewall
```

## Post-deployment checklist

- [ ] Confirm site is reachable: `curl -I https://yourdomain.com`
- [ ] Run a test search using Bluesky, Mastodon, Reddit (no key needed)
- [ ] Verify SSL certificate: `sudo certbot certificates`
- [ ] Test live mode (SSE) in the browser
- [ ] Confirm `config.yaml` is not tracked by git: `git status`

## Platform refresh schedule

| Platform | What expires | Action |
|---|---|---|
| Instagram | Session cookie (30–90 days) | Re-copy from browser DevTools |
| Snapchat | Session cookie (varies) | Re-copy from map.snapchat.com |
| TikTok | msToken (hours) | Re-copy from browser cookies |
| Twitter/X | Credits (monthly) | Check developer.twitter.com usage |
