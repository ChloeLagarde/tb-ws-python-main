# -*- coding: utf-8 -*-

# 
# @file		OLT.py
#

# LIBRAIRIES
import socket, sys, subprocess, json, re
from scripts.GetIp import *
from scripts.FindDNS import *
from scripts.Version_Alcatel_Telco_One_Access import *
from scripts.AddCheckTools import *
from scripts.SSH import *
from scripts.Ping import *
from scripts.OLT.WholesaleEssonne import *

# METHODES

# Faire les recherches génériques
# @param: str
# @return: json
def OLT(olt_name):
    result = []

    olt_dns = find_dns(olt_name)

    if re.match('.*\.\w+\.axione\.fr', olt_dns):
        olt_ip = get_ip(olt_dns)

        if re.match('\d+\.\d+\.\d+\.\d+', olt_ip):
            olt_type = version_alcatel_telco_one_access(olt_dns)

            result = {
                'dns': olt_dns,
                'ip': olt_ip,
                'type': olt_type['equipment type'],
                'version': olt_type['equipment version'],
                'ping': ping(olt_dns)
            }

            olt_spectrum = DeviceInSpectrum(olt_name, 'cpdea')
            if re.search(r'absent de Spectrum', olt_spectrum['spectrum']):
                AddInSpectrum(olt_ip, olt_name, 'cpdea')
            #
            result.update(DeviceInSpectrum(olt_name, 'cpdea'))
            #result.update(DeviceInNetbox(olt_name, olt_ip, olt_type['equipment model']))
            result.update(DeviceInCacti(olt_name, olt_ip, olt_type)[0])

            if olt_type['equipment type'] == '7360':
                olt_spectrum = DeviceInSpectrum(olt_name, 'ihub')
                if re.search(r'absent de Spectrum', olt_spectrum['spectrum ihub']):
                    AddInSpectrum(olt_ip, olt_name, 'ihub')
                #
                result.update(DeviceInSpectrum(olt_name, 'ihub'))
                result.update(GetOLTNokiaInfo(olt_name))
            elif olt_type['equipment type'] == 'MA5800':
                result.update(GetOLTHuaweiInfo(olt_name))
            else:
                return { 'error': f'Type inconnu pour {olt_name}' }
            #

            if re.search(r'enu\.axione\.fr', olt_dns):
                result.update(WholesaleEssonne(olt_name))
            #
        else:
            return { 'error': f'IP non conforme pour {olt_name}' }
        #
    else:
        return { 'error': f'DNS non conforme pour {olt_name}' }
    #

    return result
#

# Faire les recherches Nokia détaillées
# @param: str
# @return: json
def GetOLTNokiaInfo(olt_name):
    results = []
    cmds = [
        'info configure system | match exact:system-mac',
        'show equipment slot',
        'show service id 1090 base',
        'show router static-route',
        'show equipment protection-element',
        'show port nt-a:xfp:1',
        'show port nt-b:xfp:1',
        'show lag 1 description',
        'show equipment diagnostics sfp nt-a:xfp:1 detail',
        'show equipment diagnostics sfp nt-b:xfp:1 detail',
        'show equipment transceiver-inventory nt-a:xfp:1 detail',
        'show equipment transceiver-inventory nt-b:xfp:1 detail',
    ]

    results = {
        'ssh': ssh(olt_name, cmds)
    }

    results['ssh']['info configure system | match exact:system-mac'] = results['ssh']['info configure system | match exact:system-mac'].split('/')[1]
    
    results['edgs'] = {}
    lag_desc_raw = results['ssh'].get('show lag 1 description', '')
    lag_desc = lag_desc_raw.replace('\r', '').replace('\n', ' ').replace(' ', '')
    edgs = re.search(r'LAGvers(\w+\-\w+\d+\-\d+)et(\w+\-\w+\d+\-\d+)nt-a', lag_desc, re.IGNORECASE)
    if edgs:
        edg1 = edgs.group(1).strip()
        edg2 = edgs.group(2).strip()
        results['edgs'][edg1] = GetEDGInfoByOLT(edg1, olt_name)
        results['edgs'][edg2] = GetEDGInfoByOLT(edg2, olt_name)
    #

    return results
#

# Faire les recherches Huawei détaillées
# @param: str
# @return: json
def GetOLTHuaweiInfo(olt_name):
    results = []
    return results
#

# Faire les recherches Nokia EDG
# @param: str
# @return: json
def GetEDGInfoByOLT(edg_name, olt_name):
    results = []
    
    port_output = ssh(edg_name, [f'show port description | match {olt_name}'])[f'show port description | match {olt_name}']
    match = re.search(r'(\d+/\d+/\d+)', port_output)
    port = match.group(1) if match else None

    if port:
        cmds = [
            f'show port {port}',
        ]

        results = {
            'ssh': ssh(edg_name, cmds)
        }
    #

    return results
#

# Chercher les configs Wholesale ENU
# @param: str
# @return: json
def WholesaleEssonne(olt_name):
    return {
        'configs': generate_config_wholesale_enu(olt_name)
    }
#