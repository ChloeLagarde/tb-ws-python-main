import socket

def get_ip(dns):
    try:
        ip = socket.gethostbyname(dns)
        
    except socket.gaierror:
        print(f"Aucune adresse IP trouvée pour {dns}") 
    return ip  