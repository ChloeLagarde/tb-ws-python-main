import re
import pexpect
import sys
import time  # Importation pour mesurer le temps
import subprocess
import os
from scripts.FindDNS import find_dns
from scripts.Version_Alcatel_Telco_One_Access import version_alcatel_telco_one_access


class Geco7x50:
    def __init__(self, ip_address, username='isadmin', password='p2mal&', timeout=120):
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.timeout = timeout
        self.logged_in = False  
        self.shell = None  
        self.log = []  # Liste pour stocker les messages de log

    def log_message(self, message):
        """Ajoute un message au log avec un timestamp et l'affiche."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log.append(log_entry)
        print(log_entry)

        
    def login(self):
        """Établit une connexion SSH et retourne un message de succès ou d'échec."""
        command = f'ssh -F ssh_config {self.username}@{self.ip_address}'
        self.log_message(f"Tentative de connexion à {self.ip_address}...")

        start_time = time.time()
        try:
            self.shell = pexpect.spawn(command, timeout=self.timeout, maxread=4000)
            
            while True:
                index = self.shell.expect([
                    'password:',
                    'Are you sure you want to continue connecting',
                    'Could not create directory',
                    'Failed to add the host',
                    pexpect.TIMEOUT,
                    pexpect.EOF
                ], timeout=self.timeout)
                
                if index == 0:  # Demande du mot de passe
                    self.shell.sendline(self.password)
                    self.shell.expect('>')
                    self.logged_in = True
                    elapsed_time = time.time() - start_time
                    self.log_message("CONNEXION établie")
                    self.log_message(f"Temps de connexion : {elapsed_time:.2f} secondes")
                    return "CONNEXION établie"
                
                elif index == 1:  # Confirmation de l'empreinte du serveur
                    self.shell.sendline("yes")
                
                elif index == 2:  # Impossible de créer le répertoire .ssh
                    self.log_message("Avertissement : Impossible de créer le répertoire .ssh")
                
                elif index == 3:  # Impossible d'ajouter l'hôte aux known_hosts
                    self.log_message("Avertissement : Impossible d'ajouter l'hôte aux known_hosts")
                
                elif index == 4:  # Timeout
                    elapsed_time = time.time() - start_time
                    self.log_message(f"Timeout atteint lors de la connexion à {self.ip_address}.")
                    self.log_message(f"Temps de tentative de connexion : {elapsed_time:.2f} secondes")
                    return "Erreur : timeout atteint lors de la connexion."
                
                elif index == 5:  # EOF -> Résolution DNS échouée ou autre problème
                    elapsed_time = time.time() - start_time
                    self.log_message(f"Erreur : Connexion impossible à {self.ip_address} - Résolution DNS échouée ou connexion interrompue.")
                    self.log_message(f"Temps de tentative de connexion : {elapsed_time:.2f} secondes")
                    return f"Erreur : Résolution DNS échouée ou connexion interrompue pour {self.ip_address}."
        
        except pexpect.ExceptionPexpect as e:
            elapsed_time = time.time() - start_time
            self.log_message(f"Erreur de connexion : {e}")
            self.log_message(f"Temps de connexion avant l'erreur : {elapsed_time:.2f} secondes")
            return f"Erreur de connexion : {e}"


    def login_OLT(self, username, password, typing):
        ssh = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no -F /app/ssh_config {username}@{self.ip_address}')
        start_time = time.time()
        try:
            ssh.expect([pexpect.TIMEOUT, 'password:', 'Are you sure you want to continue connecting?', 'Permission denied', typing], timeout=30)
            ssh.sendline(password)
            ssh.expect(typing, timeout=30)
            ssh.logged_in = True
            elapsed_time = time.time() - start_time
            self.log_message("CONNEXION établie")
            self.log_message(f"Temps de connexion : {elapsed_time:.2f} secondes")
            return "CONNEXION établie"
        except pexpect.TIMEOUT:
            elapsed_time = time.time() - start_time
            self.log_message(f"Timeout atteint lors de la connexion à {self.ip_address}.")
            self.log_message(f"Temps de tentative de connexion : {elapsed_time:.2f} secondes")
            return "Erreur : timeout atteint lors de la connexion."
        except pexpect.exceptions.EOF as eof_exception:
            elapsed_time = time.time() - start_time
            self.log_message(f"Erreur : Connexion impossible à {self.ip_address} - Résolution DNS échouée.")
            self.log_message(f"Temps de tentative de connexion : {elapsed_time:.2f} secondes")
            return f"Erreur : Résolution DNS échouée pour {self.ip_address}."
        except pexpect.ExceptionPexpect as e:
            elapsed_time = time.time() - start_time
            self.log_message(f"Erreur de connexion : {e}")
            self.log_message(f"Temps de connexion avant l'erreur : {elapsed_time:.2f} secondes")
            return f"Erreur de connexion : {e}"

    def execute_command(self, command):
        """Exécute une commande SSH et retourne les résultats."""
        if not self.logged_in:
            return None

        self.log_message(f"Exécution de la commande : {command}")
        start_time = time.time()
        try:
            self.shell.sendline(command)
            self.shell.expect('>')
            elapsed_time = time.time() - start_time
            output = self.shell.before.decode('utf-8')
            self.log_message(f"Commande exécutée en : {elapsed_time:.2f} secondes")
            print(output)
            return output
        except pexpect.ExceptionPexpect as e:
            self.log_message(f"Erreur lors de l'exécution de la commande : {e}")
            return None

    def configure_ethernet(self, port):
        """Configure les paramètres Ethernet d'un port."""
        if not self.logged_in:
            return None

        commands = [
            f'configure ethernet line {port}',
            'info detail',
            'logout'
        ]
        for cmd in commands:
            output = self.execute_command(cmd)
            if output is None:
                self.log_message(f"Erreur lors de l'exécution de la commande : {cmd}")
                return None

        output_logout = [line.decode('utf-8') for line in self.shell.readlines()]
        self.shell.expect(pexpect.EOF)
        return ''.join(output_logout)


