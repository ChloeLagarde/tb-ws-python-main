import time
from concurrent.futures import ThreadPoolExecutor
from scripts.Ssh_Connect import SshConnect
import re

def generate_ping_commands(huawei_obj, id_service, id_vpn_instance):
    """
    Génère une liste de commandes ping en fonction des services et VPN-Instances spécifiés.
    """
    commands = set()  # Utilisation d'un set pour éviter les doublons
    ip_source_vp = None

    # Si le type ou le service correspond à Newlod, -VPNIP-, ou -INTE-
    if "Newlod" in id_service or "-VPNIP-" in id_service or "-INTE-" in id_service:
        vpn_instance_output = huawei_obj.execute_command("display ip vpn-instance interface")
        vpn_instance_data = "".join(vpn_instance_output).replace("/", "_").strip()
        vpn_instances = vpn_instance_data.split("VPN-Instance Name and")

        for instance in vpn_instances:
            # Nettoyage des espaces et autres caractères inutiles
            instance = instance.strip().replace("'", "")
            if "ID :" in instance:
                id_vpn_instance_temp = instance.split("ID :")[1].split(",")[0].strip()
            
            # Vérification de id_vpn_instance
            if not id_vpn_instance and "Trunk1" in instance and "CD78-VPNIP-" in id_service:
                id_vpn_instance = "Trunk1"
                """elif id_vpn_instance in instance:
                id_vpn_instance = id_vpn_instance_temp
                break"""



        # Commandes spécifiques pour CD78-VPNIP-
        if "CD78-VPNIP-" in id_service:
            commands.update([
                " display interface Eth-Trunk 1 | begin PortName",
                " display lacp statistics Eth-trunk 1",
                " display vrrp brief",
                f" display ip routing-table vpn-instance {id_vpn_instance}",
                f" display arp vpn-instance {id_vpn_instance}",
                f" ping -vpn-instance {id_vpn_instance} 10.49.255.14"
            ])

        elif "Newlod" in id_service or "-VPNIP-" in id_service:
            commands.add(f" ping -vpn-instance {id_vpn_instance} 217.119.184.225")

        # Commandes pour RENATER
        if "RENATER" in id_vpn_instance:

            commands.update([
                " display ip routing-table vpn-instance RENATER | no-more",
                " display arp vpn-instance RENATER | no-more"              
        ])

        # Commandes par défaut pour le vpn-instance
        else:
            commands.update([
                f" display ip routing-table vpn-instance {id_vpn_instance} | no-more",
                f" display arp vpn-instance {id_vpn_instance} | no-more"
            ])

        if "VPNIP" in id_service or "INTE" in id_service:
            commands.add(" display bgp all summary")

    # Commande pour INTERNET
    if "INTERNET" in  id_vpn_instance:
        commands.add(f" ping -vpn-instance {id_vpn_instance} 217.119.184.131")

    # Pour le cas spécifique de -VP-
    if "-VP-" in id_service:
        result = huawei_obj.execute_command(" display current-configuration | include 255.255.255.128 | no-more")
        if result:
            for line in result:
                line = line.strip().replace("'", "")
                if "ip address" in line:
                    ip_source_vp = line.split("ip address ")[1].split()[0]

        if ip_source_vp:
            commands.add(f" ping -vpn-instance SURETE_ELEC -a {ip_source_vp} 10.111.1.49 | no-more")
            commands.add(" display ip routing-table vpn-instance SURETE_ELEC | no-more")
            commands.add(" display arp vpn-instance SURETE_ELEC | no-more")

    # Exécution des commandes
    for cmd in commands:
        response = huawei_obj.execute_command(cmd)

        # Nettoyage des résultats
        for matched in response:
            matched = matched.strip().replace("'", "")
            if matched:
                print(f"Réponse : {matched}")
                print(f"<br />{matched}")

    return list(commands)

def format_result(command, result, duration):
    """Formate proprement le résultat d'une commande sous forme de balise, en filtrant les sorties indésirables."""
    # Filtrer les résultats pour exclure les lignes contenant des séquences d'échappement indésirables
    filtered_result = [line for line in result if "\u001b[16D" not in line and "Peer" not in line]
    
    # Récupérer la première ligne après filtrage si disponible
    first_line = filtered_result[0] if filtered_result else ""
    
    # Vérifier si la première ligne est une ligne de commande à exclure
    if re.match(r'^VPN-Instance .*Router ID \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:$', first_line) or re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', first_line):
        return {}
    
    formatted_result = {
        f"commande-{first_line}": {
            "Retour de la commande ": filtered_result,
            "Debut": duration[0],
            "Fin": duration[1],
            "Duree": round(duration[2], 2),
        }
    }
    return formatted_result


