import re
import subprocess

def net_snmp(host, oid):
    return_value = None
    command = ['snmpget', '-v', '2c', '-c', 'cpdea', host, oid]
    
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        print("SNMP Output:", output)  # Log pour vérifier la sortie SNMP

    except subprocess.CalledProcessError as e:
        print('Erreur lors de l\'exécution de la commande SNMP:', e.output)
        return return_value, None  # Retourner None si l'exécution échoue

    # Analyse de la sortie pour obtenir la valeur de l'OID
    if output:
        lines = output.strip().split('\n')
        if lines:
            last_line_parts = lines[-1].split(' ')
            if last_line_parts:
                return_value = last_line_parts[-1]

    return return_value, output

def extract_ip_and_time(ip):
    ip_pattern = re.compile(r'^([\d.]+)\s+time=([\d.]+)$')
    ip_match = ip_pattern.match(ip)
    if ip_match:
        return ip_match.group(1), ip_match.group(2)
    else:
        return None, None

def format_snmp_time(snmp_time_raw):
    pattern = r"\) ([^\\n]+)\n"
    match = re.search(pattern, snmp_time_raw)

    if match:
        formatted_time = match.group(1).strip()
        return formatted_time
    else:
        return "Format de réponse SNMP non reconnu"

def process_data(port, id_service, ip, state):
    return_data = {}

    # Extraction de l'IP et du temps
    ip_equipement, temps = extract_ip_and_time(ip)
    if not ip_equipement or not temps:
        return return_data
    
    return_data['ip_equipement'] = ip_equipement
    return_data['temps'] = temps

    # Motif pour le port
    port_pattern = re.compile(r'access-(\d)-(\d)-(\d)-(\d)|GigabitEthernet(\d+)/(\d+)/(\d+)')
    port_match = port_pattern.match(port)

    # Extraire type_id à partir de id_service
    try:
        type_id = id_service.split('-')[2]
    except IndexError:
        print("Erreur dans l'ID du service")
        return return_data

    # Si le port correspond au motif
    if port_match:
        if port.startswith("access-"):
            nte_service_pro = f"{port_match.group(1)}-{port_match.group(2)}-{port_match.group(3)}-{port_match.group(4)}"
            return_data['ID_SERVICE'] = id_service
            return_data['NTE_FIBRE'] = nte_service_pro
            return_data['NTE_CACTI'] = ip_equipement 
            return_data['Type_ID'] = type_id
            return_data['NTE_FIBRE_PORT_AVEC_POINT'] = f"{port_match.group(1)}.{port_match.group(2)}.{port_match.group(3)}.{port_match.group(4)}"
            return_data['slotID_ADVA'] = port_match.group(3)
            return_data['EnableState_port_nte'] = state
            fin_port_adva = port_match.group(4)
        elif port.startswith("GigabitEthernet"):
            nte_service_pro = f"{port_match.group(5)}-{port_match.group(6)}-{port_match.group(7)}"
            return_data['ID_SERVICE'] = id_service
            return_data['NTE_FIBRE'] = nte_service_pro
            return_data['NTE_CACTI'] = ip_equipement 
            return_data['Type_ID'] = type_id
            return_data['NTE_FIBRE_PORT_AVEC_POINT'] = f"{port_match.group(5)}.{port_match.group(6)}.{port_match.group(7)}"
            return_data['slotID_ADVA'] = port_match.group(6)
            return_data['EnableState_port_nte'] = state
            fin_port_adva = port_match.group(7)

        # Déterminer NbAssociation en fonction de slotID_ADVA
        if return_data['slotID_ADVA'] == '1':
            return_data['NbAssociation'] = fin_port_adva
        elif int(return_data['slotID_ADVA']) > 1:
            return_data['NbAssociation'] = f"{return_data['slotID_ADVA']}{fin_port_adva}"
    else:
        print("Aucun port valide trouvé pour :", port)
        return return_data  # Sortie anticipée si le port est invalide

    # S'assurer que NTE_FIBRE_PORT_AVEC_POINT est bien présent
    if 'NTE_FIBRE_PORT_AVEC_POINT' not in return_data:
        print("Erreur : NTE_FIBRE_PORT_AVEC_POINT manquant.")
        return return_data

    return return_data

