# -*- coding: utf-8 -*-

#
# @file     Salesforce.py
#

# LIBRAIRIES
import json, subprocess, sys, requests, re
from scripts.Version_Alcatel_Telco_One_Access import version_alcatel_telco_one_access
from scripts.FindDNS import find_dns
from scripts.Ping import ping
from scripts.Snmp_Telco_Port import snmp_telco_port
from scripts.Snmp_Ipd_Port import snmp_ipd_port
from scripts.Snmp_Ipd_Port import snmp_olt_port
from scripts.Snmp_Ipd_Vpls import snmp_ipd_vpls
from scripts.Web_soap import diag_gpon, diag_gpon_NCS
from scripts.Oam_AR import Oam_Adva
from scripts.Oam_AR import Oam_Livraison
from scripts.Service_OLT import connect_ssh
from scripts.Ssh_Check_Ne05 import SshNe05
import re

# METHODES


# ================================================Main
def get_equipment_ws(id_service):
    """
    Retourne la liste des équipements pour le service donné.
    En cas d'erreur, renvoie une liste contenant un dict d'erreur explicite.
    Ajoute en premier de la liste le résultat de validationGlobal.
    """

    if "_Details" in id_service:
        id_service_clean = id_service.replace("_Details", "")
    else:
        id_service_clean = id_service

    # Appel RefPro
    json_data = get_Data_RefPro(id_service_clean)
    # Si erreur de RefPro
    if isinstance(json_data, dict) and json_data.get("error"):
        return [json_data]

    # FTTH délégué
    if "FTTH" in id_service or "COVP" in id_service:
        result_ftth = get_Data_n_Process_FTTH(json_data, id_service)
        return result_ftth

    if "OSEN" in id_service or "XGSP" in id_service:
        result_OSEN_XGSP = Process_OSEN_XGSP(json_data, id_service)
        return result_OSEN_XGSP

    # Initialisation
    full_list = []
    nte_list = []
    data_list = []
    equipement_seen = set()
    ordre_de_passage = {}
    equipment_id = 1

    # Recherche type_acces NTE
    type_nte = None
    for item in json_data.get("items", []):
        if "nte" in item.get("equipement", "").lower():
            type_nte = item.get("type_acces")
            break

    # Parcours des équipements
    for item in json_data.get("items", []):
        try:
            equipment_name = item.get("equipement")
            port = item.get("port")
            state = item.get("statut")
            if port == "SPOF":
                continue

            key = (equipment_name, port)
            if key in equipement_seen:
                continue
            equipement_seen.add(key)

            ordre_de_passage[str(equipment_id)] = f"{equipment_id} - {equipment_name}"
            equipment_id += 1

            # Calcul VPLS
            if re.match(r"\w+\-WDM\-\d+", id_service):
                vpls = 0
            else:
                vpls = item.get("id_technique", 0)

            type_acces = item.get("type_acces")
            acces = item.get("acces")
            acces_physique = item.get("acces_physique")

            # Traitement NTE ou Data
            if "nte" in equipment_name.lower():
                try:
                    nte_items, oam_items = Process_nte(
                        equipment_name,
                        id_service,
                        port,
                        [],
                        vpls,
                        type_acces,
                        acces_physique,
                        item,
                        acces,
                    )
                    nte_list.extend(nte_items)
                    data_list.extend(oam_items)
                except Exception as e:
                    return [
                        {
                            "error": "Process_nte_failed",
                            "message": str(e),
                            "equipment": equipment_name,
                        }
                    ]
            else:
                try:
                    edg, cor, olt, other, vpls_list, oam, _ = Process_data(
                        equipment_name,
                        type_acces,
                        vpls,
                        acces_physique,
                        item,
                        id_service,
                        port,
                        state,
                        type_nte,
                    )
                    data_list.extend(edg + cor + olt + other + vpls_list + oam)
                except Exception as e:
                    return [
                        {
                            "error": "Process_data_failed",
                            "message": str(e),
                            "equipment": equipment_name,
                        }
                    ]

        except KeyError as e:
            return [
                {
                    "error": "missing_key",
                    "message": f"Clé manquante {str(e)}",
                    "item": item,
                }
            ]
        except Exception as e:
            return [{"error": "unexpected_error", "message": str(e), "item": item}]

    # Analyse des puissances optiques pour NTE
    for equip in nte_list:
        try:
            val_rx, val_tx = 1, 1
            for k, v in equip.items():
                kl = k.lower()
                if "validation_puissance_optique_tx" in kl and str(v).strip() == "0":
                    val_tx = 0
                if "validation_puissance_optique_rx" in kl and str(v).strip() == "0":
                    val_rx = 0
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        skl = sk.lower()
                        if (
                            "validation_puissance_optique_tx" in skl
                            and str(sv).strip() == "0"
                        ):
                            val_tx = 0
                        if (
                            "validation_puissance_optique_rx" in skl
                            and str(sv).strip() == "0"
                        ):
                            val_rx = 0
            equip["Validation_Puissance_Optique_NTE_RX"] = val_rx
            equip["Validation_Puissance_Optique_NTE_TX"] = val_tx
        except Exception as e:
            return [
                {
                    "error": "optical_power_analysis_failed",
                    "message": str(e),
                    "equipment": equip,
                }
            ]

    # Construction finale
    full_list = nte_list + data_list
    full_list.append({"OrdreDeTraitement": ordre_de_passage})

    # Appel de la validation globale
    validationGlobal = extract_validations(full_list)
    # On insère le résultat de validationGlobal en premier élément
    full_list.insert(0, {"validationGlobal": validationGlobal})

    return full_list


