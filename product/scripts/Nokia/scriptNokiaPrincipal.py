import socket
# import sys
import subprocess
import requests
import json
from scripts.GetIp import get_ip
from scripts.FindDNS import find_dns
from scripts.Nokia.ClassNokia import *

def IsNokia(equipment_name):
    dns = find_dns(equipment_name)
    commandIsNokia = subprocess.check_output(f"snmpget -v2c -c cpdea {dns} 1.3.6.1.2.1.1.1.0", shell=True)
    testNokia = commandIsNokia.decode('utf-8').strip()
    if "Nokia" in testNokia:
        return True
    else :
        return False

def ScriptNokiaPrincipal(equipment_name):
    result = []
    
    # Récupération de l'adresse IP et du DNS de l'équipement
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)

    # Construction des données pour chaque carte
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }

        # Ajout des données spécifiques en fonction du type de carte
        if "RA2P" in card_name:
            ra2p = RA2P(card_shelf, card_slot, ip_address)
            card_data.update({
                "Total Input Power": ra2p[0],
                "Total Output Power": ra2p[1],
                "Current Gain": ra2p[2],
                "Temperature": ra2p[3],
                "Measured Current": ra2p[4],
                "Measured Power": ra2p[5]
            })
        elif "AAR-8A" in card_name:
            aar8a = AAR8A(card_shelf, card_slot, ip_address)
            card_data.update({
                "Total Input Power": aar8a[0],
                "Index Total Output Power": aar8a[1],
                "Index Temperature": aar8a[2]
            })
        elif "EC" in card_name:
            controller = ControllerCards(card_shelf, card_slot, ip_address)
            card_data.update({
                "Temperature": controller[0],
                "Measured Current": controller[1],
                "Measured Power": controller[2]
            })
        elif "MCS8-16" in card_name or "USRPNL" in card_name or "SHFPNL" in card_name or "PF" in card_name:
            autre = Autre(card_shelf, card_slot, ip_address)
            card_data.update({
                "Temperature": autre[0]
            })

        result.append(card_data)

    return result

