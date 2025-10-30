import json
import re
import socket
import subprocess
import concurrent.futures
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Union
from scripts.FindDNS import find_dns
from scripts.Version_Alcatel_Telco_One_Access import equipment_patterns
from scripts.PBB.PuissanceOptique import *
from scripts.SnmpRequests import snmp_request
from scripts.PBB.SpectrumPBB import *

@dataclass
class SNMPResponse:
    oid: str
    value: str
    index: Optional[str] = None
    raw_output: str = ""

class NetworkEquipment:
    OIDS = {
        'type': '1.3.6.1.2.1.1.1',
        'name': '1.3.6.1.2.1.1.5',
        'interface_status': '1.3.6.1.2.1.2.2.1.8',
        'interface_admin_status': '1.3.6.1.2.1.2.2.1.7',
        'interface_desc': '1.3.6.1.2.1.2.2.1.2',
        'physical_port': '1.3.6.1.2.1.2.2.1.6',
        'port_alias': '1.3.6.1.2.1.31.1.1.1.18',
    }

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

    def _snmp_walk(self, oid: str) -> Optional[str]:
        """SNMP walk avec mise en cache (fonction de SnmpRequests)"""
        if oid in self._snmp_cache:
            return self._snmp_cache[oid]
            
        hostname_to_use = self.dns_complet if self.dns_complet else self.hostname
        
        try:
            output = snmp_request(hostname_to_use, oid)
            if output and len(output) > 0:
                result = output.decode('utf-8') if isinstance(output, bytes) else output
                self._snmp_cache[oid] = result
                return result
        except Exception as e:
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
                except Exception as e:
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

    def _get_bandwidth(self, description: str) -> str:
        if "FourHundredGigE" in description:
            return "400G"
        elif "HundredGigE" in description:
            return "100G"
        elif "TenGigE" in description:
            return "10G"
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
        
        # Cas spécial pour Cisco 8000 : différencier selon le hostname
        if "Cisco IOS XR Software (8000)" in snmp_type_output:
            hostname_lower = self.hostname.lower()
            # Si le hostname commence par 'abr', c'est un 24H8FH
            if hostname_lower.startswith('abr'):
                return "Cisco 8201-24H8FH"
            # Sinon (pbb, lsr, ou autre), c'est un 32FH
            else:
                return "Cisco 8201-32FH"
        
        # Recherche du modèle dans equipment_patterns
        for pattern_info in equipment_patterns:
            match = re.search(pattern_info["pattern"], snmp_type_output)
            if match:
                if pattern_info.get("model") and pattern_info["model"] != "Unknown" and pattern_info["model"] is not None:
                    return pattern_info["model"]
        
        # Si pas de modèle, retourner le type
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

    def _get_port_bundle_info(self, port_number: str, bundle_data: Dict[str, Dict]) -> Dict[str, str]:
        """Détermine les informations de bundle pour un port donné"""
        bundle_info = {
            "bundle": "N/A",
            "status_bundle": "N/A", 
            "state": "N/A"
        }
        
        # Normaliser le port en retirant uniquement les préfixes mais gardant le format complet
        port_normalized = port_number.replace("Hu", "").replace("FH", "").replace("HundredGigE", "")
        if not port_normalized.startswith("0/0/0/"):
            port_normalized = f"0/0/0/{port_normalized}"
        
        for bundle_name, data in bundle_data.items():
            for port in data.get('ports', []):
                port_name = port.get('port', '')
                # Appliquer la même normalisation
                port_name_normalized = port_name.replace("Hu", "").replace("FH", "").replace("HundredGigE", "")
                if not port_name_normalized.startswith("0/0/0/"):
                    port_name_normalized = f"0/0/0/{port_name_normalized}"
                
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

        bundle_data = self.get_bundle_info_equipment()
        
        for bundle_name, data in bundle_data.items():
            lag_info = {
                "bundle_name": bundle_name,
                "status": data.get('status', 'N/A'),
                "ports": []
            }
            
            for port in data.get('ports', []):
                # Nettoyer uniquement le préfixe Hu/FH mais garder le chemin complet
                port_name = port.get('port', 'N/A')
                
                # Retirer uniquement les préfixes d'interface (Hu, FH, etc.) mais garder 0/0/0/X
                port_clean = port_name.replace('Hu', '').replace('FH', '').replace('HundredGigE', '')
                
                # Si le port ne commence pas par 0/0/0/, l'ajouter
                if port_clean and not port_clean.startswith('0/0/0/'):
                    port_clean = f"0/0/0/{port_clean}"
                
                lag_info["ports"].append({
                    "port": port_clean,
                    "state": port.get('state', 'N/A')
                })
            
            info["lags"].append(lag_info)

        oids_to_fetch = list(self.OIDS.values())
        snmp_results = self._parallel_snmp_walks(oids_to_fetch)
        
        type_output = snmp_results.get(self.OIDS['type'])
        type_info = self._parse_snmp_output_with_debug(type_output, 'type') if type_output else []
        
        if type_info and len(type_info) > 0:
            type_str, version_str = self._parse_type_info(type_info[0]['value'])

            # Utiliser _find_equipment_model pour tous les équipements
            raw_snmp_output = type_info[0]['raw_output']
            model = self._find_equipment_model(raw_snmp_output)
            info["equipment_info"]["type"] = model if model != "Unknown" else type_str
            
            info["equipment_info"]["Version"] = version_str

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

        target_port = self.ip
        if self.slot:
            target_port = f"{self.ip}/{self.slot}" if self.ip else None
            
        ports_up = []
        ports_info_temp = []
        
        for idx, desc_item in desc_dict.items():
            port_number = self._extract_port_number(desc_item['value']) or f"index_{idx}"
            if target_port:
                if self.slot and port_number != target_port:
                    continue
                elif not self.slot and not port_number.startswith(target_port):
                    continue

            status = status_dict.get(idx, {}).get('value', 'Unknown')
            admin_status = admin_status_dict.get(idx, {}).get('value', 'Unknown')
            physical_address = physical_dict.get(idx, {}).get('value', 'Unknown').replace(" ", ":")
            alias = alias_dict.get(idx, {}).get('value', 'Unknown')

            status = "up" if status == "1" else "down"
            admin_status = "up" if admin_status == "1" else "down"
            
            if (status == "down" and admin_status == "down" and 
                (not alias or alias in ["Unknown", "", "N/A", None])):
                continue
            
            bandwidth = self._get_bandwidth(desc_item['value'])
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

        optical_values_batch = {}
        if ports_up and self.dns_complet and self.intermediate_host:
            optical_values_batch = self.get_optical_power_values_batch(ports_up)

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