# ==========================================Fonction récupération
def get_Data_RefPro(id_service):

    url = (
        f"https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/ref_sp?who={id_service}"
    )

    try:
        response = requests.get(url)
        if response.status_code != 200:
            return {
                "error": "http_error",
                "message": f"RefPro API a renvoye le statut {response.status_code}",
                "url": url,
            }

        json_data = response.json()
        if not json_data.get("items"):
            return {
                "error": "no_data",
                "message": "La reponse ne contient aucun item",
                "url": url,
            }

        return json_data

    except Exception as e:
        return {"error": "request_exception", "message": str(e), "url": url}


# Get equipement pss
def GetEquipementPSS(equipement):
    return_value = None
    url = f"https://pss.m2m.axione.fr/ords_PREDATOR/pwkspss/nom_reseau/{equipement}"

    try:
        response = requests.get(url)
        return_value = response.json()
    except requests.exceptions.RequestException as e:
        return {"pss": f"Erreur: {e}"}

    return return_value


# ================================Fonction processus


def get_Data_n_Process_FTTH(json_data, id_service):

    list_FTTH = []
    if "FTTHNCS" in id_service or "COVP" in id_service:
        return diag_gpon_NCS(id_service)

    # Mode détails
    use_hotline = id_service.endswith("_Details")
    id_service_clean = id_service.replace("_Details", "")

    # Utilitaire : requête HTTP sécurisée
    def fetch_url(url, context):
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                return None, {
                    "error": "http_error",
                    "message": f"{context} renvoyé {resp.status_code}",
                    "url": url,
                }
            data = resp.json()
            if not data.get("items"):
                return None, {
                    "error": "no_data",
                    "message": f"Aucun item dans réponse {context}",
                    "url": url,
                }
            return data, None
        except Exception as e:
            return None, {"error": "request_exception", "message": str(e), "url": url}

    # Récupération des données hotline si nécessaire
    hotline_data = None
    hotline_error = None
    if use_hotline:
        url_hotline = (
            f"https://ws-ords.m2m.axione.fr/ordsdwh/pwksftth/hotline_ftth?who="
            f"{id_service_clean}"
        )
        data_hot, err_hot = fetch_url(url_hotline, "hotline_ftth")
        if err_hot:
            hotline_error = err_hot
        else:
            hotline_data = data_hot["items"][0]

    # Traitement principal si json_data.items existe
    if json_data.get("items"):
        for item in json_data["items"]:
            port = item.get("port", "")
            if not verifier_format_port(port):
                continue
            try:
                equip = item.get("equipement")
                slot, Port, onu_id = port.split("/")[2:]
                uni = 1
                subscriber_id = id_service_clean
                snmpset = ""

                # Exécution du diagnostic GPON
                try:
                    diag = diag_gpon(
                        equip, slot, Port, onu_id, uni, subscriber_id, snmpset
                    )
                except Exception as e:
                    diag = None
                    diag_error = {
                        "error": "diag_gpon_failed",
                        "message": str(e),
                        "equipement": equip,
                    }

                result = {
                    "Olt": equip,
                    "Slot": slot,
                    "Port": Port,
                    "Onu_id": onu_id,
                    "Uni": uni,
                }
                if diag is not None:
                    result["Snmp info"] = diag
                else:
                    result.setdefault("erreurs", []).append(diag_error)

                # Ajout des infos hotline ou de l'erreur associée
                if use_hotline:
                    if hotline_data:
                        result["Snmp info additionnel"] = hotline_data
                    else:
                        result.setdefault("erreurs", []).append(hotline_error)

                list_FTTH.append(result)
            except Exception as e:
                list_FTTH.append(
                    {"error": "processing_item_failed", "message": str(e), "item": item}
                )
    else:
        # Aucune donnée initiale : appel hotline puis IPPON
        if hotline_data:
            ref = hotline_data.get("ref_prise_cr")
            if ref:
                url_ippon = f"https://ws-ippon.m2m.axione.fr/ippon/api/pto/{ref}"
                data_ip, err_ip = fetch_url(url_ippon, "ippon_pto")
                if err_ip:
                    list_FTTH.append(err_ip)
                else:
                    try:
                        pc = data_ip["ports"][0]["portCoupleur"]
                        slot = pc.get("idSlot", "").lstrip("0")
                        onu = pc.get("onuid")
                        olt = pc.get("olt")
                        portCarte = pc.get("portCarte")
                        uni = 1
                        subscriber_id = id_service_clean
                        snmpset = ""

                        diag = diag_gpon(
                            olt, slot, portCarte, onu, uni, subscriber_id, snmpset
                        )
                        result = {
                            "Snmp info": diag,
                            "Olt": olt,
                            "Slot": slot,
                            "Port": portCarte,
                            "Onu_id": onu,
                            "Uni": uni,
                            "Snmp info additionnel": hotline_data,
                        }
                        list_FTTH.append(result)
                    except Exception as e:
                        list_FTTH.append(
                            {
                                "error": "diag_gpon_failed_ippon",
                                "message": str(e),
                                "response": data_ip,
                            }
                        )
            else:
                list_FTTH.append(
                    {
                        "error": "missing_ref_prise_cr",
                        "message": "ref_prise_cr absent",
                        "hotline": hotline_data,
                    }
                )
        else:
            # ni items ni hotline => rien à faire
            list_FTTH.append(
                {
                    "error": "no_items_no_hotline",
                    "message": "Pas de donnees FTTH disponibles",
                }
            )

    return list_FTTH


