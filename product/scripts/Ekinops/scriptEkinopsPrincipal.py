import subprocess

from scripts.FindDNS import find_dns
from scripts.GetIp import get_ip
from scripts.Ekinops.ClassEkinops import *

def IsEkinops(equipment_name):
    dns = find_dns(equipment_name)
    commandIsEkinops = subprocess.check_output(f"snmpget -v2c -c cpdea {dns} 1.3.6.1.2.1.1.1.0", shell=True)
    testEkinops = commandIsEkinops.decode('utf-8').strip()
    if "Ekinops" in testEkinops:
        return True
    else :
        return False

def ScriptEkinopsPrincipal(equipment_name):
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version' : version
        })
    else:
        print(f"Aucun DNS correspondant trouvé pour l'équipement {equipment_name}")
    oidType="1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot="1.3.6.1.4.1.20044.7.8.1.1.2"
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)
    for card_name in card_names :
        if "PM_FAN_C" in card_name:
            chassis=card_name.split("FAN_", 1)[1]
        else:
            chassis="C600"
    for i, (card_name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        result.append(card_data)
    return result

def ScriptEkinopsSecond(equipment_name):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version' : version
        })
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for card_name in card_names :
        if "PM_FAN_C" in card_name:
            chassis=card_name.split("FAN_", 1)[1]
        else:
            chassis="C600"
    processed_emux_cards = set()
    processed_c1008mplh_cards = set()
    processed_c1008ge_cards = set()
    processed_frs02_cards = set()
    processed_pm06006mp_cards = set()
    processed_oail_hcs_cards = set()
    processed_1001rr_cards = set()
    processed_c1001hc_cards = set()
    processed_pm404_cards = set()
    processed_oabplc_cards = set()
    processed_roadm_flex_cards = set()
    processed_oabp_hcs_cards = set()
    processed_otdr_cards = set()




    for i, (card_name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
        
        
        if "EMUX" in card_name and card_slot not in processed_emux_cards:
            communaute = card_slot
            emuxclient = emuxClient(communaute, ip_address)
            emuxline = emuxLine(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({
                'Line Rx Avg Power': emuxline[2],
                'Line Tx Avg Power': emuxline[3],
                'Line Uncorrected FEC Errors': emuxline[1],
                'Line Temp': emuxline[0],
                'Port': {}
            })
            while verif:
                client_data = emuxclient.get(i, [])
                if not client_data:
                    verif = False
                elif len(client_data) >= 1:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Traffic In': client_data[3],
                        'Client Traffic Out': client_data[4],
                        'Client Input CRC': client_data[5],
                        'Client Output CRC': client_data[6],
                        'Client Temp': client_data[0]
                    }
                    card_data[f"Port {i}"] = channel_data
                i += 1
            
            processed_emux_cards.add(card_slot)
            
        elif '200FRS02' in card_name and card_slot not in processed_frs02_cards:
            communaute = card_slot
            clientFrs02 = ClientFRS02(communaute, ip_address)
            lineFrs02 = LineFRS02(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({
                'Line 1 Tx Power': lineFrs02[3],
                'Line 1 Rx Power': lineFrs02[2],
                'Line Uncorrected FEC Errors': lineFrs02[1],
                'Line 1 Temp': lineFrs02[0],
                'Client Port 1 temperature': lineFrs02[4],
                'Client Port 2 temperature': lineFrs02[5],
                'Port': {}
            })
            while verif:
                client_data = clientFrs02.get(i, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 1:
                    channel_data = {
                        'Client1/2 avg Rx Power': client_data[0],
                        'Client1/2 avg Tx Power': client_data[1],
                        'Client Input CRC': client_data[2],
                        'Client Output CRC': client_data[3],
                        'Client Traffic In': client_data[4],
                        'Client Traffic Out': client_data[5]
                    }
                    card_data[f'Port {i}'] = channel_data
                i += 1
            
            processed_frs02_cards.add(card_slot)

        elif 'OABP-HCS' in card_name and card_slot not in processed_oabp_hcs_cards:
            communaute = card_slot
            oabp_hcs = clientOABP_HCS(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = oabp_hcs.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 0:
                        channel_data = {
                            'Temperature': client_data[0],
                            'Booster RX': client_data[1],
                            'Booster TX': client_data[2],
                            'Booster Gain': client_data[3],
                            'Booster pump laser bias': client_data[4],
                            'Pre Amp RX': client_data[5],
                            'Pre Amp TX': client_data[6],
                            'Pre-Amp Gain': client_data[7],
                            'Pre-Amp pump laser bias': client_data[8]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_oabp_hcs_cards.add(card_slot)
   
        elif 'OTDR' in card_name and card_slot not in processed_otdr_cards:
            communaute = card_slot
            otdr = OTDR(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data_otdr = otdr.get(i, [])
                if not client_data_otdr:
                    verif = False
                try:
                    if len(client_data_otdr) >= 1:
                        channel_data = {
                            'Temp': client_data_otdr[0],
                            'RX Power': client_data_otdr[1],
                            'TX Power': client_data_otdr[2],
                            'OTDR Fault Distance': client_data_otdr[3]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_otdr_cards.add(card_slot)
                  
        elif 'C1008MPLH' in card_name and card_slot not in processed_c1008mplh_cards:
            communaute = card_slot
            c1008mplhClient1 = c1008mplhClient(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = c1008mplhClient1.get(j, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 1:
                        channel_data = {
                            'Client Rx Power': client_data[1],
                            'Client Tx Power': client_data[2],
                            'Client Input CRC': client_data[3],
                            'Client Input Error': client_data[4],
                            'Client Output Error': client_data[5],
                            'Client Temp': client_data[0],
                            'Line Rx Avg Power': client_data[8],
                            'Line Tx Avg Power': client_data[9],
                            'Line Error counter': client_data[7],
                            'Line Temp': client_data[6]
                        }
                        card_data[f'Port {j}'] = channel_data
                except IndexError:
                    verif = False
                j += 1
            
            processed_c1008mplh_cards.add(card_slot)

        elif 'C1008GE' in card_name and card_slot not in processed_c1008ge_cards:
            communaute = card_slot
            c1008ge = c1008GEClient(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = c1008ge.get(j, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 1:
                        channel_data = {
                            'Client Rx Power': client_data[1],
                            'Client Tx Power': client_data[2],
                            'Client Input CRC': client_data[3],
                            'Client Input Error': client_data[4],
                            'Client Output Error': client_data[5],
                            'Client Input CRC Error': client_data[6],
                            'Client Temp': client_data[0],
                            'Line Rx Power': client_data[9],
                            'Line Tx Power': client_data[10],
                            'Line Error counter': client_data[8],
                            'Line Temp': client_data[7]
                        }
                        card_data[f'Port {j}'] = channel_data
                except IndexError:
                    verif = False
                j += 1
            
            processed_c1008ge_cards.add(card_slot)
        
        elif 'PM_O6006MP' in card_name and card_slot not in processed_pm06006mp_cards:
            communaute = card_slot
            pm06006mp = pm06006Client(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = pm06006mp.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 1:
                        channel_data = {
                            'Client Rx Power': client_data[1],
                            'Client Tx Power': client_data[2],
                            'Client Traffic In': client_data[3],
                            'Client Input Errors': client_data[4],
                            'Client Output Errors': client_data[5],
                            'Client Temp': client_data[0],
                            'Line Rx Avg Power': client_data[8],
                            'Line Tx Avg Power': client_data[9],
                            'Line Error counter': client_data[7],
                            'Line Temp': client_data[6]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_pm06006mp_cards.add(card_slot)
              
        elif 'OAIL-HCS' in card_name and card_slot not in processed_oail_hcs_cards:
            communaute = card_slot
            oail = oail_hcs(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = oail.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 0:
                        channel_data = {
                            'IL1 Rx Power': client_data[1],
                            'IL1 Tx Power': client_data[2],
                            'IL1 Gain': client_data[3],
                            'IL1 pump laser bias': client_data[4],
                            'IL2 Rx Power': client_data[5],
                            'IL2 Tx Power': client_data[6],
                            'module Temp': client_data[0],
                            'IL2 Gain': client_data[7],
                            'IL2 pump laser bias': client_data[8]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_oail_hcs_cards.add(card_slot)
                
        elif '1001RR' in card_name and card_slot not in processed_1001rr_cards:
            communaute = card_slot
            pm1001rr = pm1001RRClient(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = pm1001rr.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 0:
                        channel_data = {
                            'Client Rx Power': client_data[1],
                            'Client Tx Power': client_data[2],
                            'Client Temp': client_data[0],
                            'Line Rx Power': client_data[4],
                            'Line Tx Power': client_data[5],
                            'Line Temp': client_data[3]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_1001rr_cards.add(card_slot)
                
        elif 'C1001HC' in card_name and card_slot not in processed_c1001hc_cards:
            communaute = card_slot
            c1001hc = c1001hcClient(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = c1001hc.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 0:
                        channel_data = {
                            'Client Rx Power': client_data[1],
                            'Client Tx Power': client_data[2],
                            'Client Traffic In': client_data[3],
                            'Client Traffic Out': client_data[4],
                            'Client Traffic Input CRC': client_data[5],
                            'Client Traffic Output CRC': client_data[6],
                            'Client Temp': client_data[0],
                            'Line Rx Power': client_data[9],
                            'Line Tx Power': client_data[10],
                            'Line Input Errors': client_data[8],
                            'Line Temp': client_data[7]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_c1001hc_cards.add(card_slot)


        elif 'PM404' in card_name and card_slot not in processed_pm404_cards:
            communaute = card_slot
            pm404 = pm404Client(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = pm404.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 1:
                        channel_data = {
                            'Client Rx Power': client_data[1],
                            'Client Tx Power': client_data[2],
                            'Client Temp': client_data[0],
                            'Line Rx Power': client_data[4],
                            'Line Tx Power': client_data[5],
                            'Line Temp': client_data[3]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_pm404_cards.add(card_slot)

            
        elif any(x in card_name for x in ['OAB-E', 'OABP-E', 'OABPLC']) and card_slot not in processed_oabplc_cards:
            communaute = card_slot
            oabplc = oabClient(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = oabplc.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 0:
                        channel_data = {
                            'Booster Rx Power': client_data[1],
                            'Booster Tx Power': client_data[2],
                            'Booster Gain': client_data[3],
                            'Booster pump laser bias': client_data[4],
                            'Pre-Amp Rx Power': client_data[5],
                            'Pre-Amp Tx Power': client_data[6],
                            'Pre-Amp Gain': client_data[7],
                            'Pre-Amp pump laser bias': client_data[8],
                            'module Temp': client_data[0]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_oabplc_cards.add(card_slot)

                
        elif 'ROADM-FLEX' in card_name and card_slot not in processed_roadm_flex_cards:
            communaute = card_slot
            Roadm = roadm(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = Roadm.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 0:
                        channel_data = {
                            'Channel number': client_data[0],
                            'Channel power In': client_data[1],
                            'Channel power Out': client_data[2]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1

            processed_roadm_flex_cards.add(card_slot)


        else:
            card_data = {
                'Type de carte': card_name,
                'Slot': card_slot,
                'Chassis': chassis
            }
            
        result.append(card_data)        
    return result

def ScriptEmux(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version' : version
        })
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for card_name in card_names :
        if "PM_FAN_C" in card_name:
            chassis=card_name.split("FAN_", 1)[1]
        else:
            chassis="C600"
    for i, (card_name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
        if "EMUX" in card_name and card_slot == slot:
            communaute = card_slot
            emuxclient = emuxClient(communaute, ip_address)
            emuxline = emuxLine(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({
                'Line Rx Avg Power': emuxline[2],
                'Line Tx Avg Power': emuxline[3],
                'Line Uncorrected FEC Errors': emuxline[1],
                'Line Temp': emuxline[0],
                'Port': {}
            })
            while verif:
                client_data = emuxclient.get(i, [])
                if not client_data:
                    verif = False
                elif len(client_data) >= 1:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Traffic In': client_data[3],
                        'Client Traffic Out': client_data[4],
                        'Client Input CRC': client_data[5],
                        'Client Output CRC': client_data[6],
                        'Client Temp': client_data[0]
                    }
                    card_data[f"Port {i}"] = channel_data
                i += 1
            
        else:
            card_data = {
                'Type de carte': card_name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)        
    return result

def Script200FRS02(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version' : version
        })
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for card_name in card_names:
        if "PM_FAN_C" in card_name:
            chassis = card_name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (card_name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
        if card_slot == slot and '200FRS02' in card_name:
            communaute = card_slot
            clientFrs02 = ClientFRS02(communaute, ip_address)
            lineFrs02 = LineFRS02(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({
                'Line 1 Tx Power': lineFrs02[3],
                'Line 1 Rx Power': lineFrs02[2],
                'Line Uncorrected FEC Errors': lineFrs02[1],
                'Line 1 Temp': lineFrs02[0],
                'Client Port 1 temperature': lineFrs02[4],
                'Client Port 2 temperature': lineFrs02[5],
                'Port': {}
            })
            while verif:
                client_data = clientFrs02.get(i, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 1:
                    channel_data = {
                        'Client1/2 avg Rx Power': client_data[0],
                        'Client1/2 avg Tx Power': client_data[1],
                        'Client Input CRC': client_data[2],
                        'Client Output CRC': client_data[3],
                        'Client Traffic In': client_data[4],
                        'Client Traffic Out': client_data[5]
                    }
                    card_data[f'Port {i}'] = channel_data
                i += 1
            specific_card_data = card_data
        else:
            result.append(card_data)
    
    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info
    
    return result

def ScriptOabphcs(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version' : version
        })
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for card_name in card_names:
        if "PM_FAN_C" in card_name:
            chassis = card_name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (card_name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
        if 'OABP-HCS' in card_name and card_slot == slot:
            communaute = card_slot
            oabp_hcs = clientOABP_HCS(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = oabp_hcs.get(i, [])
                if not client_data:
                    verif = False
                try:
                    if len(client_data) >= 0:
                        channel_data = {
                            'Temperature': client_data[0],
                            'Booster RX': client_data[1],
                            'Booster TX': client_data[2],
                            'Booster Gain': client_data[3],
                            'Booster pump laser bias': client_data[4],
                            'Pre Amp RX': client_data[5],
                            'Pre Amp TX': client_data[6],
                            'Pre-Amp Gain': client_data[7],
                            'Pre-Amp pump laser bias': client_data[8]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': card_name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)
    
    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info
    
    return result

def ScriptOTDR(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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
    
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)
    
    # Détermine le chassis
    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"
    
    specific_card_data = None
    
    # Parcourt toutes les cartes
    for i, (card_name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': card_name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
        if 'OTDR' in card_name and card_slot == slot:
            communaute = card_slot
            otdr = OTDR(communaute, ip_address)
            i = 1
            verif = True
            card_data.update({'Port': {}})
            
            while verif:
                client_data_otdr = otdr.get(i, [])
                if not client_data_otdr:
                    verif = False
                try:
                    if len(client_data_otdr) >= 1:
                        channel_data = {
                            'Temp': client_data_otdr[0],
                            'RX Power': client_data_otdr[1],
                            'TX Power': client_data_otdr[2],
                            'OTDR Fault Distance': client_data_otdr[3]
                        }
                        card_data[f'Port {i}'] = channel_data
                except IndexError:
                    verif = False
                i += 1
            
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': card_name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)
    
    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptC1008MPLH(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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

    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"
    
    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

        if 'C1008MPLH' in name and card_slot == slot:
            communaute = card_slot
            c1008mplhClient1 = c1008mplhClient(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = c1008mplhClient1.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 1:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Input CRC': client_data[3],
                        'Client Input Error': client_data[4],
                        'Client Output Error': client_data[5],
                        'Client Temp': client_data[0],
                        'Line Rx Avg Power': client_data[8],
                        'Line Tx Avg Power': client_data[9],
                        'Line Error counter': client_data[7],
                        'Line Temp': client_data[6]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)
    
    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptC1008GE(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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

    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"
    
    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

        if 'C1008GE' in name and card_slot == slot:
            communaute = card_slot
            c1008ge = c1008GEClient(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = c1008ge.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 1:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Input CRC': client_data[3],
                        'Client Input Error': client_data[4],
                        'Client Output Error': client_data[5],
                        'Client Input CRC Error': client_data[6],
                        'Client Temp': client_data[0],
                        'Line Rx Power': client_data[9],
                        'Line Tx Power': client_data[10],
                        'Line Error counter': client_data[8],
                        'Line Temp': client_data[7]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)
    
    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptPM06(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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

    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

        if 'PM_O6006MP' in name and card_slot == slot:
            communaute = card_slot
            pm06006mp = pm06006Client(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = pm06006mp.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 1:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Traffic In': client_data[3],
                        'Client Input Errors': client_data[4],
                        'Client Output Errors': client_data[5],
                        'Client Temp': client_data[0],
                        'Line Rx Avg Power': client_data[8],
                        'Line Tx Avg Power': client_data[9],
                        'Line Error counter': client_data[7],
                        'Line Temp': client_data[6]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptOAILHCS(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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

    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

        if 'OAIL-HCS' in name and card_slot == slot:
            communaute = card_slot
            oail = oail_hcs(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = oail.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 0:
                    channel_data = {
                        'IL1 Rx Power': client_data[1],
                        'IL1 Tx Power': client_data[2],
                        'IL1 Gain': client_data[3],
                        'IL1 pump laser bias': client_data[4],
                        'IL2 Rx Power': client_data[5],
                        'IL2 Tx Power': client_data[6],
                        'module Temp': client_data[0],
                        'IL2 Gain': client_data[7],
                        'IL2 pump laser bias': client_data[8]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def Script1001RR(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version' : version
        })
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
        if '1001RR' in name and card_slot == slot:
            communaute = card_slot
            pm1001rr = pm1001RRClient(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = pm1001rr.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 0:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Temp': client_data[0],
                        'Line Rx Power': client_data[4],
                        'Line Tx Power': client_data[5],
                        'Line Temp': client_data[3]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptC1001HC(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
    result = []
    dns = find_dns(equipment_name)
    ip_address = get_ip(dns)
    version = get_version(dns)
    if dns:
        result.append({
            'Nom equipement': equipment_name,
            'DNS': dns,
            'Adresse IP': ip_address,
            'Version' : version
        })
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
        if 'C1001HC' in name and card_slot == slot:
            communaute = card_slot
            c1001hc = c1001hcClient(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = c1001hc.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 0:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Traffic In': client_data[3],
                        'Client Traffic Out': client_data[4],
                        'Client Traffic Input CRC': client_data[5],
                        'Client Traffic Output CRC': client_data[6],
                        'Client Temp': client_data[0],
                        'Line Rx Power': client_data[9],
                        'Line Tx Power': client_data[10],
                        'Line Input Errors': client_data[8],
                        'Line Temp': client_data[7]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptPM404(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

        if 'PM404' in name and card_slot == slot:
            communaute = card_slot
            pm404 = pm404Client(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = pm404.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 1:
                    channel_data = {
                        'Client Rx Power': client_data[1],
                        'Client Tx Power': client_data[2],
                        'Client Temp': client_data[0],
                        'Line Rx Power': client_data[4],
                        'Line Tx Power': client_data[5],
                        'Line Temp': client_data[3]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptOAB(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
        else:
            chassis = "C600"

    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

        if any(x in name for x in ['OAB-E', 'OABP-E', 'OABPLC']) and card_slot == slot:
            communaute = card_slot
            oabplc = oabClient(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = oabplc.get(j, [])
                if not client_data:
                    verif = False
                if len(client_data) >= 0:
                    channel_data = {
                        'Booster Rx Power': client_data[1],
                        'Booster Tx Power': client_data[2],
                        'Booster Gain': client_data[3],
                        'Booster pump laser bias': client_data[4],
                        'Pre-Amp Rx Power': client_data[5],
                        'Pre-Amp Tx Power': client_data[6],
                        'Pre-Amp Gain': client_data[7],
                        'Pre-Amp pump laser bias': client_data[8],
                        'module Temp': client_data[0]
                    }
                    card_data[f'Port {j}'] = channel_data
                j += 1
            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Place specific card data after equipment info

    return result

def ScriptROADM(equipment_name, card_name, slot):
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
    result = []
    
    # Obtenir les informations de base de l'équipement
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
    
    # Obtenir les noms et slots des cartes
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)

    # Déterminer le chassis
    chassis = "C600"
    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
            break
    
    specific_card_data = None

    # Traiter chaque carte
    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

        # Vérifier si c'est la carte spécifiée et extraire les données détaillées
        if 'ROADM-FLEX' in name and card_slot == slot:
            communaute = card_slot
            Roadm = roadm(communaute, ip_address)
            j = 1
            verif = True
            card_data.update({'Port': {}})
            while verif:
                client_data = Roadm.get(j, [])
                if not client_data:
                    verif = False
                elif len(client_data) >= 3:
                    channel_data = {
                        'Channel number': client_data[0],
                        'Channel power In': client_data[1],
                        'Channel power Out': client_data[2]
                    }
                    card_data[f'Port {j}'] = channel_data
                    j += 1
                else:
                    verif = False

            specific_card_data = card_data
        else:
            card_data = {
                'Type de carte': name,
                'Slot': card_slot,
                'Chassis': chassis
            }

        result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Placer les données spécifiques après les informations de l'équipement

    return result

def ScriptOPM8(equipment_name, card_name, slot):
    
    oidType = "1.3.6.1.4.1.20044.7.8.1.1.3"
    oidSlot = "1.3.6.1.4.1.20044.7.8.1.1.2"
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
    card_names = get_card_types(ip_address, oidType)
    card_slots = get_card_slot(ip_address, oidSlot)
    chassis = "C600"
    for name in card_names:
        if "PM_FAN_C" in name:
            chassis = name.split("FAN_", 1)[1]
            break
    
    specific_card_data = None

    for i, (name, card_slot) in enumerate(zip(card_names, card_slots)):
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }
        
    if 'OPM8' in name and card_slot == slot:
        communaute = card_slot
        opm8 = OPM8(communaute, ip_address)
        tabChannelPower = OPM8ChannelPower(communaute, ip_address)
        card_data.update({
                "Type de carte": card_name,
                "Slot": card_slot,
                "OPM Power Input OPM1": opm8[0],
                "OPM Power Input OPM2": opm8[1],
                "OPM Power Input OPM3": opm8[2],
                "OPM Power Input OPM4": opm8[3],
                "OPM Power Input OPM5": opm8[4],
                "OPM Power Input OPM6": opm8[5],
                "OPM Power Input OPM7": opm8[6],
                "OPM Power Input OPM8": opm8[7],
                "Channel Power": {}
            })
        i = 16
        verif = True
        while verif:
            client_data = tabChannelPower.get(i, [])
            if not client_data:
                verif = False
            try:
                if len(client_data) > 1 and "Pas ici" not in client_data[1]:
                    channel_data = {
                            "Température": client_data[0],
                            "OPM Channel Power OPM1": client_data[1],
                            "OPM Channel Power OPM2": client_data[3],
                            "OPM Channel Power OPM3": client_data[5],
                            "OPM Channel Power OPM4": client_data[7],
                            "OPM Channel Power OPM5": client_data[9],
                            "OPM Channel Power OPM6": client_data[11],
                            "OPM Channel Power OPM7": client_data[13],
                            "OPM Channel Power OPM8": client_data[15]
                        }
                card_data.update({f"channel {i}": channel_data})
            except IndexError:
                verif = False
            i += 1

        specific_card_data = card_data
    else:
        card_data = {
            'Type de carte': name,
            'Slot': card_slot,
            'Chassis': chassis
        }

    result.append(card_data)

    if specific_card_data:
        result.insert(1, specific_card_data)  # Placer les données spécifiques après les informations de l'équipement

    return result