def Oam_Adva(port, id_service, ip, state, type_media):
    if state == "up":
        state = "in-service"

    return_data = process_data(port, id_service, ip, state)

    if 'NTE_FIBRE_PORT_AVEC_POINT' in return_data:
        oid = ".1.3.6.1.4.1.2544.1.12.4.1.1.1.66." + return_data["NTE_FIBRE_PORT_AVEC_POINT"]
    else:
        print("Erreur : NTE_FIBRE_PORT_AVEC_POINT manquant.")
        return return_data

    return_data['type_fttbv3'], raw = net_snmp(return_data['NTE_CACTI'], oid)
    return_data["type_media_NTE"] = type_media
    module_fiber(return_data)

    if return_data['type_fttbv3'] == "2":
        if "-PLUS" in id_service:
            return_data['NbAssociation'] = return_data.get('NbAssociation', '') + "2"
            if re.match(r'1/1/1/2', port):
                return_data['NbAssociation'] = "2"
        else:
            return_data['NbAssociation'] = return_data.get('NbAssociation', '') + "1"
            if re.match(r'1/1/1/2', port):
                return_data["NbAssociation"] = "1"
    if "IXEN" in id_service:
        port = return_data["NTE_FIBRE_PORT_AVEC_POINT"]
        ip = return_data["ip_equipement"]
        return_data['OAM_IXEN'] = OAM_IXEN(port, id_service,ip,state)
    else:    
        if return_data['EnableState_port_nte'] == "in-service" and not re.search(r'vpn', return_data.get('Type_ID', '')):
            oid = ".1.3.111.2.802.1.1.8.1.7.3.1.2.2." + return_data['NbAssociation'] + ".1.101"
            return_data['OAM_ADVA'], _ = net_snmp(return_data['NTE_CACTI'], oid)
            
            if return_data["OAM_ADVA"] == "4":
                oid = ".1.3.111.2.802.1.1.8.1.7.3.1.3.2." + return_data["NbAssociation"] + ".1.101"
                _, raw = net_snmp(return_data['NTE_CACTI'], oid)
                
                # Extraction et formatage du temps SNMP
                formatted_time = format_snmp_time(raw)
                
                return_data['OAM_ADVA'] = f"Chaine de liaison OK via OAM depuis {formatted_time}"
            else:
                return_data['OAM_ADVA'] = "Chaine de liaison via OAM KO"
    
    return return_data

def Oam_Livraison(equipment_type, equipment_model, state, vpls, ip, equipment_type_nte):
    return_dict = {}
    return_dict["TYPE_EQUIPEMENT_NTE"] = equipment_type_nte
    
    if (re.search(r'7450|7750', equipment_type) or re.search(r'7450|7750', equipment_model)) and state == "En service" and re.search(r'ADVA', return_dict["TYPE_EQUIPEMENT_NTE"]):
        ip_equipement, _ = extract_ip_and_time(ip)
        if ip_equipement is not None and re.search(r'\d+\.\d+\.\d+\.\d+', ip_equipement):
            oid = ".1.3.111.2.802.1.1.8.1.7.3.1.2.2." + vpls + ".101.1"
            return_dict["OAM_END_POINT_C"], _ = net_snmp(ip_equipement, oid)
            return_dict["OID_TEST"] = ".101.1"
            if return_dict["OAM_END_POINT_C"] == '4':
                return_dict["OAM_LIVRAISON"] = "Chaine de liaison OK via OAM"
            else:
                return_dict["OAM_LIVRAISON"] = "Verification de la chaine de liaison via OAM KO"
        else:
            return_dict["OAM_LIVRAISON"] = "Echec de verification de la chaine de liaison via OAM"
    else:
        return_dict["OAM_LIVRAISON"] = "Pas de verification d'OAM si la livraison n'est pas un 7x50 ou s'il n'y a pas d'ADVA"
    
    return return_dict

def module_fiber(return_data):
    if return_data.get('type_media_NTE') == "fiber" or return_data.get('type_media_NTE_SAS') == "fiber":
        oid = ".1.3.6.1.4.1.2544.1.12.4.1.1.1.13." + return_data.get('NTE_FIBRE_PORT_AVEC_POINT', '')
        response = net_snmp(return_data.get('NTE_CACTI', ''), oid)

        if response and 'Not Available' not in response:
            return_data['PRESENCE_SFP'] = f"Module fibre présent sur le port {return_data.get('NTE_FIBRE_PORT_AVEC_POINT', '')}"
        else:
            return_data['PRESENCE_SFP'] = f"Absence d'un module fibre sur le port {return_data.get('NTE_FIBRE_PORT_AVEC_POINT', '')}"
    else:
        print("Le type de média n'est pas 'fiber'")

    return return_data

def OAM_IXEN(port, id_service,ip,state):
    return_data = ""

    if state == "up":
        state = "in-service"

    NbAssociation ="3"

    oidMEP1 = ".1.3.111.2.802.1.1.8.1.7.3.1.2.2." + NbAssociation + ".2.1"
    return_data_snmp, _ = net_snmp(ip, oidMEP1)
    case = 1 

    if "No Such" in return_data_snmp:
        oidMEP2 = ".1.3.111.2.802.1.1.8.1.7.3.1.2.2." + NbAssociation + ".1.2"
        return_data_snmp, _ = net_snmp(ip, oidMEP2)
        case = 2
        if "No Such" in return_data_snmp:
            return_data = "Chaine de liaison via OAM KO"


    oidDate1 = ".1.3.111.2.802.1.1.8.1.7.3.1.3.2.3.2.1"
    _, return_time1 = net_snmp(ip, oidDate1)

    if "No Such" in return_time1:
        oidDate2 = ".1.3.111.2.802.1.1.8.1.7.3.1.3.2.3.1.2"
        _, return_time2 = net_snmp(ip, oidDate2)
        formatted_time2 = format_snmp_time(return_time2)
        return_data = f"Chaine de liaison OK via OAM depuis {formatted_time2}"
    else:
        formatted_time1 = format_snmp_time(return_time1)
        return_data = f"Chaine de liaison OK via OAM depuis {formatted_time1}"



    return return_data