def Process_data(
    equipment_name,
    type_acces,
    vpls,
    acces_physique,
    item,
    id_service,
    port,
    state,
    typeNte,
):
    list_edg = []
    list_nte = []
    list_vpls = []
    list_else = []
    list_cor = []
    list_olt = []
    list_mte = []
    list_Racco = []
    Oam = []

    # Flag pour ignorer Oam si id_service contient 'INTE' ou 'VPNIP'
    skip_oam = False
    if id_service and ("INTE" in id_service.upper() or "VPNIP" in id_service.upper()):
        skip_oam = True

    # Création du dictionnaire nte_name -> equipment_type
    equipment_type_nte = typeNte or ""

    host = find_dns(equipment_name)
    ip = ping(host)
    equipment_info = version_alcatel_telco_one_access(host)
    equipment_type = equipment_info["equipment type"]
    equipment_version = equipment_info["equipment version"]
    community_protected = equipment_info["cpdea_community"]
    equipment_model = equipment_info["equipment model"]

    # Détermination du port réseau selon le type d'équipement
    port_network = ""
    if equipment_type == "NE05":
        port_network = "GigabitEthernet0/2/5"
    elif equipment_type in ["GE114", "GE104", "ADVA"]:
        port_network = "network-1-1-1-1"
    elif equipment_type == "T280":
        port_network = "1/1/1"
    elif equipment_type == "NE8000":
        port_network = "GigabitEthernet 0/2/1"
    elif equipment_type == "NE8000 M1A":
        port_network = "GigabitEthernet 0/2/0"

    # Fonction interne pour ajouter l'entrée Oam si nécessaire
    def add_oam_entry():
        if not skip_oam:
            Oam_livraison = Oam_Livraison(
                equipment_type, equipment_model, state, vpls, ip, equipment_type_nte
            )
            Oam.append(
                {
                    "Oam livraison": Oam_livraison,
                    "equipment_type_Liv": equipment_type,
                    "equipment_model_Liv": equipment_model,
                    "state_Liv": state,
                    "vpls_Liv": vpls,
                    "ip_Liv": ip,
                }
            )

    # Cas EDG
    if "edg" in equipment_name:
        snmp_ipd = snmp_ipd_port(host, port, equipment_type)
        nte_name, Port_Racco = extract_Port_Racco(snmp_ipd, port)
        if nte_name and Port_Racco:
            list_Racco.append((nte_name, Port_Racco))

        if "Port de Livraison" in type_acces:
            snmp_vpls = snmp_ipd_vpls(host, vpls, equipment_type)
            add_oam_entry()
            list_edg.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_ipd,
                    "ID Technique": vpls,
                    "Vpls": snmp_vpls,
                }
            )
        else:
            list_edg.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_ipd,
                }
            )

    # Cas COR
    elif "cor" in equipment_name:
        snmp_ipd = snmp_ipd_port(host, port, equipment_type)
        nte_name, Port_Racco = extract_Port_Racco(snmp_ipd, port)
        if nte_name and Port_Racco:
            list_Racco.append((nte_name, Port_Racco))

        if "Port de Livraison" in type_acces:
            snmp_vpls = snmp_ipd_vpls(host, vpls, equipment_type)
            add_oam_entry()
            list_cor.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_ipd,
                    "ID Technique": vpls,
                    "Vpls": snmp_vpls,
                }
            )
        else:
            list_cor.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_ipd,
                }
            )

    # Cas OLT
    elif "olt" in equipment_name:
        if "Port de Livraison" in type_acces:
            snmp_vpls = snmp_ipd_vpls(host, vpls, equipment_type)
            snmp_ipd = snmp_ipd_port(host, port, equipment_type)
            nte_name, Port_Racco = extract_Port_Racco(snmp_ipd, port)
            if nte_name and Port_Racco:
                list_Racco.append((nte_name, Port_Racco))
            add_oam_entry()
            list_olt.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_ipd,
                    "ID Technique": vpls,
                    "Vpls": snmp_vpls,
                }
            )
        else:
            if "MA5800" in equipment_type:
                snmp_ipd = snmp_ipd_port(host, port, equipment_type)
                nte_name, Port_Racco = extract_Port_Racco(snmp_ipd, port)
                if nte_name and Port_Racco:
                    list_Racco.append((nte_name, Port_Racco))
                list_olt.append(
                    {
                        "equipment name": equipment_name,
                        "ip": ip,
                        "equipment_info": equipment_info,
                        "host": host,
                        "port": port,
                        "type acces": type_acces,
                        "acces physique": acces_physique,
                        "snmp info": snmp_ipd,
                    }
                )
            else:
                if ":" in port:
                    port = port.split(":", 1)[1]
                parts = port.split("/")
                slot = parts[-1]
                Port = "/".join(parts[:-1])
                verbose = True
                snmp_ipd = connect_ssh(ip, Port, slot, verbose)
                list_olt.append(
                    {
                        "equipment name": equipment_name,
                        "ip": ip,
                        "equipment_info": equipment_info,
                        "host": host,
                        "port": port,
                        "type acces": type_acces,
                        "acces physique": acces_physique,
                        "ssh info": snmp_ipd,
                        "PORT": Port,
                        "SLot": slot,
                    }
                )

    # Cas MPE
    elif "mpe" in equipment_name:
        snmp_ipd = snmp_ipd_port(host, port, equipment_type)
        if "Port de Livraison" in type_acces:
            snmp_vpls = snmp_ipd_vpls(host, vpls, equipment_type)
            nte_name, Port_Racco = extract_Port_Racco(snmp_ipd, port)
            if nte_name and Port_Racco:
                list_Racco.append((nte_name, Port_Racco))
            add_oam_entry()
            list_else.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_ipd,
                    "ID Technique": vpls,
                    "Vpls": snmp_vpls,
                }
            )
        else:
            list_else.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_ipd,
                }
            )

    # Cas autres équipements
    else:
        if "nte" in equipment_name:
            equipment_type_nte = equipment_type
        else:
            snmp_info = snmp_telco_port(
                equipment_type, equipment_version, port, host, community_protected, ip
            )
            snmp_infonetwork = snmp_info[1]
            snmp_info = snmp_info[0]
            list_else.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port_network": port_network,
                    "snmp info Network": snmp_infonetwork,
                    "port": port,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_info,
                }
            )

    return list_edg, list_cor, list_olt, list_else, list_vpls, Oam, list_Racco