def process_data(data_str):
    if data_str is None:
        return {}

    results = {}
    lines = data_str.splitlines()
    for line in lines:
        if not line.strip() or "=================" in line:
            continue
        
        if line.startswith("#") or line.startswith("Position"):
            key = line.split(":")[0].strip()
            value = line.split(":")[1].strip() if ":" in line else None
            results[key] = value
            continue

        multi_pattern = r'([^:]+?):\s*([^\s]+)\s+([^:]+?)\s*:\s*([^\s]+)'
        multi_match = re.match(multi_pattern, line.strip())
        if multi_match:
            key1 = multi_match.group(1).strip()
            value1 = multi_match.group(2).strip()
            key2 = multi_match.group(3).strip()
            value2 = multi_match.group(4).strip()
            results[key1] = value1
            results[key2] = value2
            continue
        
        pattern = r'([^:]+):\s*(".*?"|\{.*?\}|[^\s].*)'
        match = re.match(pattern, line.strip())
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            cleaned_value = value.strip('"').replace("\\", "")
            results[key] = cleaned_value

    return results

def extract_ethernet_details(output):
    """Extrait les détails de configuration Ethernet."""
    if not isinstance(output, str):
        return None

    parts = re.split(r'exit', output, maxsplit=1)
    if len(parts) > 1:
        details = parts[0].strip() + '\n' + parts[1].strip()
        details = re.sub(r'#-+|\bexit\b|configure ethernet|echo "ethernet"|mau 1|^\s*$', '', details, flags=re.MULTILINE)
        lines = details.splitlines()
        return lines[2:-4]
    return None

def process_ethernet(lines):
    """Traite les lignes de détails de configuration Ethernet."""
    if lines is None:
        return {}

    return_data = {}
    for line in lines:
        cleaned_line = ' '.join(line.rstrip().split()).replace("'", '')
        if 'speed-auto-sense' in cleaned_line:
            return_data["sense"] = "speed-auto-sense"
        match_type = re.match(r'type\s+(.*)', cleaned_line)
        if match_type:
            return_data["type_ethernet_line"] = match_type.group(1)
        if 'no autonegotiate' in cleaned_line:
            return_data["nego"] = "no autonegotiate"
        elif 'autonegotiate' in cleaned_line:
            return_data["nego"] = "autonegotiate"
    return return_data


def connect_ssh(equipement_dns, slot, port, verbose):
    """Établit une connexion SSH et exécute des commandes en capturant les sorties console."""
    Data = []
    ip, timestamp = equipement_dns.split(maxsplit=1)
    alu_obj = Geco7x50(ip)

    # Connexion SSH et capture des sorties console
    login_output_verbose = alu_obj.login() if verbose else None
    login_output = alu_obj.login()


    commands = [
        f'show equipment diagnostics sfp lt:{slot}:sfp:{port} detail',
        f'show interface port ethernet-line:{slot}/{port} detail',
        f'show equipment transceiver-inventory lt:{slot}:sfp:{port} detail',
        f'show equipment diagnostics sfp-threshold lt:{slot}:sfp:{port} detail'
    ]

    for cmd in commands:
        data = alu_obj.execute_command(cmd)
        processed = process_data(data)
        print(f"Résultat de la commande '{cmd}': {processed}")
        Data.append(processed)

    ethernet_result = alu_obj.configure_ethernet(f"{slot}/{port}")
    ethernet_details = extract_ethernet_details(ethernet_result)
    results = process_ethernet(ethernet_details)
    print("Résultat de la configuration Ethernet:", results)
    Data.append(results)
    
    return {
        "Data": Data,
        "equipement_dns": equipement_dns,
        "slot": slot,
        "port": port,
        "verbose": verbose,
        "login_output_verbose": login_output_verbose,
        "login_output": login_output
    }

def connect_ssh_olt(equipement_dns, commands):
    Data = {}
    logs = []

    # Récupération des informations de l'équipement
    equipement = find_dns(equipement_dns)
    equipement_type = version_alcatel_telco_one_access(equipement)

    # Définition du login et mot de passe selon le type d'équipement
    if equipement_type['equipment type'] == '7360' and not re.match(r'enu\.axione\.fr', equipement):
        username, password = 'isadmin', 'p2mal&'
    elif equipement_type['equipment type'] == 'EKINOPS':
        username, password = 'administrator', 'administrator'
    else:
        username, password = 'provauto', 'srv-pia64-l'

    # Définition du prompt de commande attendu selon le type d'équipement
    if equipement_type['equipment type'] == '7360':
        typing = '>#'
    elif equipement_type['equipment type'] == 'ADVA':
        typing = '-->'
    else:
        typing = r'>'

    # Connexion SSH via la fonction login_OLT avec username et password
    Olt = Geco7x50(equipement_dns)
    connection_message = Olt.login_OLT(username, password, typing)

    if "KO" in connection_message:
        logs.append("Erreur de connexion : " + connection_message)
        return {"data": None, "log": logs}
    else:
        logs.append(f"Connexion réussie à {equipement_dns}")

    # Exécution des commandes et collecte des résultats
    for cmd in commands:
        data = Olt.execute_command(cmd)
        Data[cmd] = data if data else None
        logs.append(f"Commande exécutée : {cmd}")

        # Ajoute les logs après chaque commande
        logs.extend(Olt.log)

    # Retourne les données collectées et le log complet
    return {"data": Data, "log": logs}
