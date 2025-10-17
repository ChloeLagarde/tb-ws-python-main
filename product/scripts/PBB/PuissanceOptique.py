import re
import time
from typing import Dict, List, Optional
from scripts.SSH import ssh_pbb_cisco, close_ssh_pbb_cisco

# Connexions SSH globales réutilisables
ssh_connections = {}

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
        # Utiliser la connexion centralisée du cache ou créer une nouvelle
        connection_key = f"{intermediate_host}_{final_host}"
        
        if connection_key in ssh_connections and ssh_connections[connection_key]['session'].isalive():
            session = ssh_connections[connection_key]['session']
        else:
            # Créer une nouvelle connexion via SSH.py
            conn_result = ssh_pbb_cisco(final_host, intermediate_host)
            session = conn_result['session']
            ssh_connections[connection_key] = {'session': session}

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
                    index = session.expect([prompt_pattern, '--More--', 'Press any key to continue', 'pexpect.TIMEOUT'], timeout=10)
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

                # Parsing des résultats
                result = default_result.copy()
                
                # === FORMAT 1: Tableau avec lanes (comme pbb-man72-01) ===
                lane_match = re.search(r'Lane\s+Laser Bias\s+TX Power\s+RX Power.*?\n(.*?)(?=\n\s*Temperature|\n\s*$|\Z)', output, re.DOTALL)
                if lane_match:
                    lanes_data = lane_match.group(1)
                    tx_powers = []
                    rx_powers = []
                    
                    for line in lanes_data.strip().split('\n'):
                        if re.match(r'\s*\d+\s+', line):  # Ligne commençant par un numéro de lane
                            parts = line.split()
                            if len(parts) >= 4:
                                lane_num = parts[0]
                                tx_power = parts[2].replace('dBm', '').strip()
                                rx_power = parts[3].replace('dBm', '').strip()
                                
                                try:
                                    tx_powers.append(f"Lane {lane_num}: {tx_power} dBm")
                                    rx_powers.append(f"Lane {lane_num}: {rx_power} dBm")
                                except:
                                    continue
                    
                    if tx_powers and rx_powers:
                        result['tx'] = "[" + ", ".join(tx_powers) + "]"
                        result['rx'] = "[" + ", ".join(rx_powers) + "]"
                else:
                    # === FORMAT 2: Lignes individuelles (comme pbb-th275-01) ===
                    rx_match = re.search(r'RX Power\s*=\s*(-?\d+\.\d+)\s*dBm', output)
                    if rx_match:
                        result['rx'] = f"{rx_match.group(1)} dBm"
                    
                    tx_match = re.search(r'(?:Actual\s+)?TX Power\s*=\s*(-?\d+\.\d+)\s*dBm', output)
                    if tx_match:
                        result['tx'] = f"{tx_match.group(1)} dBm"

                # === Autres informations communes aux deux formats ===
                pid_match = re.search(r'PID\s*:\s*([^\n]+)', output)
                if pid_match:
                    result['pid'] = pid_match.group(1).strip()
                    
                optics_type_match = re.search(r'Optics type\s*:\s*([^\n]+)', output)
                if optics_type_match:
                    result['optics_type'] = optics_type_match.group(1).strip()
                    
                name_match = re.search(r'Name\s*:\s*([^\n]+)', output)
                if name_match:
                    result['name'] = name_match.group(1).strip()
                    
                fec_match = re.search(r'FEC State:\s*([^\n]+)', output)
                if fec_match:
                    result['fec_state'] = fec_match.group(1).strip()
                    
                wavelength_match = re.search(r'Wavelength\s*=\s*([^\n]+)', output)
                if wavelength_match:
                    result['wavelength'] = wavelength_match.group(1).strip()
                    
                alarm_match = re.search(r'Detected Alarms:\s*([^\n]+)', output)
                if alarm_match:
                    result['alarm_status'] = alarm_match.group(1).strip()
                    
                led_state_match = re.search(r'LED State:\s*([^\n]+)', output)
                if led_state_match:
                    result['led_state'] = led_state_match.group(1).strip()
                    
                laser_state_match = re.search(r'Laser State:\s*([^\n]+)', output)
                if laser_state_match:
                    result['laser_state'] = laser_state_match.group(1).strip()
                    
                part_number_match = re.search(r'Part Number\s*:\s*([^\n]+)', output)
                if part_number_match:
                    result['part_number'] = part_number_match.group(1).strip()
                
                # Thresholds
                rx_threshold_match = re.search(r'Rx Power Threshold\(dBm\)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', output)
                if rx_threshold_match:
                    result['rx_threshold_high'] = rx_threshold_match.group(1).strip()
                    result['rx_threshold_low'] = rx_threshold_match.group(2).strip()
                    
                tx_threshold_match = re.search(r'Tx Power Threshold\(dBm\)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', output)
                if tx_threshold_match:
                    result['tx_threshold_high'] = tx_threshold_match.group(1).strip()
                    result['tx_threshold_low'] = tx_threshold_match.group(2).strip()
                
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