def Process_nte(
    equipment_name,
    id_service,
    port,
    PortRacco,
    vpls,
    type_acces,
    acces_physique,
    item,
    acces,
):
    nte_name = None
    port_racco = None
    Oam = []

    # Flag pour ignorer Oam si id_service contient 'INTE' ou 'VPNIP'
    skip_oam = False
    if id_service and ("INTE" in id_service.upper() or "VPNIP" in id_service.upper()):
        skip_oam = True

    # Parcourir les sous-listes dans PortRacco
    for sublist in PortRacco:
        if len(sublist) >= 2:
            nte_name, port_racco = sublist[0], sublist[1]

    list_nte = []
    # Récupération des informations de l'équipement
    host = find_dns(equipment_name)
    ip = ping(host)
    equipment_info = version_alcatel_telco_one_access(host)
    equipment_type = equipment_info["equipment type"]
    equipment_version = equipment_info["equipment version"]
    community_protected = equipment_info["cpdea_community"]
    equipment_model = equipment_info["equipment model"]

    # Définition du port réseau en fonction du type d'équipement
    port_network = ""
    if equipment_type == "NE05":
        port_network = "GigabitEthernet0/2/5"
    elif equipment_type in ["GE114", "GE104", "ADVA"]:
        port_network = "network-1-1-1-1"
    elif equipment_type == "T280":
        port_network = "1/1/1"
    elif equipment_type == "NE8000":
        port_network = "GigabitEthernet 0/2/1"
    elif equipment_type == "NE8000 M1A":
        port_network = "GigabitEthernet 0/2/0"

    # Fonction interne pour ajouter l'entrée Oam si nécessaire
    def add_oam_entry(state, oam_data):
        if not skip_oam:
            Oam.append({"Status": state, "oam": oam_data})

    # Traitement pour les équipements NTE
    if "nte" in equipment_name:
        equipment_type_nte = equipment_type

        if "Port de Livraison" in type_acces:
            snmp_vpls = snmp_ipd_vpls(host, vpls, equipment_type)
            snmp_info = snmp_telco_port(
                equipment_type, equipment_version, port, host, community_protected, ip
            )
            snmp_infonetwork = snmp_info[1]
            snmp_info = snmp_info[0]
            state = None

            add_oam_entry(
                state,
                Oam_Livraison(
                    equipment_type, equipment_model, state, vpls, ip, equipment_type_nte
                ),
            )

            list_nte.append(
                {
                    "equipment name": equipment_name,
                    "ip": ip,
                    "equipment_info": equipment_info,
                    "host": host,
                    "port_network": port_network,
                    "snmp info Network": snmp_infonetwork,
                    "port": port,
                    "acces": acces,
                    "type acces": type_acces,
                    "acces physique": acces_physique,
                    "snmp info": snmp_info,
                    "ID Technique": vpls,
                    "Vpls": snmp_vpls,
                }
            )

        else:
            snmp_info = snmp_telco_port(
                equipment_type, equipment_version, port, host, community_protected, ip
            )
            snmp_infonetwork = snmp_info[1] if len(snmp_info) > 1 else None
            port_network2 = snmp_info[2] if len(snmp_info) > 2 else None
            snmp_infonetwork2 = snmp_info[3] if len(snmp_info) > 3 else None
            snmp_info = snmp_info[0] if len(snmp_info) > 0 else {}
            state = snmp_info.get("admin status", "Unknown")
            type_media = item.get("type_media", "default_value")
            oam_data = Oam_Adva(port, id_service, ip, state, type_media)

            add_oam_entry(state, oam_data)

            try:
                ip_ne05, _ = ip.split(maxsplit=1)
            except ValueError:
                ip_ne05 = ip

            command = None
            if any(
                keyword in id_service.upper()
                for keyword in ["VP", "VPNIP", "RENATER", "INTE"]
            ):
                cmd = SshNe05(ip_ne05, id_service, port_network, port)
                if isinstance(cmd, str):
                    try:
                        command = json.loads(cmd)
                    except json.JSONDecodeError:
                        command = {"error": "Invalid JSON response"}
                else:
                    command = cmd

            equipment_data = {
                "equipment name": equipment_name,
                "ip": ip,
                "equipment_info": equipment_info,
                "host": host,
                "port_network": port_network,
                "snmp info Network": snmp_infonetwork,
                "port": port,
                "type acces": type_acces,
                "acces": acces,
                "acces physique": acces_physique,
                "snmp info": snmp_info,
                "Commande": command,
            }
            if port_network2 and snmp_infonetwork2:
                equipment_data.update(
                    {
                        "Port network 2": port_network2,
                        "snmp info network 2": snmp_infonetwork2,
                    }
                )
            equipment_data.update({"ID Technique": vpls})

            list_nte.append(equipment_data)

    return list_nte, Oam


