#!/bin/bash
# ============================================================
# setup_vm1.sh - Configura a VM1 como Roteador NAT + Servidor DHCP
# Rede A (externa) : enp0s3  -> NAT do VirtualBox
# Rede B (interna) : enp0s8  -> 192.168.10.1/24
# ============================================================
set -e

IF_EXTERNA="enp0s3"
IF_INTERNA="enp0s8"
IP_INTERNO="192.168.10.1"

echo "==> [1/5] Configurando IP estatico na interface da Rede B ($IF_INTERNA)"
sudo tee /etc/netplan/99-projeto-redes.yaml > /dev/null <<EOF
network:
  version: 2
  ethernets:
    $IF_EXTERNA:
      dhcp4: true
    $IF_INTERNA:
      dhcp4: false
      addresses:
        - $IP_INTERNO/24
EOF
sudo chmod 600 /etc/netplan/99-projeto-redes.yaml
sudo netplan apply

echo "==> [2/5] Habilitando encaminhamento de pacotes (roteamento)"
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-roteador.conf > /dev/null
sudo sysctl -p /etc/sysctl.d/99-roteador.conf

echo "==> [3/5] Instalando pacotes"
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables iptables-persistent isc-dhcp-server

echo "==> [4/5] Configurando NAT com iptables"
sudo iptables -t nat -C POSTROUTING -o $IF_EXTERNA -j MASQUERADE 2>/dev/null || \
  sudo iptables -t nat -A POSTROUTING -o $IF_EXTERNA -j MASQUERADE
sudo iptables -C FORWARD -i $IF_EXTERNA -o $IF_INTERNA -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
  sudo iptables -A FORWARD -i $IF_EXTERNA -o $IF_INTERNA -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -C FORWARD -i $IF_INTERNA -o $IF_EXTERNA -j ACCEPT 2>/dev/null || \
  sudo iptables -A FORWARD -i $IF_INTERNA -o $IF_EXTERNA -j ACCEPT
sudo netfilter-persistent save

echo "==> [5/5] Configurando servidor DHCP"
sudo sed -i "s/^INTERFACESv4=.*/INTERFACESv4=\"$IF_INTERNA\"/" /etc/default/isc-dhcp-server
sudo tee /etc/dhcp/dhcpd.conf > /dev/null <<'EOF'
default-lease-time 600;
max-lease-time 7200;
authoritative;

subnet 192.168.10.0 netmask 255.255.255.0 {
  range 192.168.10.100 192.168.10.200;
  option routers 192.168.10.1;
  option domain-name-servers 8.8.8.8, 1.1.1.1;
  option subnet-mask 255.255.255.0;
  option broadcast-address 192.168.10.255;
}
EOF
sudo systemctl restart isc-dhcp-server
sudo systemctl enable isc-dhcp-server

echo
echo "============ VERIFICACAO ============"
echo "-- IP da Rede B:"
ip -4 addr show $IF_INTERNA | grep inet
echo "-- ip_forward (esperado: 1):"
cat /proc/sys/net/ipv4/ip_forward
echo "-- Regra NAT:"
sudo iptables -t nat -L POSTROUTING -n -v | grep MASQUERADE
echo "-- Servico DHCP:"
systemctl is-active isc-dhcp-server
echo "====================================="
echo "VM1 configurada. Agora inicie VM2 e VM3 e verifique com 'ip a'."