def ScriptNokiaSecond(equipment_name):
    result = []
    
    # Récupération de l'adresse IP et du DNS de l'équipement
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }

        
        if any(card_name in name for name in ["11dPM12", "11QPA4B", "16P200", "130SCX", "8p20", "S4X400H", "S5AD400H", "S6AD600H", "S13X100R"]):
            transponders = opticalTransponders(card_shelf, card_slot, ip_address)
            card_data.update({"Receive Power ": transponders[0],
                        "Transmit Power ": transponders[1],
                        "Traffic Tx ": transponders[2],
                        "Traffic Rx ": transponders[3],
                        "Tx CRC ": transponders[4],
                        "Rx CRC ": transponders[5],
                        "Temperature": transponders[6],
                        "Measured Current": transponders[7],
                        "Measured Power ": transponders[8]})
            
        elif "AHPLG" in card_name or "AHPHG" in card_name or "AM2032A" in card_name or "AM2625A" in card_name:
            amplifiersGeneral = opticalAmplifiersGeneral(card_shelf, card_slot, ip_address)
            card_data.update({"Total Input Power": amplifiersGeneral[0],
                            "Total Output Power": amplifiersGeneral[1],
                            "Current Gain": amplifiersGeneral[2],
                            "Temperature": amplifiersGeneral[3],
                            "Measured Current": amplifiersGeneral[4],
                            "Measured Power": amplifiersGeneral[5]})
            
        elif "ASG" in card_name or "ASGLP " in card_name or "ASWG" in card_name:
            amplifiersAsg = opticalAmplifiersForAs(card_shelf, card_slot, ip_address)
            card_data.update({"Total Input Power": amplifiersAsg[0],
                            "Total Output Power": amplifiersAsg[1],
                            "Current Gain": amplifiersAsg[2],
                            "Temperature": amplifiersAsg[3],
                            "Measured Current": amplifiersAsg[4],
                            "Measured Power": amplifiersAsg[5],
                            "Channel Power In": amplifiersAsg[6],
                            "Channel Power Out": amplifiersAsg[7],
                            "OSCsfp Power Out": amplifiersAsg[8],
                            "OSCsfp Power In": amplifiersAsg[9]})
            
        elif "ROADM9R" in card_name or "IRDM20" in card_name :
            wavelength = wavelengthRouter(card_shelf, card_slot, ip_address)
            card_data.update({
                            "Total Input Power": wavelength[0],
                            "Total Output Power": wavelength[1],
                            "Current Gain": wavelength[2],
                            "Temperature": wavelength[3],
                            "Measured Current": wavelength[4],
                            "Measured Power": wavelength[5],
                            "Channel Power In": wavelength[6],
                            "Channel Power Out": wavelength[7],
                            "OSCsfp Power Out": wavelength[8],
                            "OSCsfp Power In": wavelength[9]
            })
            
        elif "RA2P" in card_name:
            ra2p = RA2P(card_shelf, card_slot, ip_address) 
            card_data.update({
                "Total Input Power": ra2p[0],
                "Total Output Power": ra2p[1],
                "Current Gain": ra2p[2],
                "Temperature": ra2p[3],
                "Measured Current": ra2p[4],
                "Measured Power": ra2p[5]
            })
        elif "AAR-8A" in card_name:
            aar8a = AAR8A(card_shelf, card_slot, ip_address)
            card_data.update({
                "Total Input Power": aar8a[0],
                "Index Total Output Power": aar8a[1],
                "Index Temperature": aar8a[2]
            })
        elif "EC" in card_name:
            controller = ControllerCards(card_shelf, card_slot, ip_address)
            card_data.update({
                "Temperature": controller[0],
                "Measured Current": controller[1],
                "Measured Power": controller[2]
            })
        elif "MCS8-16" in card_name or "USRPNL" in card_name or "SHFPNL" in card_name or "PF" in card_name:
            autre = Autre(card_shelf, card_slot, ip_address)
            card_data.update({
                "Temperature": autre[0]
            })
        else:
            card_data = {
                'Type de carte': card_name,
                'Slot': card_slot
            }

        result.append(card_data)

    return result