def Process_OSEN_XGSP(json_data, id_service):
    resultats = []

    def traiter_ont(equipement):
        equipment_name = equipement
        host = find_dns(equipment_name)

        if host:
            ip = ping(host)
            status = "PING OK" if "No response" not in ip else "Échec du ping"
            return {
                "type": "ONT",
                "equipment": equipment_name,
                "host": host,
                "status": status,
                "ip": ip,
            }
        else:
            return {
                "type": "ONT",
                "equipment": equipment_name,
                "status": "DNS introuvable",
            }

    for case in json_data.get("items", []):
        equipement = case.get("equipement", "")

        # Traitement ONT
        if "ont" in equipement.lower():
            type_acces = case.get("type_acces", "")
            if "XGSP" in id_service and "NOKIA" in type_acces:
                continue
            resultats.append(traiter_ont(equipement))

        # Traitement Port de Livraison
        if "Port de Livraison" in case.get("type_acces", ""):
            equipment_name = equipement
            host = find_dns(equipment_name)
            port = case.get("port", "")
            equipment_info = version_alcatel_telco_one_access(host)
            type_equipement = equipment_info.get("equipment type", "inconnu")
            port_info = snmp_ipd_port(host, port, type_equipement)
            vpls = case.get("id_technique")
            snmp_vpls = snmp_ipd_vpls(host, vpls, type_equipement)
            resultats.append(
                {
                    "type": "Port de Livraison",
                    "equipment": equipment_name,
                    "host": host,
                    "port": port,
                    "equipment_type": type_equipement,
                    "port_info": port_info,
                    "VPLS": snmp_vpls,
                }
            )

        # Traitement OLT
        if "olt" in equipement.lower():
            data = get_Data_n_Process_FTTH(json_data, id_service)
            resultats.append({"type": "OLT", "equipment": equipement, "details": data})

    return resultats


