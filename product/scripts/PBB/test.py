#!/usr/bin/env python3
"""
ClassPBBWeb.py - Version avec métrique unique
Utilise une seule requête Prometheus pour récupérer toutes les informations
"""

import json
import re
import socket
import subprocess
import concurrent.futures
import time
import requests
import urllib3
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Union

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===== FONCTIONS COPIÉES POUR ÉVITER LES IMPORTS =====

def find_dns(equipment):
    """Version simplifiée de FindDNS"""
    import subprocess
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def check_dns(equipment, dns):
        host = equipment + dns
        result = subprocess.run(["nslookup", host], capture_output=True, text=True)
        if 'NXDOMAIN' not in result.stdout:
            return host
        return None

    dns_list = ['.bcb.axione.fr', '.par.axione.fr', '.adn.axione.fr', '.cha.axione.fr', '.lim.axione.fr',
                '.qui.axione.fr', '.tou.axione.fr', '.loi.axione.fr', '.mel.axione.fr', '.mtr.axione.fr',
                '.nie.axione.fr', '.pau.axione.fr', '.hpy.axione.fr', '.sar.axione.fr', '.gon.axione.fr',
                '.vau.axione.fr', '.fin.axione.fr', '.jur.axione.fr', '.bou.axione.fr', '.gab.axione.fr',
                '.t42.axione.fr', '.t78.axione.fr', '.ais.axione.fr', '.bfo.axione.fr', '.npc.axione.fr',
                '.t72.axione.fr', '.odi.axione.fr', '.y78.axione.fr', '.lna.axione.fr', '.lab.axione.fr',
                '.adf.axione.fr', '.enn.axione.fr', '.eur.axione.fr', '.hsn.axione.fr', '.ctf.axione.fr',
                '.uki.axione.fr', '.lat.axione.fr', '.sqy.axione.fr', '.urw.axione.fr', '.enu.axione.fr']

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(check_dns, equipment, dns) for dns in dns_list]
        for future in as_completed(futures):
            result = future.result()
            if result:
                executor.shutdown(wait=False)
                return result

    return None

def snmp_request(host, oid):
    """Version simplifiée de SnmpRequests"""
    command = ['snmpwalk', '-c', 'cpdea', '-v', '2c', host, oid]
    try:
        response = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = response.communicate()
        return output
    except Exception as e:
        print(f"❌ Erreur SNMP: {e}")
        return b""

def get_pbb_monitoring_info(hostname):
    """Version simplifiée de SpectrumPBB"""
    try:
        dns = find_dns(hostname)
        if dns:
            return {
                "spectrum": f"DNS résolu: {dns}",
                "cacti": f"Hostname: {hostname}"
            }
        else:
            return {
                "spectrum": f"DNS non résolu pour {hostname}",
                "cacti": f"Hostname: {hostname}"
            }
    except Exception as e:
        return {
            "spectrum": f"Erreur: {str(e)}",
            "cacti": f"Erreur: {str(e)}"
        }

def get_optical_power_batch(host, ports, intermediate_host):
    """Version fallback pour les puissances optiques"""
    return {port: {
        'signal_optique_rx': 'N/A',
        'signal_optique_tx': 'N/A',
        'type_sfp': {
            'PID': 'N/A',
            'Optics type': 'N/A',
            'Name': 'N/A',
            'Part Number': 'N/A'
        },
        'fec_state': 'N/A',
        'wavelength': 'N/A',
        'alarm_status': 'N/A',
        'led_state': 'N/A',
        'laser_state': 'N/A',
        'threshold': {
            'rx_high': 'N/A',
            'rx_low': 'N/A',
            'tx_high': 'N/A',
            'tx_low': 'N/A'
        }
    } for port in ports}

def get_bundle_info(host, intermediate_host):
    """Version fallback pour les bundles"""
    return {}

def close_all_connections():
    """Version fallback"""
    pass

# ===== CLASSE PRINCIPALE =====



@dataclass
class SNMPResponse:
    oid: str
    value: str
    index: Optional[str] = None
    raw_output: str = ""