def execute_ping_commands_parallel(huawei_obj, commands):
    """
    Exécute une liste de commandes en parallèle et retourne les résultats.
    """
    def execute_and_collect(command):
        start_time = time.time()
        result = huawei_obj.execute_command(command)
        end_time = time.time()
        duration = (time.strftime("%H:%M:%S", time.localtime(start_time)),
                    time.strftime("%H:%M:%S", time.localtime(end_time)),
                    end_time - start_time)
        return format_result(command, result, duration)

    with ThreadPoolExecutor() as executor:
        return list(executor.map(execute_and_collect, commands))

def check(output, keywords):
    """
    Vérifie si des mots-clés sont présents dans les résultats d'une commande.
    """
    keyword_matches = {}
    for keyword in keywords:
        matching_lines = [line for line in output if keyword in line]
        if matching_lines:
            keyword_matches[keyword] = matching_lines

    return keyword_matches

def SshNe05(ip_ne05, id_service, port_network, port):
    """
    Effectue les commandes SSH pour un service donné.
    """
    login = "provauto"
    passwd = "srv-pia64-l"
    timeout = 30

    huawei_obj = SshConnect()
    huawei_obj.set_connection(ip_ne05, login, passwd, timeout)

    if huawei_obj.login_in():
        try:
            output = huawei_obj.execute_command("display ip vpn-instance interface")
            if output:
                vpn_instance_port_network = None
                vpn_instance_port = None
                vpn_instance_found = False

                # Initialisation des cases
                cases = []
                current_case = []

                # Découper l'output en blocs (cases)
                for line in output:
                    if "VPN-Instance Name and ID :" in line:  # Début d'une nouvelle case
                        if current_case:
                            cases.append(current_case)
                        current_case = [line]
                    else:
                        current_case.append(line)
                if current_case:
                    cases.append(current_case)

                # Parcourir chaque case pour trouver les ports
                for case in cases:
                    # Vérifier si la case est valide
                    if not case or "VPN-Instance Name and ID :" not in case[0]:
                        continue

                    # Extraire le nom du VPN-Instance de la première ligne de la case
                    vpn_instance_name = case[0].split(":")[1].strip().split(",")[0]

                    # Vérifier si les ports sont présents dans cette case
                    case_content = " ".join(case)
                    if port_network in case_content and port in case_content:
                        # Les deux ports sont dans le même bloc
                        vpn_instance_port_network = vpn_instance_name
                        vpn_instance_port = vpn_instance_name
                        vpn_instance_found = True
                        break
                    elif port_network in case_content:
                        # Trouvé uniquement port_network
                        vpn_instance_port_network = vpn_instance_name
                    elif port in case_content:
                        # Trouvé uniquement port
                        vpn_instance_port = vpn_instance_name

                # Si les deux ports ne sont pas trouvés dans le même bloc
                if not vpn_instance_found:
                    # Vérifier si chaque port a été associé à un VPN-Instance
                    for case in cases:
                        if not case or "VPN-Instance Name and ID :" not in case[0]:
                            continue

                        vpn_instance_name = case[0].split(":")[1].strip().split(",")[0]
                        case_content = " ".join(case)

                        if port_network in case_content and not vpn_instance_port_network:
                            vpn_instance_port_network = vpn_instance_name
                        if port in case_content and not vpn_instance_port:
                            vpn_instance_port = vpn_instance_name

                # Assurer une valeur par défaut si les ports ne sont pas trouvés
                vpn_instance_port_network = vpn_instance_port_network or "Non trouvé"
                vpn_instance_port = vpn_instance_port or "Non trouvé"

                # Définir l'id_vpn_instance final
                id_vpn_instance = vpn_instance_port_network if vpn_instance_found else None

                # Si un VPN-Instance est trouvé, exécuter les commandes ping
                if vpn_instance_port_network != "Non trouvé" or vpn_instance_port != "Non trouvé":
                    id_vpn_instance = vpn_instance_port_network if vpn_instance_port_network != "Non trouvé" else vpn_instance_port
                    keywords = ["INTERNET", "RENATER"]
                    #check_result = check(output, keywords)
                    commands = generate_ping_commands(huawei_obj, id_service, id_vpn_instance)
                    results = execute_ping_commands_parallel(huawei_obj, commands)
                    return results, output, id_vpn_instance , ip_ne05, id_service, port_network, port
                else:
                    return [{"Erreur": "Aucun VPN-Instance ID trouvé.", "Details": output}]
            else:
                return [{"Erreur": "La commande 'display ip vpn-instance interface' a échoué."}]
        finally:
            huawei_obj.logout()
    else:
        return [{"Erreur": "Échec de connexion.", "Logs": huawei_obj.log}]

