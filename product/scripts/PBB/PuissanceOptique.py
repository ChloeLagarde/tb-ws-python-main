import re
import pexpect
from typing import Dict, List, Optional
import time
from datetime import datetime

# Connexions SSH globales réutilisables
ssh_connections = {}
final_connections = {}

def get_optical_power_batch(final_host: str, ports: List[str], intermediate_host: str) -> Dict[str, Dict[str, str]]:
    """
    Récupère les puissances optiques pour plusieurs ports en une seule connexion SSH.
    Retourne un dictionnaire {port: optical_data}
    """
    results = {}
    
    # Valeurs par défaut
    default_result = {
        'rx': 'N/A', 
        'tx': 'N/A',
        'pid': 'N/A',
        'optics_type': 'N/A',
        'name': 'N/A',
        'fec_state': 'N/A',
        'wavelength': 'N/A',
        'alarm_status': 'N/A',
        'rx_threshold_high': 'N/A',
        'rx_threshold_low': 'N/A',
        'tx_threshold_high': 'N/A',
        'tx_threshold_low': 'N/A',
        'led_state': 'N/A',      
        'laser_state': 'N/A',    
        'part_number': 'N/A'     
    }
    
    try:
        intermediate_user = 'cag'
        intermediate_password = 'SpaciumAevum043?'
        final_user = 'provauto'
        final_password = 'srv-pia64-l'

        # Réutilisation de la connexion intermédiaire
        if intermediate_host in ssh_connections and ssh_connections[intermediate_host]['session'].isalive():
            session = ssh_connections[intermediate_host]['session']
        else:
            session = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {intermediate_user}@{intermediate_host}', timeout=30)
            i = session.expect(['password:', pexpect.TIMEOUT], timeout=30)
            if i == 1:
                raise Exception(f"Timeout en attendant le mot de passe pour {intermediate_host}")
            session.sendline(intermediate_password)
            
            prompt_patterns = [r'\$ ', r'# ', pexpect.TIMEOUT]
            if session.expect(prompt_patterns, timeout=30) == 2:
                raise Exception(f"Timeout en attendant le prompt sur {intermediate_host}")

            ssh_connections[intermediate_host] = {
                'session': session,
                'prompt_pattern': session.match.group(0) if session.match else r'\$ '
            }

        # Connexion à l'équipement final (réutilisable)
        connection_key = f"{intermediate_host}_{final_host}"
        
        if connection_key not in final_connections or not session.isalive():
            final_host_command = f'ssh -o StrictHostKeyChecking=no {final_user}@{final_host}'
            session.sendline(final_host_command)

            session.expect(r'\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*', timeout=60)
            session.send(' ')
            
            i = session.expect([r'Password:', r'password:', pexpect.TIMEOUT], timeout=60)
            if i == 2:
                raise Exception(f"Timeout en attendant le mot de passe pour {final_host}")
            session.sendline(final_password)

            prompt_patterns = [r'RP/0/RP0/CPU0:.*#', r'.*#', pexpect.TIMEOUT]
            if session.expect(prompt_patterns, timeout=30) == 2:
                raise Exception(f"Timeout en attendant le prompt Cisco sur {final_host}")
                
            final_connections[connection_key] = True

        # Traitement batch de tous les ports
        for i, port in enumerate(ports):
            try:
                # Commande pour récupérer les infos optiques
                optics_command = f'show controller optic {port}'
                session.sendline(optics_command)
                
                prompt_pattern = r'RP/0/RP0/CPU0:.*#'
                output = ""
                
                # Timeout réduit pour chaque commande
                start_time = time.time()
                while True:
                    index = session.expect([prompt_pattern, '--More--', 'Press any key to continue', pexpect.TIMEOUT], timeout=10)
                    output += session.before.decode('utf-8', errors='replace')
                    
                    if index == 0:
                        break
                    elif index in [1, 2]:
                        session.send(' ')
                    elif index == 3:
                        break
                    
                    # Protection contre les boucles infinies
                    if time.time() - start_time > 15:
                        break

                # Parsing des résultats avec gestion des deux formats
                result = parse_optical_data(output)
                results[port] = result
                
            except Exception as e:
                results[port] = default_result.copy()

    except Exception as e:
        # Retourner des valeurs par défaut pour tous les ports
        for port in ports:
            results[port] = default_result.copy()
    
    # Formater les résultats pour correspondre au format attendu
    formatted_results = {}
    for port, data in results.items():
        formatted_results[port] = {
            'signal_optique_rx': data['rx'],
            'signal_optique_tx': data['tx'],
            'type_sfp': {
                'PID': data['pid'],
                'Optics type': data['optics_type'],
                'Name': data['name'],
                'Part Number': data['part_number']
            },
            'fec_state': data['fec_state'],
            'wavelength': data['wavelength'],
            'alarm_status': data['alarm_status'],
            'led_state': data['led_state'],
            'laser_state': data['laser_state'],
            'threshold': {
                'rx_high': data['rx_threshold_high'],
                'rx_low': data['rx_threshold_low'],
                'tx_high': data['tx_threshold_high'],
                'tx_low': data['tx_threshold_low']
            }
        }
    
    return formatted_results