def get_bundle_info(final_host: str, intermediate_host: str) -> Dict[str, Dict]:
    """
    Récupère les informations des bundles via la commande 'show bundle'.
    Retourne un dictionnaire {bundle_name: bundle_data}
    """
    results = {}
    
    try:
        # Utiliser la connexion centralisée
        connection_key = f"{intermediate_host}_{final_host}"
        
        if connection_key in ssh_connections and ssh_connections[connection_key]['session'].isalive():
            session = ssh_connections[connection_key]['session']
        else:
            # Créer une nouvelle connexion via SSH.py
            conn_result = ssh_pbb_cisco(final_host, intermediate_host)
            session = conn_result['session']
            ssh_connections[connection_key] = {'session': session}

        # Exécution de la commande show bundle
        bundle_command = 'show bundle'
        session.sendline(bundle_command)
        
        prompt_pattern = r'RP/0/RP0/CPU0:.*#'
        output = ""
        
        # Collecte de la sortie complète
        start_time = time.time()
        while True:
            index = session.expect([prompt_pattern, '--More--', 'Press any key to continue', 'pexpect.TIMEOUT'], timeout=15)
            output += session.before.decode('utf-8', errors='replace')
            
            if index == 0:
                break
            elif index in [1, 2]:
                session.send(' ')
            elif index == 3:
                break
            
            # Protection contre les boucles infinies
            if time.time() - start_time > 30:
                break

        # Parsing de la sortie
        results = parse_bundle_output(output)
        
    except Exception as e:
        results = {}
    
    return results


def parse_bundle_output(output: str) -> Dict[str, Dict]:
    """Parse la sortie de la commande 'show bundle' et extrait les informations."""
    results = {}
    
    # Division de la sortie par bundles
    bundle_blocks = re.split(r'\n(?=Bundle-Ether\d+)', output)
    
    for block in bundle_blocks:
        if not block.strip() or 'Bundle-Ether' not in block:
            continue
            
        bundle_info = parse_single_bundle(block)
        if bundle_info:
            bundle_name = bundle_info['name']
            results[bundle_name] = bundle_info
    
    return results


