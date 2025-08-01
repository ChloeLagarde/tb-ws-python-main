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
        print(f"Erreur SNMP: {e}")
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
        print(f"🔧 Initialisation pour {hostname}")
        
        self.hostname = hostname
        self.ip = ip
        self.slot = slot  
        self.version = version
        
        # Résolution DNS
        print(f"📡 Résolution DNS pour {hostname}...")
        self.dns_complet = find_dns(hostname)
        print(f"✅ DNS résolu: {self.dns_complet}")
        
        # Résolution IP
        try:
            if self.dns_complet:
                self.ip_address = socket.gethostbyname(self.dns_complet)
                print(f"🌐 IP résolue: {self.ip_address}")
            else:
                self.ip_address = "DNS non résolu"
        except socket.gaierror as e:
            self.ip_address = f"Erreur résolution: {str(e)}"
            print(f"❌ Erreur résolution IP: {e}")
            
        self.intermediate_host = intermediate_host or "vma-prddck-104.pau"
        self.max_workers = max_workers
        self._snmp_cache = {}

    def _snmp_walk(self, oid: str) -> Optional[str]:
        """SNMP walk avec mise en cache et logging"""
        if oid in self._snmp_cache:
            return self._snmp_cache[oid]
            
        hostname_to_use = self.dns_complet if self.dns_complet else self.hostname
        
        try:
            print(f"📊 SNMP query: {oid} sur {hostname_to_use}")
            output = snmp_request(hostname_to_use, oid)
            if output and len(output) > 0:
                result = output.decode('utf-8', errors='ignore') if isinstance(output, bytes) else str(output)
                self._snmp_cache[oid] = result
                print(f"✅ SNMP OK: {len(result)} caractères")
                return result
            else:
                print(f"⚠️  SNMP vide pour {oid}")
        except Exception as e:
            print(f"❌ Erreur SNMP {oid}: {e}")
        
        return None

    def _parallel_snmp_walks(self, oids: List[str]) -> Dict[str, Optional[str]]:
        """Exécute plusieurs SNMP walks en parallèle avec logging"""
        print(f"🔄 Exécution de {len(oids)} requêtes SNMP en parallèle...")
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(oids), self.max_workers)) as executor:
            future_to_oid = {executor.submit(self._snmp_walk, oid): oid for oid in oids}
            for future in concurrent.futures.as_completed(future_to_oid):
                oid = future_to_oid[future]
                try:
                    results[oid] = future.result()
                except Exception as e:
                    print(f"❌ Erreur future {oid}: {e}")
                    results[oid] = None
        
        success_count = sum(1 for v in results.values() if v)
        print(f"📊 SNMP terminé: {success_count}/{len(oids)} réussies")
        return results

    def _extract_port_number(self, description: str) -> Optional[str]:
        """Extrait le numéro de port depuis la description"""
        patterns = [
            r'(\d+/\d+/\d+/\d+/\d+)',  
            r'(\d+/\d+/\d+/\d+)',      
            r'[Pp]ort[:\s-]*(\d+/\d+/\d+/\d+/\d+)',  
            r'[Pp]ort[:\s-]*(\d+/\d+/\d+/\d+)',
            r'HundredGigE(\d+/\d+/\d+/\d+)',
            r'TenGigE(\d+/\d+/\d+/\d+)',
            r'GigabitEthernet(\d+/\d+/\d+/\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
        return None

    def _clean_value(self, value: str) -> str:
        """Nettoie les valeurs SNMP"""
        if not isinstance(value, str):
            value = str(value)
        value = value.strip('"').strip("'")
        prefixes = ['INTEGER: ', 'STRING: ', 'Hex-STRING: ', 'Hex-', 'Counter32: ', 'Gauge32: ']
        for prefix in prefixes:
            if value.startswith(prefix):
                value = value[len(prefix):]
        return value.strip()

    def _parse_snmp_output_with_debug(self, output: str, oid_type: str) -> List[Dict]:
        """Parse la sortie SNMP avec debug"""
        if not output:
            return []
        
        responses = []
        lines = output.splitlines()
        print(f"📋 Parsing {oid_type}: {len(lines)} lignes")
        
        for line in lines:
            if not line.strip():
                continue
                
            # Pattern principal
            patterns = [
                r'([\w-]+::[\w.]+)\.(\d+)\s+=\s+(.+)',
                r'([\w.-]+)::(\w+)\.(\d+)\s+=\s+(.+)',
                r'iso\.[\d.]+\.(\d+)\s+=\s+(.+)',
            ]
            
            matched = False
            for i, pattern in enumerate(patterns):
                match = re.match(pattern, line)
                if match:
                    matched = True
                    if i == 2:  # iso pattern
                        index = match.group(1)
                        value = self._clean_value(match.group(2))
                        oid = "iso"
                    else:
                        index = match.group(2) if i == 0 else match.group(3)
                        value = self._clean_value(match.group(3) if i == 0 else match.group(4))
                        oid = match.group(1) if i == 0 else f"{match.group(1)}::{match.group(2)}"
                    
                    responses.append({
                        'oid': oid,
                        'index': index,
                        'value': value,
                        'raw_output': line
                    })
                    break
        
        print(f"✅ Parsed {oid_type}: {len(responses)} entrées")
        return responses

    def _get_bandwidth(self, description: str) -> str:
        """Détermine la bande passante depuis la description"""
        if "FourHundredGigE" in description or "400G" in description:
            return "400G"
        elif "HundredGigE" in description or "100G" in description:
            return "100G"
        elif "TenGigE" in description or "10G" in description:
            return "10G"
        elif "GigabitEthernet" in description or "1G" in description:
            return "1G"
        return "Unknown"

    def _find_equipment_model(self, snmp_type_output: str) -> str:
        """Trouve le modèle d'équipement"""
        for pattern_info in equipment_patterns:
            try:
                if re.search(pattern_info["pattern"], snmp_type_output, re.IGNORECASE):
                    return pattern_info.get("model", pattern_info.get("type", "Unknown"))
            except Exception:
                continue
        return "Unknown"

    def get_equipment_info(self) -> dict:
        """Récupère toutes les informations de l'équipement"""
        print(f"\n🎯 Début analyse complète de {self.hostname}")
        
        info = {
            "equipment_info": {
                "hostname": self.hostname,
                "ip_address": self.ip_address,
                "dns_complet": self.dns_complet if self.dns_complet else "DNS non résolu",
                "type": "Unknown",
                "Version": "Unknown"
            },
            "lags": [],
            "ports": []  
        }

        # Informations de monitoring
        print("📊 Récupération des infos de monitoring...")
        try:
            monitoring_info = get_pbb_monitoring_info(self.hostname)
            info["equipment_info"].update(monitoring_info)
        except Exception as e:
            print(f"❌ Erreur monitoring: {e}")
            info["equipment_info"]["spectrum"] = f"Erreur: {str(e)}"
            info["equipment_info"]["cacti"] = f"Erreur: {str(e)}"

        # Si pas de DNS, on s'arrête là
        if not self.dns_complet or self.ip_address.startswith("Erreur"):
            print("⚠️  Impossible de continuer sans DNS valide")
            return info

        # Requêtes SNMP
        try:
            print("📡 Démarrage des requêtes SNMP...")
            oids_to_fetch = list(self.OIDS.values())
            snmp_results = self._parallel_snmp_walks(oids_to_fetch)
            
            # Analyser le type d'équipement
            type_output = snmp_results.get(self.OIDS['type'])
            if type_output:
                print("🔍 Analyse du type d'équipement...")
                type_info = self._parse_snmp_output_with_debug(type_output, 'type')
                if type_info and len(type_info) > 0:
                    type_value = type_info[0]['value']
                    model = self._find_equipment_model(type_value)
                    info["equipment_info"]["type"] = model
                    
                    # Extraction de version
                    version_match = re.search(r'Version\s+([^\s,]+)', type_value)
                    if version_match:
                        info["equipment_info"]["Version"] = version_match.group(1)

            # Analyser les interfaces
            print("🔌 Analyse des interfaces...")
            interface_desc = self._parse_snmp_output_with_debug(
                snmp_results.get(self.OIDS['interface_desc'], ''), 'interface_desc'
            )
            interface_status = self._parse_snmp_output_with_debug(
                snmp_results.get(self.OIDS['interface_status'], ''), 'interface_status'
            )
            interface_admin_status = self._parse_snmp_output_with_debug(
                snmp_results.get(self.OIDS['interface_admin_status'], ''), 'interface_admin_status'
            )
            port_alias = self._parse_snmp_output_with_debug(
                snmp_results.get(self.OIDS['port_alias'], ''), 'port_alias'
            )

            # Créer des dictionnaires de lookup
            status_dict = {item['index']: item for item in interface_status if item.get('index')}
            admin_status_dict = {item['index']: item for item in interface_admin_status if item.get('index')}
            desc_dict = {item['index']: item for item in interface_desc if item.get('index')}
            alias_dict = {item['index']: item for item in port_alias if item.get('index')}

            print(f"📊 Traitement de {len(desc_dict)} interfaces...")

            # Traitement des ports
            port_count = 0
            for idx, desc_item in desc_dict.items():
                try:
                    description = desc_item['value']
                    port_number = self._extract_port_number(description)
                    
                    if not port_number:
                        continue

                    # Filtrage par port spécifique si demandé
                    if self.ip:
                        if self.slot and port_number != f"{self.ip}/{self.slot}":
                            continue
                        elif not self.slot and not port_number.startswith(str(self.ip)):
                            continue

                    # États
                    status_item = status_dict.get(idx, {})
                    admin_status_item = admin_status_dict.get(idx, {})
                    alias_item = alias_dict.get(idx, {})

                    status = "up" if status_item.get('value') == "1" else "down"
                    admin_status = "up" if admin_status_item.get('value') == "1" else "down"
                    alias = alias_item.get('value', 'N/A')

                    # Filtrer les ports down sans description
                    if (status == "down" and admin_status == "down" and 
                        (not alias or alias in ["Unknown", "", "N/A", None])):
                        continue

                    # Bande passante
                    bandwidth = self._get_bandwidth(description)
                    if bandwidth == "Unknown":
                        continue

                    port_info = {
                        "port": port_number,
                        "bandwidth": bandwidth,
                        "status": status,
                        "admin_status": admin_status,
                        "description": alias,
                        "interface_description": description,
                        "index": idx,
                        # Valeurs optiques par défaut
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
                    
                    info["ports"].append(port_info)
                    port_count += 1

                except Exception as e:
                    print(f"❌ Erreur traitement port {idx}: {e}")
                    continue

            print(f"✅ {port_count} ports traités avec succès")

        except Exception as e:
            print(f"❌ Erreur SNMP générale: {e}")
            info["equipment_info"]["error"] = f"Erreur SNMP: {str(e)}"

        print(f"🎉 Analyse terminée: {len(info['ports'])} ports trouvés")
        return info

    def get_port_info(self, ip: Optional[str] = None, slot: Optional[str] = None) -> Optional[List[Dict]]:
        """Récupère les informations d'un port spécifique"""
        target_ip = ip if ip is not None else self.ip
        target_slot = slot if slot is not None else self.slot
        
        equipment_info = self.get_equipment_info()
        ports = equipment_info.get("ports", [])
        
        if target_slot:
            target_port = f"{target_ip}/{target_slot}" if target_ip else None
            return [port for port in ports if port["port"] == target_port]
        elif target_ip:
            return [port for port in ports if port["port"].startswith(str(target_ip))]
        else:
            return ports

    def print_equipment_info(self):
        """Affiche les informations de l'équipement en JSON"""
        return json.dumps(self.get_equipment_info(), indent=2, ensure_ascii=False)


# ===== MAIN =====

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ClassPBBWeb - Version Standalone")
    print("=" * 60)
    print("ℹ️  Cette version inclut toutes les dépendances")
    print("ℹ️  Aucun import externe requis")
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
        print(f"\n🎯 Démarrage de l'analyse...")
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