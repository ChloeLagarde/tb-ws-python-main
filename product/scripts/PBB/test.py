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
        'name': '1.3.6.1.2.1.1.5',  # OID pour récupérer le FQDN
        'type': '1.3.6.1.2.1.1.1',
    }
    
    PROMETHEUS_BASE_URL = "http://promxy.query.consul:8082/api/v1/query"

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
        self._fqdn = None

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

    def _query_prometheus_unified(self, hostname: str, max_retries: int = 20) -> Optional[List[Dict]]:
        """Exécute une seule requête Prometheus avec système de retry"""
        query = f'ifMetrics_ifAdminStatus{{hostname="{hostname}", ifName=~".*0/0/0.*"}}'
        params = {'query': query}
        
        # Construire l'URL complète pour affichage
        full_url = f"{self.PROMETHEUS_BASE_URL}?query={requests.utils.quote(query)}"
        print(f"🔍 URL Prometheus générée:")
        print(f"   {full_url}")
        print(f"🔄 Tentatives de récupération (max: {max_retries})...")
        
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(self.PROMETHEUS_BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('status') == 'success' and data.get('data', {}).get('result'):
                    result_count = len(data['data']['result'])
                    print(f"✅ Tentative {attempt}/{max_retries}: {result_count} résultats récupérés")
                    return data['data']['result']
                else:
                    print(f"⏳ Tentative {attempt}/{max_retries}: Aucun résultat (attente 2s...)")
                    time.sleep(2)
                    
            except requests.exceptions.Timeout as e:
                print(f"⏱️  Tentative {attempt}/{max_retries}: Timeout (attente 2s...)")
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                print(f"❌ Tentative {attempt}/{max_retries}: Erreur - {e}")
                time.sleep(2)
        
        print(f"❌ Échec après {max_retries} tentatives - Basculement vers SNMP")
        return None

    def _extract_bandwidth_from_ifname(self, ifname: str) -> str:
        """Extrait le débit depuis le nom de l'interface"""
        if "FourHundredGigE" in ifname or ifname.startswith("Fo"):
            return "400G"
        elif "HundredGigE" in ifname or ifname.startswith("Hu"):
            return "100G"
        elif "TenGigE" in ifname or ifname.startswith("Te"):
            return "10G"
        elif "GigabitEthernet" in ifname or ifname.startswith("Gi"):
            return "1G"
        return "Unknown"

    def _normalize_port_name(self, port_name: str) -> str:
        """Normalise un nom de port en retirant les préfixes"""
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

    def _process_ports_via_prometheus(self, prometheus_results: List[Dict], 
                                      bundle_data: Dict[str, Dict], 
                                      target_port: Optional[str]) -> tuple:
        """Traite les ports depuis les résultats Prometheus"""
        ports_up = []
        ports_info_temp = []
        
        for result in prometheus_results:
            metric = result.get('metric', {})
            value_array = result.get('value', [])
            
            # Récupération des données
            ifname = metric.get('ifName', '')
            ifalias = metric.get('ifAlias', '')
            ifphysaddr = metric.get('ifPhysAddress', '')
            model = metric.get('model', 'Unknown')
            admin_status = value_array[1] if len(value_array) > 1 else '2'
            
            # Filtres
            # 1. Si le port est down (2), on skip
            if admin_status == '2':
                continue
            
            # 2. Si c'est un Optics dans la description, on skip
            if 'optics' in ifalias.lower():
                continue
            
            # Normalisation du port
            port_number = self._normalize_port_name(ifname)
            
            # Filtrage par port cible si spécifié
            if target_port:
                if self.slot and port_number != target_port:
                    continue
                elif not self.slot and not port_number.startswith(target_port):
                    continue
            
            # Détermination du débit
            bandwidth = self._extract_bandwidth_from_ifname(ifname)
            
            if bandwidth == "Unknown":
                continue
            
            # Informations bundle
            bundle_info = self._get_port_bundle_info(port_number, bundle_data)
            
            # Construction de la description avec le débit
            description = f"{ifname} ({bandwidth})"
            
            # Statut (1 = up)
            status = "up"
            
            port_info = {
                "port": port_number,
                "description": description,
                "model": model,
                "alias": ifalias,
                "status": status,
                "admin_status": status,
                "physical_address": ifphysaddr,
                "bandwidth": bandwidth
            }
            
            if bundle_info["bundle"] != "N/A" and bundle_info["status_bundle"].lower() in ["up", "active"]:
                port_info.update({
                    "bundle": bundle_info["bundle"],
                    "status_bundle": bundle_info["status_bundle"],
                    "state": bundle_info["state"]
                })
            
            ports_info_temp.append(port_info)
            ports_up.append(port_number)
        
        return ports_info_temp, ports_up

    def _process_ports_via_snmp(self, bundle_data: Dict[str, Dict], 
                                target_port: Optional[str]) -> tuple:
        """Traite les ports via SNMP (fallback)"""
        print("📡 Récupération SNMP des interfaces...")
        
        # OIDs nécessaires
        oids_to_fetch = [
            '1.3.6.1.2.1.2.2.1.8',   # interface_status
            '1.3.6.1.2.1.2.2.1.7',   # interface_admin_status
            '1.3.6.1.2.1.2.2.1.2',   # interface_desc
            '1.3.6.1.2.1.2.2.1.6',   # physical_port
            '1.3.6.1.2.1.31.1.1.1.18' # port_alias
        ]
        
        hostname_to_use = self.dns_complet if self.dns_complet else self.hostname
        
        # Récupération parallèle
        snmp_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(oids_to_fetch)) as executor:
            future_to_oid = {
                executor.submit(snmp_request, hostname_to_use, oid): oid 
                for oid in oids_to_fetch
            }
            
            for future in concurrent.futures.as_completed(future_to_oid):
                oid = future_to_oid[future]
                try:
                    output = future.result()
                    result = output.decode('utf-8') if isinstance(output, bytes) else output
                    snmp_results[oid] = result
                except Exception as e:
                    print(f"❌ Erreur SNMP pour OID {oid}: {e}")
                    snmp_results[oid] = ""
        
        # Parser les résultats
        def parse_snmp(output):
            if not output:
                return {}
            results = {}
            for line in output.splitlines():
                match = re.search(r'\.(\d+)\s+=\s+(?:INTEGER:\s*)?(?:STRING:\s*"?)?([^"\n]+)', line)
                if match:
                    results[match.group(1)] = match.group(2).strip('"').strip()
            return results
        
        status_dict = parse_snmp(snmp_results.get(oids_to_fetch[0], ''))
        admin_status_dict = parse_snmp(snmp_results.get(oids_to_fetch[1], ''))
        desc_dict = parse_snmp(snmp_results.get(oids_to_fetch[2], ''))
        physical_dict = parse_snmp(snmp_results.get(oids_to_fetch[3], ''))
        alias_dict = parse_snmp(snmp_results.get(oids_to_fetch[4], ''))
        
        ports_up = []
        ports_info_temp = []
        
        for idx in desc_dict.keys():
            desc_value = desc_dict[idx]
            port_number = self._extract_port_number(desc_value) or f"index_{idx}"
            
            status_val = status_dict.get(idx, '2')
            admin_status_val = admin_status_dict.get(idx, '2')
            status = "up" if status_val == "1" else "down"
            admin_status = "up" if admin_status_val == "1" else "down"
            
            physical_address = physical_dict.get(idx, 'Unknown').replace(" ", ":")
            alias = alias_dict.get(idx, 'Unknown')
            
            # Filtres SNMP
            if status == "down" and admin_status == "down" and (not alias or alias in ["Unknown", "", "N/A"]):
                continue
            
            if 'optics' in alias.lower():
                continue
            
            # Filtrage par port cible
            if target_port:
                if self.slot and port_number != target_port:
                    continue
                elif not self.slot and not port_number.startswith(target_port):
                    continue
            
            bandwidth = self._extract_bandwidth_from_ifname(desc_value)
            if bandwidth == "Unknown":
                continue
            
            bundle_info = self._get_port_bundle_info(port_number, bundle_data)
            
            port_info = {
                "port": port_number,
                "description": f"{desc_value} ({bandwidth})",
                "model": "Unknown",  # Non disponible via SNMP simple
                "alias": alias,
                "status": status,
                "admin_status": admin_status,
                "physical_address": physical_address,
                "bandwidth": bandwidth
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

    def get_bundle_info_equipment(self) -> Dict[str, Dict]:
        """Récupère les informations des bundles pour cet équipement"""
        try:
            bundle_info = get_bundle_info(self.dns_complet, self.intermediate_host)
            return bundle_info
        except Exception as e:
            return {}

    def get_optical_power_values_batch(self, ports: List[str]) -> Dict[str, Dict]:
        """Récupère les puissances optiques pour plusieurs ports"""
        try:
            optical_data = get_optical_power_batch(self.dns_complet, ports, self.intermediate_host)
            return optical_data
        except Exception as e:
            return {port: self._get_default_optical_values() for port in ports}

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
            info["equipment_info"]["spectrum"] = f"Erreur: {str(e)}"
            info["equipment_info"]["cacti"] = f"Erreur: {str(e)}"

        # ÉTAPE 1: Récupérer le FQDN via SNMP
        print("\n📍 ÉTAPE 1: Récupération du FQDN")
        print("-" * 60)
        fqdn = self._get_fqdn_from_snmp()
        if not fqdn:
            print("⚠️  Impossible de récupérer le FQDN via SNMP")
            print(f"ℹ️  Utilisation du DNS complet comme fallback: {self.dns_complet if self.dns_complet else self.hostname}")
            fqdn = self.dns_complet if self.dns_complet else self.hostname
        
        print(f"✅ FQDN final utilisé: {fqdn}")

        # ÉTAPE 2: Récupération via Prometheus (méthode unifiée avec retry)
        print("\n📍 ÉTAPE 2: Requête Prometheus unifiée avec retry")
        print("-" * 60)
        
        prometheus_results = self._query_prometheus_unified(fqdn)
        
        use_snmp_fallback = False
        if not prometheus_results:
            print("⚠️  Prometheus n'a retourné aucune donnée après 20 tentatives")
            print("🔄 Basculement vers SNMP...")
            use_snmp_fallback = True
        else:
            print(f"✅ {len(prometheus_results)} interfaces récupérées via Prometheus")

        # ÉTAPE 3: Récupération des bundles
        print("\n📍 ÉTAPE 3: Récupération des bundles")
        print("-" * 60)
        bundle_data = self.get_bundle_info_equipment()
        if bundle_data:
            print(f"✅ {len(bundle_data)} bundles trouvés")
            
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
        else:
            print("ℹ️  Aucun bundle trouvé")

        # ÉTAPE 4: Traitement des ports
        print("\n📍 ÉTAPE 4: Traitement des ports")
        print("-" * 60)
        
        target_port = self.ip
        if self.slot:
            target_port = f"{self.ip}/{self.slot}" if self.ip else None
        
        if target_port:
            print(f"🎯 Filtrage sur le port: {target_port}")
        
        ports_up = []
        ports_info_temp = []
        
        if use_snmp_fallback:
            print("🔄 Utilisation de SNMP (fallback)")
            # Code SNMP fallback ici
            ports_info_temp, ports_up = self._process_ports_via_snmp(bundle_data, target_port)
        else:
            print("🔄 Utilisation de Prometheus")
            ports_info_temp, ports_up = self._process_ports_via_prometheus(prometheus_results, bundle_data, target_port)
        
        print(f"✅ {len(ports_info_temp)} ports valides trouvés")
        if not use_snmp_fallback:
            print(f"✅ {len(ports_up)} ports UP")

        # ÉTAPE 5: Récupération des valeurs optiques
        print("\n📍 ÉTAPE 5: Récupération des valeurs optiques")
        print("-" * 60)
        
        optical_values_batch = {}
        if ports_up and self.dns_complet and self.intermediate_host:
            print(f"🔍 Récupération des valeurs optiques pour {len(ports_up)} ports...")
            optical_values_batch = self.get_optical_power_values_batch(ports_up)
            print(f"✅ Valeurs optiques récupérées")
        else:
            print("ℹ️  Pas de ports UP ou DNS non résolu, valeurs optiques par défaut")

        # ÉTAPE 6: Assemblage final
        print("\n📍 ÉTAPE 6: Assemblage des données finales")
        print("-" * 60)
        
        # Récupération du modèle depuis le premier port (ils ont tous le même)
        if ports_info_temp:
            equipment_model = ports_info_temp[0].get('model', 'Unknown')
            info["equipment_info"]["type"] = equipment_model
            print(f"✅ Modèle d'équipement: {equipment_model}")
        
        for port_info in ports_info_temp:
            port_number = port_info["port"]
            
            if port_number in optical_values_batch:
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
    print("🚀 ClassPBBWeb - Version Métrique Unique")
    print("=" * 60)
    print("ℹ️  Utilise une seule requête Prometheus pour tout récupérer")
    print("ℹ️  Filtre automatiquement les ports down et Optics")
    print("=" * 60)
    
    equipment_name = input("\n📝 Entrez le nom de l'équipement: ").strip()
    
    if not equipment_name:
        print("❌ Erreur: Nom d'équipement requis")
        exit(1)
    
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