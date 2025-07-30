# -*- coding: utf-8 -*-

# 
# @file		SpectrumPBB.py
#

# LIBRAIRIES
import socket, sys, subprocess, json, re
from scripts.GetIp import *
from scripts.FindDNS import *
from scripts.AddCheckTools import *
from scripts.Ping import *

# METHODES

# Faire les recherches génériques pour les équipements PBB Cisco
# @param: str
# @return: json
def PBB(pbb_name):
    result = {}

    pbb_dns = find_dns(pbb_name)

    if re.match('.*\.\w+\.axione\.fr', pbb_dns):
        pbb_ip = get_ip(pbb_dns)

        if re.match('\d+\.\d+\.\d+\.\d+', pbb_ip):
            result = {
                'dns': pbb_dns,
                'ip': pbb_ip,
                'ping': ping(pbb_dns)
            }

            # Vérification et ajout dans Spectrum avec la communauté 'cpdea'
            pbb_spectrum = DeviceInSpectrum(pbb_name, 'cpdea')
            if re.search(r'absent de Spectrum', pbb_spectrum['spectrum']):
                AddInSpectrum(pbb_ip, pbb_name, 'cpdea')
                # Re-vérifier après ajout
                result.update(DeviceInSpectrum(pbb_name, 'cpdea'))
            else:
                result.update(pbb_spectrum)

            # Vérification et ajout dans Cacti
            # Pour les équipements Cisco, on utilise généralement le type 'CISCO'
            cacti_result, device_id = DeviceInCacti(pbb_name, pbb_ip, 'CISCO')
            result.update(cacti_result)

            # Si l'équipement n'est pas dans Cacti, on peut essayer de l'ajouter
            if re.search(r"n'est pas dans cacti", cacti_result.get('cacti', '')):
                try:
                    # Paramètres pour l'ajout dans Cacti pour un équipement Cisco
                    # template=10 correspond généralement au template Cisco dans Cacti
                    add_result = AddInCacti(pbb_name, pbb_ip, template=10, avail=1, version=2, community='cpdea', id=0)
                    if add_result:
                        result.update(add_result)
                except Exception as e:
                    result['cacti_add_error'] = f"Erreur lors de l'ajout dans Cacti: {str(e)}"

        else:
            return { 'error': f'IP non conforme pour {pbb_name}' }
    else:
        return { 'error': f'DNS non conforme pour {pbb_name}' }

    return result

# Fonction spécifique pour récupérer uniquement les infos Spectrum et Cacti
# @param: str
# @return: dict
def get_pbb_monitoring_info(pbb_name):
    """
    Récupère uniquement les informations de monitoring (Spectrum et Cacti) 
    pour un équipement PBB
    """
    try:
        pbb_dns = find_dns(pbb_name)
        
        if not re.match('.*\.\w+\.axione\.fr', pbb_dns):
            return {
                'spectrum': f'DNS non conforme pour {pbb_name}',
                'cacti': f'DNS non conforme pour {pbb_name}'
            }

        pbb_ip = get_ip(pbb_dns)
        
        if not re.match('\d+\.\d+\.\d+\.\d+', pbb_ip):
            return {
                'spectrum': f'IP non conforme pour {pbb_name}',
                'cacti': f'IP non conforme pour {pbb_name}'
            }

        result = {}

        # Vérification dans Spectrum
        try:
            pbb_spectrum = DeviceInSpectrum(pbb_name, 'cpdea')
            result.update(pbb_spectrum)
            
            # Si absent de Spectrum, essayer de l'ajouter
            if re.search(r'absent de Spectrum', pbb_spectrum.get('spectrum', '')):
                add_spectrum_result = AddInSpectrum(pbb_ip, pbb_name, 'cpdea')
                if add_spectrum_result:
                    result.update(add_spectrum_result)
                # Re-vérifier après tentative d'ajout
                result.update(DeviceInSpectrum(pbb_name, 'cpdea'))
        except Exception as e:
            result['spectrum'] = f'Erreur Spectrum: {str(e)}'

        # Vérification dans Cacti
        try:
            cacti_result, device_id = DeviceInCacti(pbb_name, pbb_ip, 'CISCO')
            result.update(cacti_result)
        except Exception as e:
            result['cacti'] = f'Erreur Cacti: {str(e)}'

        return result

    except Exception as e:
        return {
            'spectrum': f'Erreur générale Spectrum: {str(e)}',
            'cacti': f'Erreur générale Cacti: {str(e)}'
        }