class NetworkEquipment:
    OIDS = {
        'name': '1.3.6.1.2.1.1.5',
        'type': '1.3.6.1.2.1.1.1',
        'interface_status': '1.3.6.1.2.1.2.2.1.8',
        'interface_admin_status': '1.3.6.1.2.1.2.2.1.7',
        'interface_desc': '1.3.6.1.2.1.2.2.1.2',
        'physical_port': '1.3.6.1.2.1.2.2.1.6',
        'port_alias': '1.3.6.1.2.1.31.1.1.1.18',
    }
    
    PROMETHEUS_BASE_URL = "http://promxy.query.consul:8082/api/v1/query"

    def __init__(self, hostname: str, ip: Optional[str] = None, slot: Optional[str] = None, 
                 community: Union[str, List[str]] = None, version: str = '2c', 
                 intermediate_host: Optional[str] = None, max_workers: int = 5):
        self.hostname = hostname
        self.ip = ip
        self.slot = slot  
        self.version = version
        self.dns_complet = find_dns(hostname)
        self.ip_address = socket.gethostbyname(self.dns_complet) if self.dns_complet else "DNS non résolu"
        self.intermediate_host = "vma-prddck-104.pau"
        self.max_workers = max_workers
        self._snmp_cache = {}
        self._fqdn = None
        
        # Session requests pour Prometheus
        self.session = requests.Session()
        self.session.verify = False

    def _get_fqdn_from_referentiel(self, hostname: str) -> Optional[str]:
        """Récupère le FQDN depuis le référentiel réseau Axione"""
        try:
            url = "https://toolbox.int.axione.fr/outilsreseaux/referentiel-reseau.html"
            
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            proxies = {
                'http': None,
                'https': None
            }
            
            print(f"🔍 Recherche de '{hostname}' dans le référentiel réseau...")
            
            response = self.session.get(url, headers=headers, proxies=proxies, timeout=10)
            response.raise_for_status()
            
            # Parser le HTML pour trouver le hostname
            # Le tableau contient des colonnes avec IP et Node
            lines = response.text.split('\n')
            
            for i, line in enumerate(lines):
                # Chercher le hostname dans la page (peut être dans différentes colonnes)
                if hostname.lower() in line.lower():
                    # Chercher la colonne "Node" qui contient le FQDN
                    # Pattern pour trouver un FQDN complet (ex: edg-hdf64-01.pau.axione.fr)
                    fqdn_pattern = r'([a-zA-Z0-9-]+\.(?:bcb|par|adn|cha|lim|qui|tou|loi|mel|mtr|nie|pau|hpy|sar|gon|vau|fin|jur|bou|gab|t42|t78|ais|bfo|npc|t72|odi|y78|lna|lab|adf|enn|eur|hsn|ctf|uki|lat|sqy|urw|enu)\.axione\.fr)'
                    
                    # Chercher dans la ligne courante et les lignes voisines
                    search_range = lines[max(0, i-2):min(len(lines), i+3)]
                    for search_line in search_range:
                        fqdn_match = re.search(fqdn_pattern, search_line)
                        if fqdn_match:
                            fqdn = fqdn_match.group(1)
                            print(f"✅ FQDN trouvé dans le référentiel: {fqdn}")
                            return fqdn
            
            print(f"⚠️  Hostname '{hostname}' non trouvé dans le référentiel")
            return None
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération depuis le référentiel: {e}")
            return None

    def _get_fqdn_from_snmp(self) -> Optional[str]:
        """Récupère le FQDN via SNMP (OID sysName)"""
        if self._fqdn:
            return self._fqdn
        
        # Prioriser le DNS complet trouvé par find_dns()
        if self.dns_complet:
            self._fqdn = self.dns_complet
            return self._fqdn
        
        # Essayer le référentiel réseau (pour Huawei notamment)
        fqdn_referentiel = self._get_fqdn_from_referentiel(self.hostname)
        if fqdn_referentiel:
            self._fqdn = fqdn_referentiel
            return self._fqdn
            
        hostname_to_use = self.hostname
        
        # Liste des OIDs à essayer (ordre de priorité)
        oids_to_try = [
            '1.3.6.1.2.1.1.5',      # sysName (standard)
            '1.3.6.1.4.1.2011.5.25.31.1.1.1.1.5',  # Huawei hostname
            '1.3.6.1.2.1.1.5.0',    # sysName.0 (avec .0 à la fin)
        ]
        
        for oid in oids_to_try:
            try:
                output = snmp_request(hostname_to_use, oid)
                if output and len(output) > 0:
                    result = output.decode('utf-8') if isinstance(output, bytes) else output
                    match = re.search(r'STRING:\s*"?([^"\n]+)"?', result)
                    if match:
                        fqdn_raw = match.group(1).strip()
                        fqdn_clean = fqdn_raw.split()[0] if ' ' in fqdn_raw else fqdn_raw
                        if fqdn_clean and fqdn_clean not in ["", "N/A", "Unknown"]:
                            self._fqdn = fqdn_clean
                            print(f"FQDN récupéré via SNMP (OID {oid}): {self._fqdn}")
                            return self._fqdn
            except Exception as e:
                continue
        
        print(f"Erreur: Impossible de récupérer le FQDN via SNMP")
        return None

    def _query_prometheus_unified(self, hostname: str, max_retries: int = 20) -> Optional[List[Dict]]:
        """Requête Prometheus unifiée avec retry"""
        query = f'ifMetrics_ifAdminStatus{{hostname=%22{hostname}%22}}'
        full_url = f"{self.PROMETHEUS_BASE_URL}?query={query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        proxies = {
            'http': None,
            'https': None
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(full_url, headers=headers, proxies=proxies, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('status') == 'success' and data.get('data', {}).get('result'):
                    return data['data']['result']
                else:
                    time.sleep(2)
                    
            except Exception:
                time.sleep(2)
        
        return None

    def _extract_bandwidth_from_ifname(self, ifname: str) -> str:
        """Détecte la bande passante multi-vendor"""
        # Cisco/PBB
        if "FourHundredGigE" in ifname or ifname.startswith("Fo"):
            return "400G"
        elif "HundredGigE" in ifname or ifname.startswith("Hu"):
            return "100G"
        elif "TenGigE" in ifname or ifname.startswith("Te"):
            return "10G"
        elif "GigabitEthernet" in ifname or ifname.startswith("Gi"):
            return "1G"
        elif "FastEthernet" in ifname or ifname.startswith("Fa"):
            return "100M"
        
        # Nokia
        elif ifname.startswith("1/1/c"):
            return "100G"
        elif ifname.startswith("1/1/x"):
            return "10G"
        
        # Huawei
        elif "XGigabitEthernet" in ifname or "XGE" in ifname:
            return "10G"
        elif "GE" in ifname and "XGE" not in ifname:
            return "1G"
        elif "40GE" in ifname:
            return "40G"
        elif "100GE" in ifname:
            return "100G"
        
        # Juniper
        elif "xe-" in ifname:
            return "10G"
        elif "et-" in ifname:
            return "100G"
        elif "ge-" in ifname:
            return "1G"
        
        return "Unknown"

    def _snmp_walk(self, oid: str) -> Optional[str]:
        """SNMP walk avec mise en cache"""
        if oid in self._snmp_cache:
            return self._snmp_cache[oid]
            
        hostname_to_use = self.dns_complet if self.dns_complet else self.hostname
        
        try:
            output = snmp_request(hostname_to_use, oid)
            if output and len(output) > 0:
                result = output.decode('utf-8') if isinstance(output, bytes) else output
                self._snmp_cache[oid] = result
                return result
        except Exception:
            pass
        
        return None

    def _parallel_snmp_walks(self, oids: List[str]) -> Dict[str, Optional[str]]:
        """Exécute plusieurs SNMP walks en parallèle"""
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(oids)) as executor:
            future_to_oid = {executor.submit(self._snmp_walk, oid): oid for oid in oids}
            for future in concurrent.futures.as_completed(future_to_oid):
                oid = future_to_oid[future]
                try:
                    results[oid] = future.result()
                except Exception:
                    results[oid] = None
        return results

    def _extract_port_number(self, description: str) -> Optional[str]:
        patterns = [
            r'(\d+/\d+/\d+/\d+/\d+)',  
            r'(\d+/\d+/\d+/\d+)',      
            r'[Pp]ort[:\s-]*(\d+/\d+/\d+/\d+/\d+)',  
            r'[Pp]ort[:\s-]*(\d+/\d+/\d+/\d+)',      
        ]
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
        return None

    def _clean_value(self, value: str) -> str:
        value = value.strip('"')
        for prefix in ['INTEGER: ', 'STRING: ', 'Hex-STRING: ', 'Hex-']:
            value = value.replace(prefix, '')
        return value.strip()

    def _parse_snmp_output_with_debug(self, output: str, oid_type: str) -> List[Dict]:
        if not output:
            return []
        
        responses = []
        
        for line in output.splitlines():
            patterns = [
                r'([\w-]+::[\w.]+)\.(\d+)\s+=\s+(.+)',
                r'([\w-]+::[\w.]+)(?:\[(\d+)\])?\s+=\s+(.+)',
                r'([\w-]+::[\w.]+)\s+=\s+(?:(?:index\s+)?(\d+):\s+)?(.+)'
            ]
            
            matched = False
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    matched = True
                    index = match.group(2)
                    value = self._clean_value(match.group(3))
                    responses.append({
                        'oid': match.group(1),
                        'index': index,
                        'value': value,
                        'raw_output': line
                    })
                    break
            
            if not matched:
                num_match = re.search(r'\.(\d+)\s+=', line)
                if num_match:
                    index = num_match.group(1)
                    value_match = re.search(r'=\s+(.+)$', line)
                    value = self._clean_value(value_match.group(1)) if value_match else "Unknown"
                    oid_match = re.search(r'^([\w-]+::[\w.]+)', line)
                    oid = oid_match.group(1) if oid_match else "Unknown"
                    
                    responses.append({
                        'oid': oid,
                        'index': index,
                        'value': value,
                        'raw_output': line
                    })
        
        return responses

    def _get_bandwidth(self, description: str, speed: Optional[str] = None) -> str:
        """Détermine la bande passante"""
        if speed:
            try:
                speed_mbps = int(speed)
                if speed_mbps >= 400000:
                    return "400G"
                elif speed_mbps >= 100000:
                    return "100G"
                elif speed_mbps >= 10000:
                    return "10G"
                elif speed_mbps >= 1000:
                    return "1G"
            except (ValueError, TypeError):
                pass
        
        return self._extract_bandwidth_from_ifname(description)

    def _parse_type_info(self, type_value: str) -> tuple:  
        type_value = type_value.strip('"')  
        parts = type_value.split(',', 1)  
        
        if len(parts) == 2:
            software_type = parts[0].strip()   
            version_full = parts[1].strip()  
            
            if "Version" in version_full:
                version_parts = version_full.split(" ")
                if len(version_parts) >= 2 and "Version" == version_parts[0]:
                    return software_type, version_parts[1]
            
            return software_type, version_full
        else:
            return type_value, ""  

    def _find_equipment_model(self, snmp_type_output: str) -> str:
        """Détermine le modèle d'équipement"""
        if "Cisco IOS XR Software (8000)" in snmp_type_output:
            hostname_lower = self.hostname.lower()
            if hostname_lower.startswith('abr'):
                return "Cisco 8201-24H8FH"
            else:
                return "Cisco 8201-32FH"
        
        for pattern_info in equipment_patterns:
            match = re.search(pattern_info["pattern"], snmp_type_output)
            if match:
                if pattern_info.get("model") and pattern_info["model"] != "Unknown" and pattern_info["model"] is not None:
                    return pattern_info["model"]
        
        for pattern_info in equipment_patterns:
            match = re.search(pattern_info["pattern"], snmp_type_output)
            if match and pattern_info.get("type"):
                return pattern_info["type"]
                
        return "Unknown"

    def get_bundle_info_equipment(self) -> Dict[str, Dict]:
        """Récupère les bundles"""
        try:
            bundle_info = get_bundle_info(self.dns_complet, self.intermediate_host)
            return bundle_info
        except Exception:
            return {}

    def _normalize_port_name(self, port_name: str, vendor: str = "Cisco") -> str:
        """Normalise le port selon le vendor"""
        if vendor not in ["Cisco", "Unknown"]:
            return port_name
        
        prefixes_to_remove = [
            'HundredGigE', 'Hu', 'FH',
            'TenGigE', 'Te',
            'GigabitEthernet', 'Gi',
            'FourHundredGigE', 'Fo',
            'FastEthernet', 'Fa'
        ]
        
        port_clean = port_name
        
        for prefix in prefixes_to_remove:
            if port_clean.startswith(prefix):
                port_clean = port_clean[len(prefix):]
                break
        
        if port_clean and not port_clean.startswith('0/0/0/'):
            port_clean = f"0/0/0/{port_clean}"
        
        return port_clean

    def _get_port_bundle_info(self, port_number: str, bundle_data: Dict[str, Dict]) -> Dict[str, str]:
        """Infos bundle pour un port"""
        bundle_info = {
            "bundle": "N/A",
            "status_bundle": "N/A", 
            "state": "N/A"
        }
        
        port_normalized = self._normalize_port_name(port_number)
        
        for bundle_name, data in bundle_data.items():
            for port in data.get('ports', []):
                port_name = port.get('port', '')
                port_name_normalized = self._normalize_port_name(port_name)
                
                if port_normalized == port_name_normalized:
                    bundle_info = {
                        "bundle": bundle_name,
                        "status_bundle": data.get('status', 'N/A').lower(),
                        "state": port.get('state', 'N/A')
                    }
                    break
                    
        return bundle_info

    def _get_default_optical_values(self) -> Dict:
        """Valeurs optiques par défaut"""
        return {
            "signal_optique_rx": "N/A",
            "signal_optique_tx": "N/A",
            "type_sfp": {
                "PID": "N/A",
                "Optics type": "N/A",
                "Name": "N/A",
                "Part Number": "N/A"
            },
            "fec_state": "N/A",
            "wavelength": "N/A",
            "alarm_status": "N/A",
            "led_state": "N/A",        
            "laser_state": "N/A",
            "threshold": {
                "rx_high": "N/A",
                "rx_low": "N/A",
                "tx_high": "N/A",
                "tx_low": "N/A"
            }
        }

    def get_optical_power_values_batch(self, ports: List[str]) -> Dict[str, Dict]:
        """Récupère les puissances optiques"""
        try:
            optical_data = get_optical_power_batch(self.dns_complet, ports, self.intermediate_host)
            return optical_data
        except Exception:
            return {port: self._get_default_optical_values() for port in ports}

    def get_optical_power_values(self) -> Dict[str, Union[str, Dict[str, str]]]:
        """Version un seul port"""
        try:
            optical_data = get_optical_power(self.dns_complet, self.port, self.intermediate_host)
            return {
                "signal_optique_rx": optical_data['rx'],
                "signal_optique_tx": optical_data['tx'],
                "type_sfp": {
                    "PID": optical_data['pid'],
                    "Optics type": optical_data['optics_type'],
                    "Name": optical_data['name'],
                    "Part Number": optical_data['part_number']  
                },
                "fec_state": optical_data['fec_state'],
                "wavelength": optical_data['wavelength'],
                "alarm_status": optical_data['alarm_status'],
                "led_state": optical_data['led_state'],        
                "laser_state": optical_data['laser_state'],    
                "threshold": {
                    "rx_high": optical_data['rx_threshold_high'],
                    "rx_low": optical_data['rx_threshold_low'],
                    "tx_high": optical_data['tx_threshold_high'],
                    "tx_low": optical_data['tx_threshold_low']
                }
            }
        except Exception:
            return self._get_default_optical_values()
        finally:
            close_all_connections()

    def _process_ports_via_prometheus(self, prometheus_results: List[Dict], 
                                      bundle_data: Dict[str, Dict], 
                                      target_port: Optional[str]) -> tuple:
        """Traite les ports depuis Prometheus"""
        ports_up = []
        ports_info_temp = []
        
        for result in prometheus_results:
            metric = result.get('metric', {})
            value_array = result.get('value', [])
            
            ifname = metric.get('ifName', '')
            ifalias = metric.get('ifAlias', '').strip('"')
            ifphysaddr = metric.get('ifPhysAddress', '')
            model = metric.get('model', 'Unknown')
            vendor = metric.get('vendor', 'Unknown')
            category = metric.get('category', 'Unknown')
            admin_status = value_array[1] if len(value_array) > 1 else '2'
            
            # Convertir admin_status en up/down
            status = "up" if admin_status == '1' else "down"
            
            # Filtre 1: Si "Optics" dans le nom du port → skip
            if 'optics' in ifname.lower():
                continue
            
            # Filtre 2: Si pas de description → skip (tous les ports sans description)
            if not ifalias or ifalias.strip() in ["", "N/A"]:
                continue
            
            # Filtre 3: Si c'est un Optics dans la description → skip
            if 'optics' in ifalias.lower():
                continue
            
            # Filtre 4: Pour PBB, vérifier 0/0/0
            if category == "PBB" and '0/0/0' not in ifname:
                continue
            
            port_number = self._normalize_port_name(ifname, vendor)
            
            if target_port:
                if self.slot and port_number != target_port:
                    continue
                elif not self.slot and not port_number.startswith(target_port):
                    continue
            
            bandwidth = self._extract_bandwidth_from_ifname(ifname)
            bundle_info = self._get_port_bundle_info(port_number, bundle_data)
            
            description = ifalias
            
            port_info = {
                "port": port_number,
                "bandwidth": bandwidth,
                "status": status,
                "admin_status": status,
                "physical_address": ifphysaddr,
                "description": description,
                "model": model,
                "vendor": vendor,
                "category": category
            }
            
            if bundle_info["bundle"] != "N/A" and bundle_info["status_bundle"].lower() in ["up", "active"]:
                port_info.update({
                    "bundle": bundle_info["bundle"],
                    "status_bundle": bundle_info["status_bundle"],
                    "state": bundle_info["state"]
                })
            
            ports_info_temp.append(port_info)
            
            if status == "up":
                ports_up.append(port_number)
        
        return ports_info_temp, ports_up

    def get_equipment_info(self) -> dict:
        info = {
            "equipment_info": {
                "hostname": self.hostname,
                "ip_address": self.ip_address,
                "dns_complet": self.dns_complet if self.dns_complet else "DNS non résolu"
            },
            "lags": [],
            "ports": []  
        }

        try:
            monitoring_info = get_pbb_monitoring_info(self.hostname)
            info["equipment_info"].update(monitoring_info)
        except Exception as e:
            info["equipment_info"]["spectrum"] = f"Erreur: {str(e)}"
            info["equipment_info"]["cacti"] = f"Erreur: {str(e)}"

        # Récupération FQDN
        fqdn = self._get_fqdn_from_snmp()
        if not fqdn:
            fqdn = self.dns_complet if self.dns_complet else self.hostname

        # Tentative Prometheus
        prometheus_results = self._query_prometheus_unified(fqdn)
        
        use_snmp_fallback = False
        if not prometheus_results:
            use_snmp_fallback = True

        # Bundles
        bundle_data = self.get_bundle_info_equipment()
        
        for bundle_name, data in bundle_data.items():
            lag_info = {
                "bundle_name": bundle_name,
                "status": data.get('status', 'N/A'),
                "ports": []
            }
            
            for port in data.get('ports', []):
                port_name = port.get('port', 'N/A')
                port_clean = self._normalize_port_name(port_name)
                
                lag_info["ports"].append({
                    "port": port_clean,
                    "state": port.get('state', 'N/A')
                })
            
            info["lags"].append(lag_info)

        # Type et version via SNMP
        type_output = self._snmp_walk(self.OIDS['type'])
        type_info = self._parse_snmp_output_with_debug(type_output, 'type') if type_output else []
        
        if type_info and len(type_info) > 0:
            type_str, version_str = self._parse_type_info(type_info[0]['value'])
            raw_snmp_output = type_info[0]['raw_output']
            model = self._find_equipment_model(raw_snmp_output)
            info["equipment_info"]["type"] = model if model != "Unknown" else type_str
            info["equipment_info"]["Version"] = version_str

        target_port = self.ip
        if self.slot:
            target_port = f"{self.ip}/{self.slot}" if self.ip else None

        # Traitement des ports
        if use_snmp_fallback:
            # Mode SNMP
            oids_to_fetch = [
                self.OIDS['interface_status'],
                self.OIDS['interface_admin_status'],
                self.OIDS['interface_desc'],
                self.OIDS['physical_port'],
                self.OIDS['port_alias']
            ]
            snmp_results = self._parallel_snmp_walks(oids_to_fetch)
            
            interface_status = self._parse_snmp_output_with_debug(snmp_results.get(self.OIDS['interface_status'], ''), 'interface_status')
            interface_admin_status = self._parse_snmp_output_with_debug(snmp_results.get(self.OIDS['interface_admin_status'], ''), 'interface_admin_status')
            interface_desc = self._parse_snmp_output_with_debug(snmp_results.get(self.OIDS['interface_desc'], ''), 'interface_desc')
            physical_port = self._parse_snmp_output_with_debug(snmp_results.get(self.OIDS['physical_port'], ''), 'physical_port')
            port_alias = self._parse_snmp_output_with_debug(snmp_results.get(self.OIDS['port_alias'], ''), 'port_alias')

            status_dict = {item['index']: item for item in interface_status if item['index']}
            admin_status_dict = {item['index']: item for item in interface_admin_status if item['index']}
            desc_dict = {item['index']: item for item in interface_desc if item['index']}
            physical_dict = {item['index']: item for item in physical_port if item['index']}
            alias_dict = {item['index']: item for item in port_alias if item['index']}
            
            ports_up = []
            ports_info_temp = []
            
            for idx in desc_dict.keys():
                desc_item = desc_dict[idx]
                port_number = self._extract_port_number(desc_item['value']) or f"index_{idx}"
                status = status_dict.get(idx, {}).get('value', 'Unknown')
                admin_status = admin_status_dict.get(idx, {}).get('value', 'Unknown')
                physical_address = physical_dict.get(idx, {}).get('value', 'Unknown').replace(" ", ":")
                alias = alias_dict.get(idx, {}).get('value', 'Unknown')
                bandwidth = self._get_bandwidth(desc_item['value'])
                
                status = "up" if status == "1" else "down"
                admin_status = "up" if admin_status == "1" else "down"

                if target_port:
                    if self.slot and port_number != target_port:
                        continue
                    elif not self.slot and not port_number.startswith(target_port):
                        continue

                if (status == "down" and admin_status == "down" and 
                    (not alias or alias in ["Unknown", "", "N/A", None])):
                    continue
                
                if bandwidth == "Unknown":
                    continue
                    
                bundle_info = self._get_port_bundle_info(port_number, bundle_data)
                    
                port_info = {
                    "port": port_number,
                    "bandwidth": bandwidth,
                    "status": status,
                    "admin_status": admin_status,
                    "physical_address": physical_address,
                    "description": alias,
                    "index": idx
                }
                
                if bundle_info["bundle"] != "N/A" and bundle_info["status_bundle"].lower() in ["up", "active"]:
                    port_info.update({
                        "bundle": bundle_info["bundle"],
                        "status_bundle": bundle_info["status_bundle"],
                        "state": bundle_info["state"]
                    })
                
                ports_info_temp.append(port_info)
                
                if status == "up":
                    ports_up.append(port_number)
        else:
            # Mode Prometheus
            ports_info_temp, ports_up = self._process_ports_via_prometheus(prometheus_results, bundle_data, target_port)
            
            # Récupérer model/vendor/category du premier port
            if ports_info_temp:
                info["equipment_info"]["type"] = ports_info_temp[0].get('model', info["equipment_info"].get("type", "Unknown"))
                info["equipment_info"]["vendor"] = ports_info_temp[0].get('vendor', 'Unknown')
                info["equipment_info"]["category"] = ports_info_temp[0].get('category', 'Unknown')

        # Valeurs optiques
        optical_values_batch = {}
        if ports_up and self.dns_complet and self.intermediate_host:
            optical_values_batch = self.get_optical_power_values_batch(ports_up)

        # Assemblage final
        for port_info in ports_info_temp:
            port_number = port_info["port"]
            
            if port_info.get("status") == "up" and port_number in optical_values_batch:
                optical_values = optical_values_batch[port_number]
            else:
                optical_values = self._get_default_optical_values()
            
            port_info.update({
                "signal_optique_rx": optical_values['signal_optique_rx'],
                "signal_optique_tx": optical_values['signal_optique_tx'],
                "threshold": optical_values['threshold'],
                "type_sfp": optical_values['type_sfp'],
                "fec_state": optical_values['fec_state'],
                "wavelength": optical_values['wavelength'],
                "alarm_status": optical_values['alarm_status'],
                "led_state": optical_values['led_state'],        
                "laser_state": optical_values['laser_state']    
            })
            
            port_info.pop('index', None)
            port_info.pop('model', None)
            port_info.pop('vendor', None)
            port_info.pop('category', None)
            
            info["ports"].append(port_info)

        return info

    def get_port_info(self, ip: Optional[str] = None, slot: Optional[str] = None) -> Optional[List[Dict]]:
        target_ip = ip if ip is not None else self.ip
        target_slot = slot if slot is not None else self.slot
        target_port = target_ip
        if target_slot:
            target_port = f"{target_ip}/{target_slot}" if target_ip else None

        equipment_info = self.get_equipment_info()
        ports = equipment_info.get("ports", [])
        
        if target_slot:
            return [port for port in ports if port["port"] == target_port]
        else:
            return [port for port in ports if port["port"].startswith(target_ip)]

    def print_equipment_info(self):
        return json.dumps(self.get_equipment_info(), indent=2)


