import requests
import json
import re
from typing import Dict, Any
import urllib3

# Import de NetworkEquipment pour exécuter les commandes SNMP/SSH
from scripts.PBB.ClassPBBWeb import *
from scripts.Nokia.scriptNokiaPrincipal import ScriptNokiaPrincipal

# Désactiver les warnings SSL pour les certificats auto-signés
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ServiceEquipmentFetcher:
    def __init__(self, base_url: str = 'https://ws-ords.m2m.axione.fr'):
        self.base_url = base_url
        self.referer = base_url
        self.session = requests.Session()
        self.session.verify = False  # Désactiver la vérification SSL
    
    def get_status_from_page(self, page_url: str) -> str:
        """Récupère le statut depuis la page web"""
        try:
            headers = {
                'Referer': self.referer,
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            response = self.session.get(page_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Chercher le statut sélectionné dans le dropdown
            pattern = r'<option[^>]*selected[^>]*>([^<]+)</option>'
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            
            valid_statuses = ['Annulée', 'Créée', 'En attente d\'éléments', 'En service', 'Rejetée', 'Résiliée', 'Suspendue', 'Validée']
            for match in matches:
                if match.strip() in valid_statuses:
                    return match.strip()
            
            return "En service"  # Fallback
        except:
            return "En service"  # Fallback en cas d'erreur
        
    def get_equipment_by_service_id(self, service_id: str, page_url: str = None) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/ordscomxdsl/pwksrefpro/ref_sp?who={service_id}"
            headers = {
                'Referer': self.referer,
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }

            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data or not data.get('items'):
                return {
                    'Statut': 'Service non trouvé',
                    'message': f'Aucun équipement trouvé pour le service ID: {service_id}',
                    'service_id': service_id,
                    'equipment_count': 0,
                    'equipments': []
                }
            
            # Récupérer le statut depuis la page web si URL fournie, sinon depuis l'API
            if page_url:
                service_status = self.get_status_from_page(page_url)
            else:
                service_status = "En service"
                if data.get('items') and len(data['items']) > 0:
                    first_item = data['items'][0]
                    if 'statut' in first_item:
                        service_status = first_item['statut']
            
            # Extraction données equip du service
            equipments = []
            for item in data['items']:
                hostname = item.get('equipement', 'N/A')
                port = item.get('port', 'N/A')
                
                equipment_info = {
                    'hostname': hostname,
                    'port': port
                }
                
                # Si hostname et port valides, exécuter ClassPBBWeb
                if hostname != 'N/A' and port != 'N/A':
                    try:
                        # Déterminer si c'est un équipement WDM ou PBB
                        if hostname.startswith('wdm-'):
                            # Pour les équipements WDM, exécuter ScriptNokiaPrincipal
                            try:
                                wdm_result = ScriptNokiaPrincipal(hostname)
                                equipment_info['resultat_script'] = wdm_result
                            except Exception as wdm_error:
                                equipment_info['resultat_script'] = {
                                    'error': f"Erreur ScriptNokiaPrincipal: {str(wdm_error)}",
                                    'status': 'failed',
                                    'type': 'WDM'
                                }
                        else:
                            # Pour les équipements PBB, extraire IP
                            ip = None
                            slot = None
                            
                            # Analyser le format du port (ex: 0/0/0/20)
                            if '/' in port:
                                port_parts = port.split('/')
                                if len(port_parts) >= 4:
                                    # Format type: 0/0/0/20
                                    ip = '/'.join(port_parts[:4])
                                    if len(port_parts) > 4:
                                        slot = port_parts[4]
                                else:
                                    ip = port
                            else:
                                ip = port
                            
                            # Instance et récupération des infos
                            network_equipment = NetworkEquipment(hostname, ip=ip, slot=slot)
                            equipment_details = network_equipment.get_equipment_info()
                            
                            equipment_result = {
                                'ip_address': equipment_details['equipment_info'].get('ip_address', 'N/A'),
                                'dns_complet': equipment_details['equipment_info'].get('dns_complet', 'N/A'),
                                'type': equipment_details['equipment_info'].get('type', 'N/A'),
                                'Version': equipment_details['equipment_info'].get('Version', 'N/A')
                            }
                            
                            # Ajout des info des ports
                            ports_info = []
                            for port_detail in equipment_details.get('ports', []):
                                # Ne garder que le port correspondant
                                if port_detail['port'] == ip or (slot and port_detail['port'] == f"{ip}/{slot}"):
                                    ports_info.append(port_detail)
                            
                            equipment_result['ports'] = ports_info
                            equipment_info['resultat_script'] = equipment_result
                            
                    except Exception as e:
                        equipment_info['resultat_script'] = {
                            'error': f"Erreur lors de la récupération des détails: {str(e)}",
                            'status': 'failed'
                        }
                else:
                    equipment_info['resultat_script'] = {
                        'error': 'Hostname ou port invalide',
                        'status': 'skipped'
                    }
                
                equipments.append(equipment_info)
            
            result = {
                'Statut': service_status,
                'service_id': service_id,
                'equipment_count': len(equipments),
                'equipments': equipments
            }

            return result
            
        except requests.exceptions.RequestException as e:
            return {
                'Statut': 'Erreur de connexion',
                'message': f"Erreur de requête HTTP: {str(e)}",
                'service_id': service_id,
                'equipment_count': 0,
                'equipments': [],
                'error_type': 'RequestException'
            }
            
        except json.JSONDecodeError as e:
            return {
                'Statut': 'Erreur de données',
                'message': f"Erreur de parsing JSON: {str(e)}",
                'service_id': service_id,
                'equipment_count': 0,
                'equipments': [],
                'error_type': 'JSONDecodeError'
            }
            
        except Exception as e:
            return {
                'Statut': 'Erreur inconnue',
                'message': f"Erreur inattendue: {str(e)}",
                'service_id': service_id,
                'equipment_count': 0,
                'equipments': [],
                'error_type': 'UnexpectedException'
            }
    
    def close(self):
        """Ferme la session"""
        if hasattr(self, 'session'):
            self.session.close()