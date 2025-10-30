import re
from scripts.SnmpRequests import snmp_request, snmp_request_public, snmp_request_cpdeacpdea

# Liste de dictionnaires contenant les expressions régulières et les informations des équipements
equipment_patterns = [
    {"pattern": r'TiMOS-(\w+-\d+\.\d+\.\w+).*ALCATEL SAS-X', "type": "7210-SASX", "model": "ALCATEL SAS-X", "version_group": 1},
    {"pattern": r'TiMOS-(\w+-\d+\.\d+\.\w+).*Nokia 7250', "type": "7250", "model": "Nokia 7250", "version_group": 1},
    {"pattern": r'TiMOS-(\w+-\d+\.\d+\.\w+).*ALCATEL SAS-M', "type": "7210", "model": "ALCATEL SAS-M", "version_group": 1},
    {"pattern": r'TiMOS-(\w+-\d+\.\d+\.\w+).*Nokia SAS-Mxp', "type": "7210", "model": "Nokia SAS-Mxp", "version_group": 1},
    {"pattern": r'TiMOS-(\w+-\d+\.\d+\.\w+).*ALCATEL ESS 7450', "type": "7450", "model": "ALCATEL ESS 7450", "version_group": 1},
    {"pattern": r'TiMOS-(\w+-\d+\.\d+\.\w+).*ALCATEL SR 7750', "type": "7750", "model": "ALCATEL SR 7750", "version_group": 1},
    {"pattern": r'TiMOS-(\w+-\d+\.\d+\.\w+).*Nokia 7750', "type": "7750", "model": "NOKIA 7750", "version_group": 1},
    {"pattern": r'STRING: \"(R.*) NFXS-\w{1} FANT', "type": "7360", "model": "Unknown", "version_group": 1},
    {"pattern": r'HUAWEI (NE20.*-.*)', "type": "NE20", "model": "HUAWEI", "version_group": 1},
    {"pattern": r'HUAWEI (NE40.*-.*-.*)', "type": "NE40", "model": "HUAWEI", "version_group": 1},
    {"pattern": r'(8000 M1A) (\S+)', "type": "NE8000 M1A", "model": "Unknown", "version_group": 2},
    {"pattern": r'(8000 M1C) (\S+)', "type": "NE8000 M1C", "model": "Unknown", "version_group": 2},
    {"pattern": r'JUNOS (.*), Build', "type": "JUNOS", "model": "Unknown", "version_group": 1},
    {"pattern": r'STRING: T5C 24G Routing Switch software version\s+(\d+\.\d+\.\w+)', "type": "T5C", "model": "Unknown", "version_group": 1},
    {"pattern": r'T-Marc 380 Switch.*?(\d+\.\d+\.\w+)', "type": "T380", "model": "Unknown", "version_group": 1},
    {"pattern": r'T-Marc 280 Switch.*?(\d+\.\d+\.\w+)', "type": "T280", "model": "Unknown", "version_group": 1},
    {"pattern": r'(SHDSL-\d+P) 2ETH-4P HWA RTC 64M (T\d+/\d+)', "type": "SHDSL", "model": "2ETH-4P HWA RTC 64M", "version_group": 2},
    {"pattern": r'(SHDSL-\d+P) 2ETH-4P HWA RTC 64M\s+(no flash active)', "type": "SHDSL", "model": "2ETH-4P HWA RTC 64M", "version_group": 2},
    {"pattern": r'GE112', "type": "ADVA", "model": "GE112", "version_oid": ".1.3.6.1.2.1.47.1.1.1.1.10.1"},
    {"pattern": r'GE104', "type": "ADVA", "model": "GE104", "version_oid": ".1.3.6.1.2.1.47.1.1.1.1.10.1"},
    {"pattern": r'GE114', "type": "ADVA", "model": "GE114", "version_oid": ".1.3.6.1.2.1.47.1.1.1.1.10.1"},
    {"pattern": r'GE206V', "type": "ADVA", "model": "GE206V", "version_oid": ".1.3.6.1.2.1.47.1.1.1.1.10.1"},
    {"pattern": r'XG210', "type": "ADVA", "model": "XG210", "version_oid": ".1.3.6.1.2.1.47.1.1.1.1.10.1"},
    {"pattern": r'Cisco IOS Software.*ASR', "type": "CISCO_ASR", "model": "Cisco IOS Software", "version_group": 1},
    {"pattern": r'Cisco IOS Software', "type": "CISCO", "model": "Cisco IOS Software", "version_group": 1},
    {"pattern": r'HUAWEI NE05', "type": "NE05", "model": "HUAWEI NE05", "version_oid": ".1.3.6.1.4.1.2011.5.25.19.1.4.2.1.5.1"},
    {"pattern": r'Huawei Versatile Routing Platform Software', "type": "HUAWEI_SWITCH", "model": "HUAWEI_SWITCH"},
    {"pattern": r'ALCATEL SAS-X', "type": "7210-SASX", "model": "7210 SAS-X 24F 2XFP-1"},
    {"pattern": r'ALCATEL SAS-M', "type": "7210", "model": None},
    {"pattern": r'Nokia SAS-Mxp', "type": "7210", "model": "7210 SAS-Mxp 22F2C 4SFP+ ETR-1"},
    {"pattern": r'ALCATEL ESS 7450', "type": "7x50", "model": "7450 ESS-1"},
    {"pattern": r'ALCATEL SR 7750', "type": "7x50", "model": None},
    {"pattern": r'Nokia 7750', "type": "7x50", "model": None},
    {"pattern": r'(\w+\d+) internet router, kernel JUNOS (.*), Build', "type": "JUNOS", "model": "Unknown", "version_group": 2},
    {"pattern": r'STRING: T5C 24G', "type": "T5C", "model": "T5CL3-24G"},
    {"pattern": r'STRING: T-Marc 380 Switch software version\s+(\d+\.\d+\.\w+\.\d+)', "type": "T380", "model": "Unknown", "version_group": 1},
    {"pattern": r'T-Marc 380 Switch Product Category : AccessEthernet\(TM\)  software version\s+(\d+\.\d+\.\w+)', "type": "T380", "model": "Unknown", "version_group": 1},
    {"pattern": r'T-Marc 280 Switch Product Category : AccessEthernet\(TM\)  software version (\d+\.\d+\.\w+)', "type": "T280", "model": "T-Marc 280", "version_group": 1},
    {"pattern": r'Cisco IOS XR Software', "type": "CISCO", "model": "Unknown"},
    {"pattern": r'MA5600', "type": "MA5600", "model": "Unknown"},
    {"pattern": r'Ciena', "type": "CIENA", "model": "Unknown"},
    {"pattern": r'Ekinops 360', "type": "EKINOPS", "model": "Unknown"},
    {"pattern": r'Nokia 1830', "type": "NOKIA PSS", "model": "Unknown"},
    {"pattern": r'Cisco IOS XR Software \(8000\)', "type": "CISCO", "model": "Cisco 8201"}
]