def parse_single_bundle(block: str) -> Optional[Dict]:
    """Parse les informations d'un seul bundle."""
    lines = block.strip().split('\n')
    if not lines:
        return None
    
    # Extraction du nom du bundle
    bundle_match = re.match(r'(Bundle-Ether\d+)', lines[0])
    if not bundle_match:
        return None
    
    bundle_name = bundle_match.group(1)
    
    # Initialisation des données du bundle
    bundle_data = {
        'name': bundle_name,
        'status': 'N/A',
        'local_links_active': 'N/A',
        'local_links_standby': 'N/A',
        'local_links_configured': 'N/A',
        'local_bandwidth_effective': 'N/A',
        'local_bandwidth_available': 'N/A',
        'mac_address': 'N/A',
        'lacp_status': 'N/A',
        'bfd_ipv4_state': 'N/A',
        'ports': []
    }
    
    # Parsing des informations principales
    for line in lines:
        line = line.strip()
        
        status_match = re.search(r'Status:\s+(.+)', line)
        if status_match:
            bundle_data['status'] = status_match.group(1).strip()
        
        links_match = re.search(r'Local links <active/standby/configured>:\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', line)
        if links_match:
            bundle_data['local_links_active'] = links_match.group(1)
            bundle_data['local_links_standby'] = links_match.group(2)
            bundle_data['local_links_configured'] = links_match.group(3)
        
        bandwidth_match = re.search(r'Local bandwidth <effective/available>:\s+(\d+)\s*\((\d+)\)\s*kbps', line)
        if bandwidth_match:
            bundle_data['local_bandwidth_effective'] = f"{bandwidth_match.group(1)} kbps"
            bundle_data['local_bandwidth_available'] = f"{bandwidth_match.group(2)} kbps"
        
        mac_match = re.search(r'MAC address \(source\):\s+([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4})', line)
        if mac_match:
            bundle_data['mac_address'] = mac_match.group(1)
        
        if 'LACP:' in line:
            lacp_match = re.search(r'LACP:\s+(.+)', line)
            if lacp_match:
                bundle_data['lacp_status'] = lacp_match.group(1).strip()
        
        if line.startswith('State:') and bundle_data['bfd_ipv4_state'] == 'N/A':
            state_match = re.search(r'State:\s+(.+)', line)
            if state_match:
                bundle_data['bfd_ipv4_state'] = state_match.group(1).strip()
    
    # Parsing des ports
    bundle_data['ports'] = parse_bundle_ports(block)
    
    return bundle_data


def parse_bundle_ports(block: str) -> List[Dict[str, str]]:
    """Parse les informations des ports d'un bundle."""
    ports = []
    lines = block.split('\n')
    
    port_section_started = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if '--------------------' in line and 'Port' in lines[i-1] if i > 0 else False:
            port_section_started = True
            continue
        
        if port_section_started:
            if not line or line.startswith('Bundle-Ether') or 'IPv4 BFD:' in line:
                break
            
            if line.startswith('Link is') or line.startswith('LACP') or '--' in line:
                continue
            
            port_match = re.match(r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', line)
            if port_match:
                port_info = {
                    'port': port_match.group(1),
                    'device': port_match.group(2),
                    'state': port_match.group(3),
                    'port_id': port_match.group(4),
                    'bandwidth': port_match.group(5)
                }
                ports.append(port_info)
    
    return ports


def format_bundle_summary(bundle_data: Dict[str, Dict]) -> str:
    """Formate un résumé des informations des bundles."""
    if not bundle_data:
        return "Aucune information de bundle trouvée."
    
    summary = "=== INFORMATIONS DES BUNDLES ===\n\n"
    
    for bundle_name, info in bundle_data.items():
        summary += f"Bundle: {bundle_name}\n"
        summary += f"  Status: {info['status']}\n"
        summary += f"  Links actifs/standby/configurés: {info['local_links_active']}/{info['local_links_standby']}/{info['local_links_configured']}\n"
        summary += f"  Bande passante: {info['local_bandwidth_effective']} (disponible: {info['local_bandwidth_available']})\n"
        summary += f"  LACP: {info['lacp_status']}\n"
        summary += f"  BFD IPv4: {info['bfd_ipv4_state']}\n"
        
        if info['ports']:
            summary += "  Ports:\n"
            for port in info['ports']:
                summary += f"    - {port['port']}: {port['state']} ({port['bandwidth']} kbps)\n"
        else:
            summary += "  Aucun port configuré\n"
        
        summary += "\n"
    
    return summary


def close_connection(hostname: str) -> None:
    """Ferme une connexion SSH spécifique"""
    # Chercher dans le cache de connexions
    keys_to_remove = [key for key in ssh_connections.keys() if hostname in key]
    
    for key in keys_to_remove:
        if ssh_connections[key]['session'].isalive():
            try:
                close_ssh_pbb_cisco(ssh_connections[key]['session'])
                del ssh_connections[key]
            except Exception:
                pass


def close_all_connections() -> None:
    """Ferme toutes les connexions SSH"""
    keys = list(ssh_connections.keys())
    for key in keys:
        try:
            close_ssh_pbb_cisco(ssh_connections[key]['session'])
        except Exception:
            pass
    
    ssh_connections.clear()