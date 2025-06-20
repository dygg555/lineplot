import socket
import time
import random

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

a = 0
b = 0
c = 0

while True:
    channel = 0
    a += 1
    if a > 100:
        a = 0
    
    b += 3
    if b > 30:
        b = 0

    c += 5
    if c > 200:
        c = 0
    values = [a, b,c,c-5]
    data = f"{channel}," + ",".join(map(str, values))
    print(data)
    sock.sendto(data.encode(), (UDP_IP, UDP_PORT))
    time.sleep(0.02)