def parse_optical_data(output: str) -> Dict[str, str]:
    """
    Parse les données optiques avec support des deux formats Cisco :
    - Format avec lanes multiples
    - Format simple avec valeurs globales
    """
    result = {
        'rx': 'N/A', 
        'tx': 'N/A',
        'pid': 'N/A',
        'optics_type': 'N/A',
        'name': 'N/A',
        'fec_state': 'N/A',
        'wavelength': 'N/A',
        'alarm_status': 'N/A',
        'rx_threshold_high': 'N/A',
        'rx_threshold_low': 'N/A',
        'tx_threshold_high': 'N/A',
        'tx_threshold_low': 'N/A',
        'led_state': 'N/A',
        'laser_state': 'N/A',
        'part_number': 'N/A'
    }
    
    # 1. Chercher d'abord le format avec lanes multiples
    lane_data = parse_lane_data(output)
    if lane_data:
        # Format avec lanes - créer un tableau avec toutes les valeurs
        rx_values = []
        tx_values = []
        for lane_num, lane_info in lane_data.items():
            rx_values.append(f"Lane {lane_num}: {lane_info['rx']}")
            tx_values.append(f"Lane {lane_num}: {lane_info['tx']}")
        
        result['rx'] = "[" + ", ".join(rx_values) + "]"
        result['tx'] = "[" + ", ".join(tx_values) + "]"
    else:
        # 2. Format simple - valeurs globales
        rx_match = re.search(r'RX Power\s*=\s*(-?\d+\.\d+)\s*dBm', output)
        tx_match = re.search(r'Actual TX Power\s*=\s*(-?\d+\.\d+)\s*dBm', output)
        
        if rx_match:
            result['rx'] = f"{rx_match.group(1)} dBm"
        if tx_match:
            result['tx'] = f"{tx_match.group(1)} dBm"
    
    # Extraction des autres informations (communes aux deux formats)
    pid_match = re.search(r'PID\s*:\s*([^\n\r]+)', output)
    if pid_match:
        result['pid'] = pid_match.group(1).strip()
    
    optics_type_match = re.search(r'Optics type\s*:\s*([^\n\r]+)', output)
    if optics_type_match:
        result['optics_type'] = optics_type_match.group(1).strip()
    
    name_match = re.search(r'Name\s*:\s*([^\n\r]+)', output)
    if name_match:
        result['name'] = name_match.group(1).strip()
    
    fec_match = re.search(r'FEC State:\s*([^\n\r]+)', output)
    if fec_match:
        result['fec_state'] = fec_match.group(1).strip()
    
    wavelength_match = re.search(r'Wavelength\s*=\s*([^\n\r]+)', output)
    if wavelength_match:
        result['wavelength'] = wavelength_match.group(1).strip()
    
    alarm_match = re.search(r'Detected Alarms:\s*([^\n\r]+)', output)
    if alarm_match:
        result['alarm_status'] = alarm_match.group(1).strip()
    
    # Seuils de puissance
    rx_threshold_match = re.search(r'Rx Power Threshold\(dBm\)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', output)
    if rx_threshold_match:
        result['rx_threshold_high'] = rx_threshold_match.group(1).strip()
        result['rx_threshold_low'] = rx_threshold_match.group(2).strip()
    
    tx_threshold_match = re.search(r'Tx Power Threshold\(dBm\)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', output)
    if tx_threshold_match:
        result['tx_threshold_high'] = tx_threshold_match.group(1).strip()
        result['tx_threshold_low'] = tx_threshold_match.group(2).strip()
    
    led_state_match = re.search(r'LED State:\s*([^\n\r]+)', output)
    if led_state_match:
        result['led_state'] = led_state_match.group(1).strip()
    
    laser_state_match = re.search(r'Laser State:\s*([^\n\r]+)', output)
    if laser_state_match:
        result['laser_state'] = laser_state_match.group(1).strip()
    
    part_number_match = re.search(r'Part Number\s*:\s*([^\n\r]+)', output)
    if part_number_match:
        result['part_number'] = part_number_match.group(1).strip()
    
    return result

