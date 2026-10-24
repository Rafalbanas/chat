#!/usr/bin/env bash
# Read-only audit. No env files, private keys, prompts or service logs are read.
set -euo pipefail
target=${1:-mikrus}
if [[ "$target" == -* ]]; then
  echo 'Podaj alias SSH lub użytkownik@host, bez opcji SSH.' >&2
  exit 2
fi
ssh -T -o BatchMode=yes -o ConnectTimeout=12 "$target" 'bash -s' <<'REMOTE'
set -u
section() { printf '\n### %s\n' "$1"; }
section 'Host i zasoby'
date -u +'%Y-%m-%dT%H:%M:%SZ'
hostname
id
uname -srmo
uptime
free -m
df -h / /var /opt 2>/dev/null
section 'Porty TCP'
ss -lntp 2>/dev/null || ss -lnt
section 'Usługi: wyłącznie nazwy i stany'
systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null || true
systemctl list-unit-files --no-pager --no-legend 2>/dev/null | awk '$1 ~ /caddy|nginx|ollama|ssh|autossh|tunnel|tailor/ {print}' || true
section 'Docker: wersje i metadane bez środowiska'
if command -v docker >/dev/null; then
  docker version --format '{{.Server.Version}}' 2>/dev/null || true
  docker compose version 2>/dev/null || true
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}' 2>/dev/null || true
  docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' 2>/dev/null || true
fi
section 'Pliki konfiguracji proxy: wyłącznie ścieżki'
for d in /etc/caddy /etc/nginx/sites-enabled /etc/nginx/conf.d; do
  if [ -d "$d" ]; then find "$d" -maxdepth 2 -type f -o -type l; fi
done
section 'Reguły SSH: wyłącznie forwarding'
if command -v sshd >/dev/null; then
  sshd -T 2>/dev/null | awk '$1 ~ /^(allowtcpforwarding|gatewayports|permitlisten|permitopen|passwordauthentication|permitrootlogin)$/ {print}' || true
fi
section 'DNS i HTTPS'
getent ahostsv4 banas.dev || true
getent ahostsv4 chat.banas.dev || true
for url in https://banas.dev https://chat.banas.dev; do
  curl --max-time 15 -sS -o /dev/null -w "$url HTTP=%{http_code} TLS=%{ssl_verify_result}\n" "$url" || true
done
section 'Ollama lokalna: wyłącznie wersja, modele i zajętość'
for endpoint in version tags ps; do
  printf '\n/api/%s\n' "$endpoint"
  curl --max-time 3 -fsS "http://127.0.0.1:11434/api/$endpoint" || true
done
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader || true
fi
REMOTE