# ============================Fonction Utilitaire
def verifier_format_port(port):
    return bool(re.match(r"^\d+/\d+/\d+/\d+/\d+$", port))


def extract_Port_Racco(snmp_ipd, port):
    # Vérification que snmp_ipd est un dictionnaire valide
    if snmp_ipd is not None and isinstance(snmp_ipd, dict):
        description = snmp_ipd.get(
            "description"
        )  # Utilisation de .get() pour éviter les erreurs de clé manquante

        # Vérification si la description existe et contient la chaîne 'interface-racco-vers-nte:'
        if description and isinstance(description, str):
            if "interface-racco-vers-nte:" in description:
                nte_name = description.split("interface-racco-vers-nte:")[
                    1
                ].strip()  # Récupération après le texte spécifié et suppression des espaces superflus
                # Vérifier si `nte_name` n'est pas vide après la découpe
                if nte_name:
                    # Vérifier que `port` est valide
                    if port:
                        Port_Racco = port
                        return nte_name, Port_Racco
                    else:
                        return None, "Port is invalid"
                else:
                    return None, "NTE name is empty"
            else:
                return None, "'interface-racco-vers-nte:' not found in description"
        else:
            return None, "Description is missing or invalid"
    else:
        return None, "Invalid SNMP IPD data"


