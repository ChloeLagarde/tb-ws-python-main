#!/usr/bin/env python3
"""
ClassPBBWeb.py - Version standalone
Inclut toutes les fonctions nécessaires pour éviter les problèmes d'import
"""

import json
import re
import socket
import subprocess
import concurrent.futures
import time
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Union

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
        # Simuler les vérifications Spectrum et Cacti
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

# Patterns d'équipements (version simplifiée)
equipment_patterns = [
    {"pattern": r'Cisco IOS XR Software \(8000\)', "type": "CISCO", "model": "Cisco 8201-32FH"},
    {"pattern": r'TiMOS.*Nokia 7750', "type": "7750", "model": "Nokia 7750"},
    {"pattern": r'TiMOS.*Nokia 7250', "type": "7250", "model": "Nokia 7250"},
    {"pattern": r'TiMOS.*ALCATEL', "type": "ALCATEL", "model": "Alcatel"},
    {"pattern": r'HUAWEI', "type": "HUAWEI", "model": "Huawei"},
    {"pattern": r'Cisco IOS Software', "type": "CISCO", "model": "Cisco IOS"},
]

# Fonctions optiques simplifiées
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
        'name': '1.3.6.1.2.1.1.5',  # Seul OID conservé pour récupérer le DNS
        'type': '1.3.6.1.2.1.1.1',
        'interface_status': '1.3.6.1.2.1.2.2.1.8',
        'interface_admin_status': '1.3.6.1.2.1.2.2.1.7',
        'interface_desc': '1.3.6.1.2.1.2.2.1.2',
        'physical_port': '1.3.6.1.2.1.2.2.1.6',
        'port_alias': '1.3.6.1.2.1.31.1.1.1.18',
    }
    
    PROMETHEUS_BASE_URL = "http://promxy.query.consul:8082/api/v1/query"
    
    METRICS_QUERIES = {
        'interface_status': 'ifMetrics_ifOperStatus',
        'interface_admin_status': 'ifMetrics_ifAdminStatus',
        'interface_desc': 'ifMetrics_ifDescr',
        'interface_alias': 'ifMetrics_ifAlias',
        'interface_physaddr': 'ifMetrics_ifPhysAddress',
        'interface_speed': 'ifMetrics_ifHighSpeed',
    }

    def __init__(self, hostname: str, ip: Optional[str] = None, slot: Optional[str] = None, 
                 community: Union[str, List[str]] = None, version: str = '2c', 
                 intermediate_host: Optional[str] = None, max_workers: int = 5):
        self.hostname = hostname
        self.ip = ip
        self.slot = slot  
        self.version = version
        
        print(f"🔍 Recherche du DNS pour {hostname}...")
        self.dns_complet = find_dns(hostname)
        
        if self.dns_complet:
            print(f"✅ DNS trouvé: {self.dns_complet}")
            try:
                self.ip_address = socket.gethostbyname(self.dns_complet)
                print(f"✅ IP résolue: {self.ip_address}")
            except Exception as e:
                print(f"⚠️  Erreur lors de la résolution IP: {e}")
                self.ip_address = "IP non résolue"
        else:
            print(f"❌ DNS non résolu pour {hostname}")
            self.ip_address = "DNS non résolu"
        
        self.intermediate_host = "vma-prddck-104.pau"
        self.max_workers = max_workers
        self._snmp_cache = {}
        self._fqdn = None  # FQDN récupéré via SNMP

    def _get_fqdn_from_snmp(self) -> Optional[str]:
        """Récupère le FQDN via SNMP (OID sysName)"""
        if self._fqdn:
            print(f"ℹ️  FQDN déjà en cache: {self._fqdn}")
            return self._fqdn
            
        hostname_to_use = self.dns_complet if self.dns_complet else self.hostname
        
        print(f"🔍 Récupération du FQDN via SNMP depuis {hostname_to_use}...")
        
        try:
            output = snmp_request(hostname_to_use, self.OIDS['name'])
            if output and len(output) > 0:
                result = output.decode('utf-8') if isinstance(output, bytes) else output
                # Parser la sortie SNMP pour extraire le hostname
                match = re.search(r'STRING:\s*"?([^"\n]+)"?', result)
                if match:
                    self._fqdn = match.group(1).strip()
                    print(f"✅ FQDN récupéré via SNMP: {self._fqdn}")
                    return self._fqdn
                else:
                    print(f"⚠️  Format de réponse SNMP inattendu: {result[:100]}")
            else:
                print(f"⚠️  Réponse SNMP vide")
        except Exception as e:
            print(f"❌ Erreur lors de la récupération du FQDN via SNMP: {e}")
        
        return None

    def _query_prometheus(self, metric_name: str, hostname: str) -> Optional[Dict]:
        """Exécute une requête Prometheus et retourne les résultats"""
        try:
            query = f'{metric_name}{{hostname=~"{hostname}"}}'
            params = {'query': query}
            
            print(f"🔍 Requête Prometheus: {query}")
            
            response = requests.get(self.PROMETHEUS_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success' and data.get('data', {}).get('result'):
                result_count = len(data['data']['result'])
                print(f"✅ Prometheus {metric_name}: {result_count} résultats")
                return data['data']['result']
            else:
                print(f"⚠️  Prometheus {metric_name}: Aucun résultat")
            
            return None
            
        except requests.exceptions.Timeout as e:
            print(f"⏱️  Timeout Prometheus pour {metric_name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur requête Prometheus pour {metric_name}: {e}")
            return None

    def _parallel_prometheus_queries(self, fqdn: str) -> Dict[str, Optional[List]]:
        """Exécute plusieurs requêtes Prometheus en parallèle"""
        print(f"\n📊 Début des requêtes Prometheus pour FQDN: {fqdn}")
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.METRICS_QUERIES)) as executor:
            future_to_metric = {
                executor.submit(self._query_prometheus, metric_name, fqdn): key 
                for key, metric_name in self.METRICS_QUERIES.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_metric):
                metric_key = future_to_metric[future]
                try:
                    results[metric_key] = future.result()
                except Exception as e:
                    print(f"❌ Erreur lors de la récupération de {metric_key}: {e}")
                    results[metric_key] = None
        
        print(f"📊 Fin des requêtes Prometheus\n")
        return results

    def _parse_prometheus_results(self, results: List[Dict]) -> Dict[str, Dict]:
        """Parse les résultats Prometheus en un dictionnaire indexé par index
        
        Exemple de structure d'entrée:
        {
            "metric": {
                "ifAlias": "...",
                "ifDescr": "HundredGigE0/0/0/10/0",
                "ifPhysAddress": "3c:26:e4:4c:6e:50",
                "index": "78",
                ...
            },
            "value": [1764067798.148, "1"]
        }
        """
        parsed = {}
        
        if not results:
            return parsed
        
        for result in results:
            metric = result.get('metric', {})
            value_array = result.get('value', [])
            
            # La valeur est dans value[1]
            value = value_array[1] if len(value_array) > 1 else None
            
            # L'index est dans metric['index']
            index = metric.get('index')
            if not index:
                continue
            
            if index not in parsed:
                parsed[index] = {
                    'value': value,
                    'ifDescr': metric.get('ifDescr', ''),
                    'ifAlias': metric.get('ifAlias', ''),
                    'ifName': metric.get('ifName', ''),
                    'ifPhysAddress': metric.get('ifPhysAddress', ''),
                    'ifType': metric.get('ifType', ''),
                    'metric': metric
                }
            else:
                # Mettre à jour avec les nouvelles informations
                parsed[index]['value'] = value
                parsed[index]['metric'].update(metric)
        
        return parsed

    def _snmp_walk(self, oid: str) -> Optional[str]:
        """SNMP walk avec mise en cache (utilisé en fallback)"""
        if oid in self._snmp_cache:
            return self._snmp_cache[oid]
            
        hostname_to_use = self.dns_complet if self.dns_complet else self.hostname
        
        print(f"🔍 SNMP walk sur {hostname_to_use} pour OID {oid}")
        
        try:
            output = snmp_request(hostname_to_use, oid)
            if output and len(output) > 0:
                result = output.decode('utf-8') if isinstance(output, bytes) else output
                self._snmp_cache[oid] = result
                print(f"✅ SNMP walk réussi pour OID {oid}")
                return result
            else:
                print(f"⚠️  SNMP walk vide pour OID {oid}")
        except Exception as e:
            print(f"❌ Erreur SNMP walk pour OID {oid}: {e}")
        
        return None

    def _parallel_snmp_walks(self, oids: List[str]) -> Dict[str, Optional[str]]:
        """Exécute plusieurs SNMP walks en parallèle (utilisé en fallback)"""
        print(f"\n📊 Début des requêtes SNMP (fallback) pour {len(oids)} OIDs")
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(oids)) as executor:
            future_to_oid = {executor.submit(self._snmp_walk, oid): oid for oid in oids}
            for future in concurrent.futures.as_completed(future_to_oid):
                oid = future_to_oid[future]
                try:
                    results[oid] = future.result()
                except Exception as e:
                    print(f"❌ Erreur SNMP pour OID {oid}: {e}")
                    results[oid] = None
        print(f"📊 Fin des requêtes SNMP\n")
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
        """Détermine la bande passante à partir de la description ou de la vitesse"""
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
        
        if "FourHundredGigE" in description or "Fo" in description:
            return "400G"
        elif "HundredGigE" in description or "Hu" in description:
            return "100G"
        elif "TenGigE" in description or "Te" in description:
            return "10G"
        elif "GigabitEthernet" in description or "Gi" in description:
            return "1G"
        return "Unknown"

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
        """Détermine le modèle d'équipement basé sur la sortie SNMP et le hostname"""
        
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
        """Récupère les informations des bundles pour cet équipement"""
        try:
            bundle_info = get_bundle_info(self.dns_complet, self.intermediate_host)
            return bundle_info
        except Exception as e:
            return {}

    def _normalize_port_name(self, port_name: str) -> str:
        """Normalise un nom de port en retirant les préfixes et en ajoutant 0/0/0/ si nécessaire"""
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
        """Détermine les informations de bundle pour un port donné"""
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
        """Retourne les valeurs optiques par défaut"""
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
        """Récupère les puissances optiques pour plusieurs ports en une seule connexion SSH"""
        try:
            optical_data = get_optical_power_batch(self.dns_complet, ports, self.intermediate_host)
            return optical_data
        except Exception as e:
            return {port: self._get_default_optical_values() for port in ports}

    def get_optical_power_values(self) -> Dict[str, Union[str, Dict[str, str]]]:
        """Version compatible pour un seul port (rétrocompatibilité)"""
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
        except Exception as e:
            return self._get_default_optical_values()
        finally:
            close_all_connections()

    def get_equipment_info(self) -> dict:
        print("\n" + "="*60)
        print("📊 DÉBUT DE LA RÉCUPÉRATION DES INFORMATIONS")
        print("="*60)
        
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
            info["equipment_info"]["spectrum"] = f"Erreur lors de la récupération Spectrum: {str(e)}"
            info["equipment_info"]["cacti"] = f"Erreur lors de la récupération Cacti: {str(e)}"

        # ÉTAPE 1: Récupérer le FQDN via SNMP EN PREMIER
        print("\n📍 ÉTAPE 1: Récupération du FQDN")
        print("-" * 60)
        fqdn = self._get_fqdn_from_snmp()
        if not fqdn:
            print("⚠️  Impossible de récupérer le FQDN via SNMP")
            print(f"ℹ️  Utilisation du DNS complet comme fallback: {self.dns_complet if self.dns_complet else self.hostname}")
            fqdn = self.dns_complet if self.dns_complet else self.hostname
        
        print(f"✅ FQDN final utilisé: {fqdn}")

        # ÉTAPE 2: Tentative de récupération via Prometheus
        print("\n📍 ÉTAPE 2: Requêtes Prometheus")
        print("-" * 60)
        use_snmp_fallback = False
        metrics_results = self._parallel_prometheus_queries(fqdn)
        
        # Vérifier si les métriques sont disponibles
        successful_metrics = sum(1 for v in metrics_results.values() if v is not None and len(v) > 0)
        total_metrics = len(metrics_results)
        
        print(f"📊 Résultats Prometheus: {successful_metrics}/{total_metrics} métriques récupérées")
        
        if successful_metrics == 0:
            print("⚠️  Aucune métrique Prometheus disponible, basculement vers SNMP")
            use_snmp_fallback = True
        else:
            print(f"✅ Utilisation de Prometheus ({successful_metrics} métriques disponibles)")

        # ÉTAPE 3: Récupération des bundles
        print("\n📍 ÉTAPE 3: Récupération des bundles")
        print("-" * 60)
        bundle_data = self.get_bundle_info_equipment()
        if bundle_data:
            print(f"✅ {len(bundle_data)} bundles trouvés")
        else:
            print("ℹ️  Aucun bundle trouvé")
        
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

        # ÉTAPE 4: Récupération des informations d'équipement (type et version)
        print("\n📍 ÉTAPE 4: Récupération du type d'équipement")
        print("-" * 60)
        type_output = self._snmp_walk(self.OIDS['type'])
        type_info = self._parse_snmp_output_with_debug(type_output, 'type') if type_output else []
        
        if type_info and len(type_info) > 0:
            type_str, version_str = self._parse_type_info(type_info[0]['value'])
            raw_snmp_output = type_info[0]['raw_output']
            model = self._find_equipment_model(raw_snmp_output)
            info["equipment_info"]["type"] = model if model != "Unknown" else type_str
            info["equipment_info"]["Version"] = version_str
            print(f"✅ Type: {info['equipment_info']['type']}")
            print(f"✅ Version: {info['equipment_info']['Version']}")
        else:
            print("⚠️  Impossible de récupérer le type d'équipement")

        # ÉTAPE 5: Traitement des ports
        print("\n📍 ÉTAPE 5: Récupération des ports")
        print("-" * 60)
        
        if use_snmp_fallback:
            print("🔄 Mode SNMP (fallback)")
            # Utiliser SNMP comme fallback
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
            
            print(f"✅ SNMP: {len(desc_dict)} interfaces trouvées")
        else:
            print("🔄 Mode Prometheus")
            # Utiliser les métriques Prometheus
            status_dict = self._parse_prometheus_results(metrics_results.get('interface_status', []))
            admin_status_dict = self._parse_prometheus_results(metrics_results.get('interface_admin_status', []))
            desc_dict = self._parse_prometheus_results(metrics_results.get('interface_desc', []))
            physical_dict = self._parse_prometheus_results(metrics_results.get('interface_physaddr', []))
            alias_dict = self._parse_prometheus_results(metrics_results.get('interface_alias', []))
            speed_dict = self._parse_prometheus_results(metrics_results.get('interface_speed', []))
            
            print(f"✅ Prometheus: {len(desc_dict)} interfaces trouvées")

        target_port = self.ip
        if self.slot:
            target_port = f"{self.ip}/{self.slot}" if self.ip else None
        
        if target_port:
            print(f"🎯 Filtrage sur le port: {target_port}")
            
        ports_up = []
        ports_info_temp = []
        
        print(f"\n🔍 Analyse des ports...")
        
        for idx in desc_dict.keys():
            if use_snmp_fallback:
                # Mode SNMP
                desc_item = desc_dict[idx]
                port_number = self._extract_port_number(desc_item['value']) or f"index_{idx}"
                status = status_dict.get(idx, {}).get('value', 'Unknown')
                admin_status = admin_status_dict.get(idx, {}).get('value', 'Unknown')
                physical_address = physical_dict.get(idx, {}).get('value', 'Unknown').replace(" ", ":")
                alias = alias_dict.get(idx, {}).get('value', 'Unknown')
                bandwidth = self._get_bandwidth(desc_item['value'])
                
                status = "up" if status == "1" else "down"
                admin_status = "up" if admin_status == "1" else "down"
            else:
                # Mode Prometheus
                desc_data = desc_dict[idx]
                
                # Extraire ifDescr depuis le dictionnaire parsé
                desc_value = desc_data.get('ifDescr', '')
                port_number = self._extract_port_number(desc_value) or f"index_{idx}"
                
                # Status : 1 = up, 2 = down
                status_value = status_dict.get(idx, {}).get('value', '2')
                status = "up" if status_value == "1" else "down"
                
                admin_status_value = admin_status_dict.get(idx, {}).get('value', '2')
                admin_status = "up" if admin_status_value == "1" else "down"
                
                # Adresse physique
                physical_address = physical_dict.get(idx, {}).get('ifPhysAddress', 'Unknown')
                
                # Alias
                alias = alias_dict.get(idx, {}).get('ifAlias', 'Unknown')
                
                # Vitesse pour déterminer la bande passante
                speed = speed_dict.get(idx, {}).get('value')
                bandwidth = self._get_bandwidth(desc_value, speed)

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

        print(f"✅ {len(ports_info_temp)} ports valides trouvés")
        print(f"✅ {len(ports_up)} ports UP")

        # ÉTAPE 6: Récupération des valeurs optiques
        print("\n📍 ÉTAPE 6: Récupération des valeurs optiques")
        print("-" * 60)
        
        optical_values_batch = {}
        if ports_up and self.dns_complet and self.intermediate_host:
            print(f"🔍 Récupération des valeurs optiques pour {len(ports_up)} ports...")
            optical_values_batch = self.get_optical_power_values_batch(ports_up)
            print(f"✅ Valeurs optiques récupérées")
        else:
            print("ℹ️  Pas de ports UP ou DNS non résolu, valeurs optiques par défaut")

        # ÉTAPE 7: Assemblage final
        print("\n📍 ÉTAPE 7: Assemblage des données finales")
        print("-" * 60)
        
        for port_info in ports_info_temp:
            port_number = port_info["port"]
            
            if port_info["status"] == "up" and port_number in optical_values_batch:
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
            
            info["ports"].append(port_info)

        print(f"✅ {len(info['ports'])} ports ajoutés au résultat final")
        print("\n" + "="*60)
        print("✅ RÉCUPÉRATION DES INFORMATIONS TERMINÉE")
        print("="*60 + "\n")

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
    print("🚀 ClassPBBWeb - Version Standalone Corrigée")
    print("=" * 60)
    print("ℹ️  Cette version inclut toutes les dépendances")
    print("ℹ️  Avec messages de debug améliorés")
    print("=" * 60)
    
    # Demander le nom d'équipement
    equipment_name = input("\n📝 Entrez le nom de l'équipement: ").strip()
    
    if not equipment_name:
        print("❌ Erreur: Nom d'équipement requis")
        exit(1)
    
    # Demander le port spécifique (optionnel)
    port_filter = input("📝 Port spécifique (optionnel, ex: 0/0/0/1): ").strip()
    slot_filter = input("📝 Slot spécifique (optionnel): ").strip()
    
    try:
        print(f"\n🎯 Démarrage de l'analyse pour '{equipment_name}'...")
        print("=" * 60)
        start_time = time.time()
        
        # Créer l'instance
        network_equipment = NetworkEquipment(
            hostname=equipment_name,
            ip=port_filter if port_filter else None,
            slot=slot_filter if slot_filter else None
        )
        
        # Récupérer les informations
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
        
        # Traceback détaillé
        import traceback
        print("\n📋 Traceback complet:")
        print("-" * 40)
        traceback.print_exc()
        print("-" * 40)