# ===== MAIN =====

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ClassPBBWeb - Version Métrique Unique")
    print("=" * 60)
    print("ℹ️  Utilise une seule requête Prometheus pour tout récupérer")
    print("ℹ️  Filtre automatiquement les ports down et Optics")
    print("=" * 60)
    
    equipment_name = input("\n📝 Entrez le nom de l'équipement: ").strip()
    
    if not equipment_name:
        print("❌ Erreur: Nom d'équipement requis")
        exit(1)
    
    hostname_override = input("📝 Hostname FQDN (optionnel, laissez vide pour auto-détection): ").strip()
    port_filter = input("📝 Port spécifique (optionnel, ex: 0/0/0/1): ").strip()
    slot_filter = input("📝 Slot spécifique (optionnel): ").strip()
    
    try:
        print(f"\n🎯 Démarrage de l'analyse pour '{equipment_name}'...")
        print("=" * 60)
        start_time = time.time()
        
        network_equipment = NetworkEquipment(
            hostname=equipment_name,
            ip=port_filter if port_filter else None,
            slot=slot_filter if slot_filter else None
        )
        
        # Si l'utilisateur a fourni un hostname, l'utiliser directement
        if hostname_override:
            print(f"ℹ️  Utilisation du hostname fourni: {hostname_override}")
            network_equipment._fqdn = hostname_override
        
        if port_filter or slot_filter:
            result = {
                "equipment_info": network_equipment.get_equipment_info()["equipment_info"],
                "filtered_ports": network_equipment.get_port_info()
            }
        else:
            result = network_equipment.get_equipment_info()
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print(f"✅ ANALYSE TERMINÉE en {elapsed_time:.2f}s")
        print("=" * 60)
        print("📋 RÉSULTAT JSON:")
        print("=" * 60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except KeyboardInterrupt:
        print("\n\n❌ Opération annulée par l'utilisateur")
        exit(0)
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution: {str(e)}")
        print(f"🔍 Type d'erreur: {type(e).__name__}")
        
        import traceback
        print("\n📋 Traceback complet:")
        print("-" * 40)
        traceback.print_exc()
        print("-" * 40)