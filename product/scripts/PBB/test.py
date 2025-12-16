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
        
        # Initialiser une session requests avec configuration similaire à Service.py
        self.session = requests.Session()
        self.session.verify = False  # Désactiver la vérification SSL
        
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
                    fqdn_raw = match.group(1).strip()
                    # Nettoyer le FQDN pour garder seulement le hostname complet
                    # Exemple: "pbb-man72-01.bcb.axione.fr" ou parfois avec des espaces/caractères parasites
                    fqdn_clean = fqdn_raw.split()[0] if ' ' in fqdn_raw else fqdn_raw
                    self._fqdn = fqdn_clean
                    print(f"✅ FQDN récupéré via SNMP: {self._fqdn}")
                    return self._fqdn
                else:
                    print(f"⚠️  Format de réponse SNMP inattendu: {result[:100]}")
            else:
                print(f"⚠️  Réponse SNMP vide")
        except Exception as e:
            print(f"❌ Erreur lors de la récupération du FQDN via SNMP: {e}")
        
        # Si SNMP échoue, utiliser le DNS complet trouvé
        if self.dns_complet:
            print(f"ℹ️  Utilisation du DNS complet comme FQDN: {self.dns_complet}")
            self._fqdn = self.dns_complet
            return self._fqdn
        
        return None

    def _query_prometheus_unified(self, hostname: str, max_retries: int = 20) -> Optional[List[Dict]]:
        """Exécute une seule requête Prometheus avec système de retry"""
        # Construction de la requête simplifiée (sans filtre ifName)
        query = f'ifMetrics_ifAdminStatus{{hostname=%22{hostname}%22}}'
        
        # Construire l'URL complète
        full_url = f"{self.PROMETHEUS_BASE_URL}?query={query}"
        
        # Headers similaires à Service.py
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Désactiver les proxies pour cette requête
        proxies = {
            'http': None,
            'https': None
        }
        
        print(f"🔍 Requête Prometheus:")
        print(f"   Hostname utilisé: {hostname}")
        print(f"   Query: {query}")
        print(f"   URL complète ({len(full_url)} caractères):")
        print(f"   {repr(full_url)}")
        print(f"   Headers: {headers}")
        print(f"   Proxies désactivés: {proxies}")
        print(f"🔄 Tentatives de récupération (max: {max_retries})...")
        print("=" * 60)
        
        for attempt in range(1, max_retries + 1):
            print(f"\n⏱️  TENTATIVE {attempt}/{max_retries}")
            print("-" * 60)
            
            try:
                print(f"📤 Envoi de la requête GET avec session (sans proxy)...")
                print(f"   URL: {full_url[:120]}{'...' if len(full_url) > 120 else ''}")
                
                # Mesurer le temps de la requête
                request_start = time.time()
                
                # Utiliser self.session avec proxies désactivés
                response = self.session.get(full_url, headers=headers, proxies=proxies, timeout=30)
                
                request_time = time.time() - request_start
                
                print(f"📥 Réponse reçue en {request_time:.2f}s")
                print(f"   Status HTTP: {response.status_code}")
                print(f"   Taille réponse: {len(response.content)} bytes")
                print(f"   URL effective: {response.url}")
                
                # Vérifier l'URL effective
                if response.url != full_url:
                    print(f"⚠️  URL redirigée vers: {response.url}")
                
                response.raise_for_status()
                
                print(f"🔍 Parsing JSON...")
                data = response.json()
                
                print(f"📊 Contenu JSON:")
                print(f"   Status: {data.get('status', 'N/A')}")
                
                if 'data' in data:
                    print(f"   Data présent: Oui")
                    if 'result' in data.get('data', {}):
                        result_count = len(data['data']['result'])
                        print(f"   Nombre de résultats: {result_count}")
                        
                        if result_count > 0:
                            print(f"   Premier résultat (aperçu):")
                            first_result = data['data']['result'][0]
                            print(f"      Metric: {first_result.get('metric', {}).get('ifName', 'N/A')}")
                            print(f"      Value: {first_result.get('value', ['N/A'])[1] if len(first_result.get('value', [])) > 1 else 'N/A'}")
                            
                            print(f"✅ SUCCÈS: {result_count} résultats récupérés")
                            return data['data']['result']
                        else:
                            print(f"⚠️  Résultat vide (0 interfaces trouvées)")
                    else:
                        print(f"   Result présent: Non")
                        print(f"   Contenu data: {data.get('data', {})}")
                else:
                    print(f"   Data présent: Non")
                    print(f"   Contenu complet: {data}")
                
                print(f"⏳ Aucune donnée exploitable, attente de 2s avant nouvelle tentative...")
                time.sleep(2)
                    
            except requests.exceptions.Timeout as e:
                print(f"❌ TIMEOUT après 30s")
                print(f"   Erreur: {str(e)}")
                print(f"   Type: {type(e).__name__}")
                print(f"⏳ Attente de 2s avant nouvelle tentative...")
                time.sleep(2)
                
            except requests.exceptions.HTTPError as e:
                print(f"❌ ERREUR HTTP")
                print(f"   Status code: {response.status_code}")
                print(f"   Raison: {response.reason}")
                print(f"   Erreur: {str(e)}")
                try:
                    error_data = response.json()
                    print(f"   Réponse JSON erreur: {error_data}")
                except:
                    print(f"   Réponse texte erreur: {response.text[:200]}")
                print(f"⏳ Attente de 2s avant nouvelle tentative...")
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ ERREUR REQUÊTE")
                print(f"   Type: {type(e).__name__}")
                print(f"   Erreur: {str(e)}")
                print(f"⏳ Attente de 2s avant nouvelle tentative...")
                time.sleep(2)
                
            except json.JSONDecodeError as e:
                print(f"❌ ERREUR PARSING JSON")
                print(f"   Erreur: {str(e)}")
                print(f"   Réponse brute (100 premiers caractères): {response.text[:100]}")
                print(f"⏳ Attente de 2s avant nouvelle tentative...")
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ ERREUR INATTENDUE")
                print(f"   Type: {type(e).__name__}")
                print(f"   Erreur: {str(e)}")
                import traceback
                print(f"   Traceback: {traceback.format_exc()[:300]}")
                print(f"⏳ Attente de 2s avant nouvelle tentative...")
                time.sleep(2)
        
        print("\n" + "=" * 60)
        print(f"❌ ÉCHEC DÉFINITIF après {max_retries} tentatives")
        print(f"   Basculement vers SNMP...")
        print("=" * 60)
        return None

    def _extract_bandwidth_from_ifname(self, ifname: str) -> str:
        """Extrait le débit depuis le nom de l'interface"""
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
        elif ifname.startswith("1/1/c") or ifname.startswith("1/1/x"):
            # Ports Nokia haute vitesse (ex: 1/1/c1/1)
            if "/c" in ifname:
                return "100G"
            elif "/x" in ifname:
                return "10G"
        
        # Huawei
        elif "XGigabitEthernet" in ifname or "XGE" in ifname:
            return "10G"
        elif "GE" in ifname and not "XGE" in ifname:
            return "1G"
        elif "40GE" in ifname:
            return "40G"
        elif "100GE" in ifname:
            return "100G"
        
        # Juniper
        elif "xe-" in ifname:
            return "10G"
        elif "et-" in ifname:
            return "40G" if "40g" in ifname.lower() else "100G"
        elif "ge-" in ifname:
            return "1G"
        
        # Patterns génériques basés sur des nombres
        elif "10g" in ifname.lower() or "10-gig" in ifname.lower():
            return "10G"
        elif "100g" in ifname.lower() or "100-gig" in ifname.lower():
            return "100G"
        elif "40g" in ifname.lower() or "40-gig" in ifname.lower():
            return "40G"
        elif "1g" in ifname.lower() or "1-gig" in ifname.lower():
            return "1G"
        
        return "Unknown"

    def _normalize_port_name(self, port_name: str, vendor: str = "Cisco") -> str:
        """Normalise un nom de port en fonction du vendor"""
        
        # Pour les équipements non-Cisco, retourner le port tel quel
        if vendor not in ["Cisco", "Unknown"]:
            return port_name
        
        # Normalisation Cisco uniquement
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
        
        # Ajouter 0/0/0/ uniquement si nécessaire pour Cisco
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
        
        print(f"📊 Analyse de {len(prometheus_results)} résultats Prometheus...")
        
        filtered_stats = {
            'total': len(prometheus_results),
            'down': 0,
            'optics': 0,
            'pbb_filter': 0,
            'target_filter': 0,
            'bandwidth_unknown': 0,
            'accepted': 0
        }
        
        for result in prometheus_results:
            metric = result.get('metric', {})
            value_array = result.get('value', [])
            
            # Récupération des données
            ifname = metric.get('ifName', '')
            ifalias = metric.get('ifAlias', '').strip('"')  # Retirer les guillemets pour Huawei/Nokia
            ifphysaddr = metric.get('ifPhysAddress', '')
            model = metric.get('model', 'Unknown')
            vendor = metric.get('vendor', 'Unknown')
            category = metric.get('category', 'Unknown')
            admin_status = value_array[1] if len(value_array) > 1 else '2'
            
            # Debug pour le premier port
            if filtered_stats['total'] == len(prometheus_results):
                print(f"\n🔍 Exemple de port analysé:")
                print(f"   ifName: {ifname}")
                print(f"   ifAlias: {ifalias}")
                print(f"   vendor: {vendor}")
                print(f"   category: {category}")
                print(f"   admin_status: {admin_status}")
            
            # Filtre 1: Si le port est down (2), on skip
            if admin_status == '2':
                filtered_stats['down'] += 1
                continue
            
            # Filtre 2: Si c'est un Optics dans la description, on skip
            if 'optics' in ifalias.lower():
                filtered_stats['optics'] += 1
                continue
            
            # Filtre 3: Pour les équipements PBB (Cisco), vérifier si c'est bien une interface 0/0/0
            # Pour les autres, pas de filtre spécifique sur le format du port
            if category == "PBB" and '0/0/0' not in ifname:
                filtered_stats['pbb_filter'] += 1
                continue
            
            # Normalisation du port en fonction du vendor
            port_number = self._normalize_port_name(ifname, vendor)
            
            # Filtrage par port cible si spécifié
            if target_port:
                if self.slot and port_number != target_port:
                    filtered_stats['target_filter'] += 1
                    continue
                elif not self.slot and not port_number.startswith(target_port):
                    filtered_stats['target_filter'] += 1
                    continue
            
            # Détermination du débit
            bandwidth = self._extract_bandwidth_from_ifname(ifname)
            
            # Si bandwidth Unknown, afficher un warning mais accepter quand même le port
            if bandwidth == "Unknown":
                print(f"⚠️  Bandwidth inconnu pour: {ifname} (vendor: {vendor})")
                # Ne pas skip, juste mettre "Unknown"
                # filtered_stats['bandwidth_unknown'] += 1
                # continue
            
            # Informations bundle (principalement pour Cisco/PBB)
            bundle_info = self._get_port_bundle_info(port_number, bundle_data)
            
            # Construction de la description avec le débit
            description = f"{ifname} ({bandwidth})"
            
            # Statut (1 = up)
            status = "up"
            
            port_info = {
                "port": port_number,
                "description": description,
                "model": model,
                "vendor": vendor,
                "category": category,
                "alias": ifalias,
                "status": status,
                "admin_status": status,
                "physical_address": ifphysaddr,
                "bandwidth": bandwidth
            }
            
            # Ajouter les infos bundle uniquement si disponibles
            if bundle_info["bundle"] != "N/A" and bundle_info["status_bundle"].lower() in ["up", "active"]:
                port_info.update({
                    "bundle": bundle_info["bundle"],
                    "status_bundle": bundle_info["status_bundle"],
                    "state": bundle_info["state"]
                })
            
            ports_info_temp.append(port_info)
            ports_up.append(port_number)
            filtered_stats['accepted'] += 1
        
        # Afficher les statistiques de filtrage
        print(f"\n📊 Statistiques de filtrage:")
        print(f"   Total interfaces: {filtered_stats['total']}")
        print(f"   ❌ Down (status=2): {filtered_stats['down']}")
        print(f"   ❌ Optics: {filtered_stats['optics']}")
        print(f"   ❌ PBB sans 0/0/0: {filtered_stats['pbb_filter']}")
        print(f"   ❌ Filtrage port cible: {filtered_stats['target_filter']}")
        print(f"   ⚠️  Bandwidth inconnu: {filtered_stats['bandwidth_unknown']}")
        print(f"   ✅ Acceptés: {filtered_stats['accepted']}")
        
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
        
        # Récupération du modèle et vendor depuis le premier port (ils ont tous le même)
        if ports_info_temp:
            equipment_model = ports_info_temp[0].get('model', 'Unknown')
            equipment_vendor = ports_info_temp[0].get('vendor', 'Unknown')
            equipment_category = ports_info_temp[0].get('category', 'Unknown')
            
            info["equipment_info"]["type"] = equipment_model
            info["equipment_info"]["vendor"] = equipment_vendor
            info["equipment_info"]["category"] = equipment_category
            
            print(f"✅ Modèle d'équipement: {equipment_model}")
            print(f"✅ Vendor: {equipment_vendor}")
            print(f"✅ Catégorie: {equipment_category}")
        
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