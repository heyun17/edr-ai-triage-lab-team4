#!/usr/bin/env bash
set -euo pipefail

MY_IP="${1:?Usage: bootstrap.sh YOUR_PUBLIC_IP}"

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from "$MY_IP" to any port 6443 proto tcp

# Local k3s pod and service traffic.
sudo ufw allow from 10.42.0.0/16 to any
sudo ufw allow from 10.43.0.0/16 to any

printf 'vm.max_map_count=262144\n' | sudo tee /etc/sysctl.d/99-edr.conf
sudo sysctl --system >/dev/null
sudo swapoff -a
sudo ufw --force enable
sudo ufw status