def extract_validations(data):
    résultats = {}
    livraisons = {}

    def recurse(
        obj, equip_name=None, equip_type=None, type_acces=None, is_livraison=False
    ):
        if isinstance(obj, dict):
            # Détection des cas de livraison
            if "equipment_type_Liv" in obj or "Oam livraison" in obj:
                is_livraison = True
            if obj.get("type acces") == "Port de Livraison":
                is_livraison = True
                type_acces = "Port de Livraison"

            # Mise à jour du nom/type d'équipement
            if "equipment name" in obj:
                equip_name = obj["equipment name"]
            if "equipment_info" in obj and isinstance(obj["equipment_info"], dict):
                equip_type = obj["equipment_info"].get("equipment type", equip_type)

            for k, v in obj.items():
                # Cas des champs de validation
                if "Validation_" in k:
                    try:
                        flag = int(v)
                    except (TypeError, ValueError):
                        flag = 0
                    target_dict = livraisons if is_livraison else résultats
                    target_dict.setdefault(equip_name or "<inconnu>", {})[k] = flag

                # Cas OAM si type = ADVA ou 7x50
                if k.startswith("OAM_") and equip_type:
                    t = equip_type.lower()
                    if "7x50" in t or "adva" in t:
                        flag = 1 if "OK" in str(v).upper() else 0
                        résultats.setdefault(equip_name or "<inconnu>", {})[k] = flag

                recurse(v, equip_name, equip_type, type_acces, is_livraison)

        elif isinstance(obj, list):
            for item in obj:
                recurse(item, equip_name, equip_type, type_acces, is_livraison)

    recurse(data)

    # Validation globale
    all_flags = [flag for sous in résultats.values() for flag in sous.values()]
    global_validation = 1 if all_flags and all(f == 1 for f in all_flags) else 0

    # Indicateur s'il y a des champs invalides
    has_invalid_fields = any(f != 1 for f in all_flags)

    # Préparer les rapports de livraison
    delivery_reports = []
    for equip, vals in livraisons.items():
        erreurs = {k: v for k, v in vals.items() if v != 1}
        if erreurs:
            delivery_reports.append(
                {
                    "equipment": equip,
                    "status": "ALERTE",
                    "errors": erreurs,
                    "message": f"{len(erreurs)} champ(s) invalide(s)",
                }
            )
        else:
            delivery_reports.append(
                {
                    "equipment": equip,
                    "status": "INFO",
                    "message": "Tous les champs sont valides",
                }
            )

    return {
        "results": résultats,
        "global_validation": global_validation,
        "has_invalid_fields": has_invalid_fields,
        "delivery_reports": delivery_reports,
    }


# create a JSON file with results
def create_json(data):
    with open("./data/data2.json", "w") as outfile:
        return json.dumps(data, indent=2)