def parse_lane_data(output: str) -> Optional[Dict[str, Dict[str, str]]]:
    """
    Parse les données des lanes si présentes dans le format tableau
    Retourne None si pas de lanes trouvées
    """
    # Chercher le tableau des lanes
    lane_section = re.search(
        r'Lane\s+Laser Bias\s+TX Power\s+RX Power\s+Output Frequency\s*\n\s*-+.*?\n((?:\s*\d+.*?\n)*)', 
        output, 
        re.MULTILINE | re.DOTALL
    )
    
    if not lane_section:
        return None
    
    lanes_text = lane_section.group(1)
    lanes_data = {}
    
    # Parser chaque ligne de lane
    for line in lanes_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Format: Lane_num   Laser_bias   TX_Power   RX_Power   Output_Freq
        lane_match = re.match(r'(\d+)\s+[\d.]+\s*mA\s+([\d.-]+)\s*dBm\s+([\d.-]+)\s*dBm\s+.*', line)
        if lane_match:
            lane_num = lane_match.group(1)
            tx_power = lane_match.group(2)
            rx_power = lane_match.group(3)
            
            lanes_data[lane_num] = {
                'tx': f"{tx_power} dBm",
                'rx': f"{rx_power} dBm"
            }
    
    return lanes_data if lanes_data else None

def get_optical_power(final_host: str, port: str, intermediate_host: str) -> Dict[str, str]:
    """Version compatible pour un seul port (rétrocompatibilité)"""
    results = get_optical_power_batch(final_host, [port], intermediate_host)
    if port in results:
        # Conversion au format attendu par l'ancienne API
        data = results[port]
        return {
            'rx': data['signal_optique_rx'],
            'tx': data['signal_optique_tx'],
            'pid': data['type_sfp']['PID'],
            'optics_type': data['type_sfp']['Optics type'],
            'name': data['type_sfp']['Name'],
            'part_number': data['type_sfp']['Part Number'],
            'fec_state': data['fec_state'],
            'wavelength': data['wavelength'],
            'alarm_status': data['alarm_status'],
            'rx_threshold_high': data['threshold']['rx_high'],
            'rx_threshold_low': data['threshold']['rx_low'],
            'tx_threshold_high': data['threshold']['tx_high'],
            'tx_threshold_low': data['threshold']['tx_low'],
            'led_state': data['led_state'],
            'laser_state': data['laser_state']
        }
    else:
        # Valeurs par défaut
        return {
            'rx': 'N/A',
            'tx': 'N/A',
            'pid': 'N/A',
            'optics_type': 'N/A',
            'name': 'N/A',
            'part_number': 'N/A',
            'fec_state': 'N/A',
            'wavelength': 'N/A',
            'alarm_status': 'N/A',
            'rx_threshold_high': 'N/A',
            'rx_threshold_low': 'N/A',
            'tx_threshold_high': 'N/A',
            'tx_threshold_low': 'N/A',
            'led_state': 'N/A',
            'laser_state': 'N/A'
        }

def close_connection(hostname: str) -> None:
    """Ferme une connexion SSH spécifique"""
    if hostname in ssh_connections and ssh_connections[hostname]['session'].isalive():
        try:
            session = ssh_connections[hostname]['session']
            session.sendline('exit')
            session.close()
            del ssh_connections[hostname]
        except Exception as e:
            print(f"Erreur lors de la fermeture de la connexion SSH pour {hostname}: {str(e)}")

def close_all_connections() -> None:
    """Ferme toutes les connexions SSH"""
    hosts = list(ssh_connections.keys())
    for hostname in hosts:
        close_connection(hostname)
    
    # Réinitialiser aussi les connexions finales
    global final_connections
    final_connections = {}