def version_alcatel_telco_one_access(host):
    output = snmp_request(host, '1.3.6.1.2.1.1.1.0')
    equipment_info = {
        'equipment type': "",
        'equipment model': "",
        'equipment version': "Unknown",
        'cpdea_community': False
    }

    # Parcourir les patterns pour trouver une correspondance
    for pattern_info in equipment_patterns:
        match = re.search(pattern_info["pattern"], str(output))
        if match:
            equipment_info['equipment type'] = pattern_info.get("type", "")
            equipment_info['equipment model'] = pattern_info.get("model", "")
            
            # Obtenir la version soit par groupe de capture soit par OID
            version_group = pattern_info.get("version_group")
            version_oid = pattern_info.get("version_oid")
            if version_group and match.group(version_group):
                equipment_info['equipment version'] = match.group(version_group)
            elif version_oid:
                version_output = snmp_request(host, version_oid)
                version_match = re.search(r'STRING: \"(\S+)\"', str(version_output))
                if version_match:
                    equipment_info['equipment version'] = version_match.group(1).replace('\\n', '')
            break

    # Si pas de correspondance trouvée, vérifier la communauté CPDEA
    if not equipment_info['equipment type']:
        output = snmp_request_cpdeacpdea(host, "iso.3.6.1.2.1.1.1.0")
        if re.search("Huawei Integrated Access Software", str(output)):
            equipment_info.update({
                'equipment type': "MA5800",
                'equipment model': "HUAWEI MA5800",
                'equipment version': "Unknown"
            })
        elif re.search(r'Huawei Versatile Routing Platform Software', str(output)):
            equipment_info.update({
                'equipment type': "HUAWEI_SWITCH",
                'equipment model': "HUAWEI_SWITCH",
                'equipment version': "Unknown",
                'cpdea_community': True
            })

    return equipment_info