def ScriptTransponders(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if any(card_name in name for name in ["11dPM12", "11QPA4B", "16P200", "130SCX", "8p20", "S4X400H", "S5AD400H", "S6AD600H", "S13X100R"]):
            transponders = opticalTransponders(card_shelf, card_slot, ip_address)
            card_data.update({"Receive Power": transponders[0],
                        "Transmit Power": transponders[1],
                        "Traffic Tx": transponders[2],
                        "Traffic Rx": transponders[3],
                        "Tx CRC": transponders[4],
                        "Rx CRC": transponders[5],
                        "Temperature": transponders[6],
                        "Measured Current": transponders[7],
                        "Measured Power": transponders[8]})
        else:
            card_data = {
                'Type de carte': card_name,
                'Slot': card_slot
            }
        result.append(card_data)
    return result

def ScriptAmplifiersGeneral(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if "AHPLG" in card_name or "AHPHG" in card_name or "AM2032A" in card_name or "AM2625A" in card_name:
            amplifiersGeneral = opticalAmplifiersGeneral(card_shelf, card_slot, ip_address)
            card_data.update({"Total Input Power": amplifiersGeneral[0],
                            "Total Output Power": amplifiersGeneral[1],
                            "Current Gain": amplifiersGeneral[2],
                            "Temperature": amplifiersGeneral[3],
                            "Measured Current": amplifiersGeneral[4],
                            "Measured Power": amplifiersGeneral[5]})
        else: 
            card_data = {
                    'Type de carte': card_name,
                    'Slot': card_slot
                }
        result.append(card_data)
    return result

def ScriptAmplifiersForAs(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if "ASG" in card_name or "ASGLP " in card_name or "ASWG" in card_name:
            amplifiersAsg = opticalAmplifiersForAs(card_shelf, card_slot, ip_address)
            card_data.update({"Total Input Power": amplifiersAsg[0],
                            "Total Output Power": amplifiersAsg[1],
                            "Current Gain": amplifiersAsg[2],
                            "Temperature": amplifiersAsg[3],
                            "Measured Current": amplifiersAsg[4],
                            "Measured Power": amplifiersAsg[5],
                            "Channel Power In": amplifiersAsg[6],
                            "Channel Power Out": amplifiersAsg[7],
                            "OSCsfp Power Out": amplifiersAsg[8],
                            "OSCsfp Power In": amplifiersAsg[9]})
        else: 
            card_data = {
                    'Type de carte': card_name,
                    'Slot': card_slot
                }
        result.append(card_data)
    return result

def ScriptWavelengthRouter(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if "ROADM9R" in card_name or "IRDM20" in card_name :
            wavelength = wavelengthRouter(card_shelf, card_slot, ip_address)
            card_data.update({
                            "Total Input Power": wavelength[0],
                            "Total Output Power": wavelength[1],
                            "Current Gain": wavelength[2],
                            "Temperature": wavelength[3],
                            "Measured Current": wavelength[4],
                            "Measured Power": wavelength[5],
                            "Channel Power In": wavelength[6],
                            "Channel Power Out": wavelength[7],
                            "OSCsfp Power Out": wavelength[8],
                            "OSCsfp Power In": wavelength[9]
            })
        else: 
            card_data = {
                    'Type de carte': card_name,
                    'Slot': card_slot
                }
        result.append(card_data)
    return result

def ScriptRA2P(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if "RA2P" in card_name:
            ra2p = RA2P(card_shelf, card_slot, ip_address) 
            card_data.update({
                "Total Input Power": ra2p[0],
                "Total Output Power": ra2p[1],
                "Current Gain": ra2p[2],
                "Temperature": ra2p[3],
                "Measured Current": ra2p[4],
                "Measured Power": ra2p[5]
            })
        else: 
            card_data = {
                    'Type de carte': card_name,
                    'Slot': card_slot
                }
        result.append(card_data)
    return result

def ScriptAAR8A(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if "AAR-8A" in card_name:
            aar8a = AAR8A(card_shelf, card_slot, ip_address)
            card_data.update({
                "Total Input Power": aar8a[0],
                "Total Output Power": aar8a[1],
                "Temperature": aar8a[2]
            })
        else: 
            card_data = {
                    'Type de carte': card_name,
                    'Slot': card_slot
                }
        result.append(card_data)
    return result

def ScriptControllerCards(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if "EC" in card_name:
            controller = ControllerCards(card_shelf, card_slot, ip_address)
            card_data.update({
                "Temperature": controller[0],
                "Measured Current": controller[1],
                "Measured Power": controller[2]
            })
        else: 
            card_data = {
                    'Type de carte': card_name,
                    'Slot': card_slot
                }
        result.append(card_data)
    return result

def ScriptAutre(equipment_name, card_name, slot):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version': version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")

    # Appel des fonctions de la classe Nokia
    oidType = "1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.22"
    card_names = get_card_names(ip_address, oidType)
    card_slots = get_slot(ip_address, oidType)
    card_shelfs = get_shelf(ip_address, oidType)
    for i, (card_name, card_slot, card_shelf) in enumerate(zip(card_names, card_slots, card_shelfs)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Shelf': card_shelf
        }
        if "MCS8-16" in card_name or "USRPNL" in card_name or "SHFPNL" in card_name or "PF" in card_name:
            autre = Autre(card_shelf, card_slot, ip_address)
            card_data.update({
                "Temperature": autre[0]
            })
        else:
            card_data = {
                'Type de carte': card_name,
                'Slot': card_slot
            }

        result.append(card_data)

    return result
