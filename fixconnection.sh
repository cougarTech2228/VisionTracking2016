ip link set enp0s22f2u1 up
ip addr add 192.168.7.1 dev enp0s22f2u1
ip route add 192.168.7.0/24 via 0.0.0.0 dev enp0s22f2u1

ip link set enp0s22f2u4 up
ip addr add 172.22.11.1 dev enp0s22f2u4
ip route add 172.22.11.0/24 via 0.0.0.0 dev enp0s22f2u4


