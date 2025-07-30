# ================================================================================================================Bibliotheque
import subprocess
from zeep.transports import Transport
from zeep import Client
from zeep import xsd
import urllib3
import requests
import zeep  # Ajout de l'importation de zeep

import json
import re
import xml.etree.ElementTree as ET


from zeep import Client, xsd
from zeep.transports import Transport
from zeep.wsse.signature import Signature
from zeep.plugins import HistoryPlugin
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from scripts.Snmp_Ipd_Vpls import snmp_ipd_vpls
from scripts.FindDNS import find_dns

# Desactivation des messages d'alerte sur des commandes non sécurisées
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def diag_gpon(equipment, slot, port, onu_id, uni, subscriber_id, snmpset):

    ENDPOINT = "https://ws.m2m.axione.fr/wsdl/diagGpon.wsdl"

    # --------------------------------------------------------------------------------------------Creation de la session
    # Création d'une session pour maintenir l'état de la connexion
    session = requests.Session()

    # Désactivation de la vérification du certificat SSL (à utiliser avec précaution)
    session.verify = False

    # Configuration du proxy pour les requêtes HTTPS
    proxy_config = {"https": "http://10.1.80.5:80"}

    # Mise à jour des paramètres de proxy de la session
    session.proxies.update(proxy_config)

    # Configuration du transport avec la session
    transport = Transport(session=session, timeout=20)

    # Creation du client Zeep
    client = Client(ENDPOINT, transport=transport)

    # Définition d'un élément 'Header' avec un élément interne 'headerElement'
    header = xsd.Element(
        "Header",
        xsd.ComplexType(
            [
                xsd.Element("headerElement", xsd.String()),
            ]
        ),
    )

    # Création d'une instance de l'élément 'Header'
    header_value = header(headerElement="")

    # Convertion des paramètres en str
    equipment = str(equipment)
    slot = str(slot)
    port = str(port)
    onu_id = str(onu_id)
    uni = str(uni)
    subscriber_id = str(subscriber_id)
    snmpset = str(snmpset)

    # Récupération des paramètres et les placer dans les données de la requête
    request_data = {
        "equipment": equipment,
        "slot": slot,
        "port": port,
        "onu_id": onu_id,
        "uni": uni,
        "subscriber_id": subscriber_id,
        "snmpset": snmpset,
    }

    try:
        result = client.service.request(_soapheaders=[header_value], **request_data)

        # Vérifier si result est défini avant d'accéder à ses attributs
        if result:
            # Convertir les valeurs d'admin state et oper state en chaînes de caractères
            admin_state = str(result.adminstate_pon)
            oper_state = str(result.operstate_pon)

            return {
                "return code": result.return_code,
                "Admin state": admin_state,
                "oper state": oper_state,
                "slid": result.slid,
                "serial number": result.serial_number,
                "version": result.version,
                "version hardware": result.version_hardware,
                "type ont": result.type_ont,
                "Status ont": result.status_ont,
                "Admin state uni": result.adminstate_uni,
                "operstate uni": result.operstate_uni,
                "mac uni box": result.mac_uni_box,
                "rx signal level ont": result.rx_signal_level_ont,
                "tx signal level ont": result.tx_signal_level_ont,
                "rx sig level olt": result.rx_sig_level_olt,
                "distance": result.distance,
                "status subscriber id": result.status_subscriber_id,
                "ip subscriber id": result.ip_subscriber_id,
                "mac subscriber id": result.mac_subscriber_id,
                "sla subscriber id": result.sla_subscriber_id,
                "return snmpset": result.return_snmpset,
                "poe power": result.poe_power,
            }
        else:
            return "Result is undefined"
    except zeep.exceptions.Fault as e:
        return f"Error: {e}"


def diag_gpon_FTTHNCS(data, resultRefPro, id_service):
    resultMAC = Parameter_MAC(resultRefPro, id_service)

    resultats_livraison = []
    resultats_collecte = []
    use_snmp_ipd_vpls = id_service.endswith("_Details")

    if use_snmp_ipd_vpls:
        # === Gestion du port_livraison : unique ou liste ===
        port_livraison = resultMAC.get("port_livraison")
        if isinstance(port_livraison, dict):
            equipement = port_livraison.get("equipement")
            id_technique = port_livraison.get("id_technique")
            if equipement and id_technique:
                res_liv = snmp_ipd_vpls(equipement, id_technique, "")
                resultats_livraison.append({equipement: res_liv})
        elif isinstance(port_livraison, list):
            for port in port_livraison:
                equipement = port.get("equipement")
                id_technique = port.get("id_technique")
                if equipement and id_technique:
                    res_liv = snmp_ipd_vpls(equipement, id_technique, "")
                    resultats_livraison.append({equipement: res_liv})

        # === Gestion du port_collecte : unique ou liste ===
        port_collecte = resultMAC.get("port_collecte")
        if isinstance(port_collecte, dict):
            equipement = port_collecte.get("equipement")
            id_technique = port_collecte.get("id_technique")
            if equipement and id_technique:
                res_col = snmp_ipd_vpls(equipement, id_technique, "")
                resultats_collecte.append({
                    equipement: {
                        "MAC_SAP": res_col.get("MAC_SAP"),
                        "SVLAN": port_collecte.get("SVLAN", ""),
                        "community": port_collecte.get("community", "")
                    }
                })
        elif isinstance(port_collecte, list):
            for port in port_collecte:
                equipement = port.get("equipement")
                id_technique = port.get("id_technique")
                if equipement and id_technique:
                    res_col = snmp_ipd_vpls(equipement, id_technique, "")
                    resultats_collecte.append({
                        equipement: {
                            "MAC_SAP": res_col.get("MAC_SAP"),
                            "SVLAN": port.get("SVLAN", ""),
                            "community": port.get("community", "")
                        }
                    })

    # === Appel SOAP ===
    json_payload = json.dumps(data)

    session = requests.Session()
    session.verify = False
    session.proxies.update({"https": "http://10.1.80.5:80"})

    transport = Transport(session=session, timeout=120)
    history = HistoryPlugin()

    wsdl_url = "https://ws.m2m.axione.fr/wsdl/diagGpon.wsdl"

    try:
        client = Client(wsdl=wsdl_url, transport=transport, plugins=[history])
    except Exception as e:
        print(f"[ERROR] Impossible de charger le client SOAP : {e}")
        return {
            "code": 0,
            "error": f"Erreur chargement client SOAP : {e}",
            "data": data,
            "resultats_livraison": resultats_livraison,
            "resultats_collecte": resultats_collecte,
        }

    header = xsd.Element(
        "Header",
        xsd.ComplexType([
            xsd.Element("headerElement", xsd.String()),
        ])
    )
    header_value = header(headerElement="")

    try:
        response = client.service.request_new(
            _soapheaders=[header_value], json_input=json_payload
        )

        if history.last_received:
            envelope_xml = ET.tostring(history.last_received["envelope"], encoding="utf-8")
            root = ET.fromstring(envelope_xml)

            namespaces = {
                "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
                "diag": "http://ws.m2m.axione.fr/diagGpon",
            }

            json_element = root.find(".//diag:json", namespaces)
            if json_element is not None and json_element.text:
                data_json = json.loads(json_element.text)
                return {
                    "data": data_json,
                    "resultats_livraison": resultats_livraison,
                    "resultats_collecte": resultats_collecte,
                }

        return {
            "error": "Réponse SOAP vide ou invalide",
            "data": data,
            "resultats_livraison": resultats_livraison,
            "resultats_collecte": resultats_collecte,
            "resultMAC": resultMAC,
        }

    except Exception:
        try:
            if history.last_received:
                envelope_str = ET.tostring(
                    history.last_received["envelope"], encoding="utf-8"
                ).decode("utf-8")
                result = extraire_contenu_json(envelope_str)
                data_json = json.loads(result)
                return {
                    "data": data_json,
                    "Json_Build": data,
                    "resultats_livraison": resultats_livraison,
                    "resultats_collecte": resultats_collecte,
                    "resultMAC": resultMAC,
                }
        except Exception:
            return {
                "error": "Erreur : aucune réponse SOAP",
                "data": data,
                "resultats_livraison": resultats_livraison,
                "resultats_collecte": resultats_collecte,
                "resultMAC": resultMAC,
            }


proxy_config = {"https": "http://10.1.80.5:80"}


def get_data_refpro(id_service):

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


def get_commentaire_data(data):
    if len(data.get("items", [])) > 0 and "commentaire" in data["items"][0]:
        data_commentaire = data["items"][0]["commentaire"]
        if not data_commentaire or not isinstance(data_commentaire, str):
            return {"uni": {}}

        try:
            sections = re.split(r"\s*(?=UNI\s+\d+\s+-)", data_commentaire)
        except Exception as e:
            return {"uni": {}}

        lignes = [ligne.strip() for ligne in sections if ligne.strip()]
        results = {"uni": {}}
        for ligne in lignes:
            match = re.match(
                r"UNI (\d+) - Type: ([^-]+) - Livraison: [^-]+ - Profil: ([^-]+) - Class: (\S+)",
                ligne,
            )
            if match:
                uni_id = match.group(1)
                type_source = match.group(2).strip()
                profil = match.group(3).strip()
                classe = match.group(4).strip()

                type_trad = {"Camera": "Camera", "Infrarouge": "Infrarouge"}.get(
                    type_source, type_source
                )
                class_trad = {"video_unicast": "Video unicast"}.get(classe, classe)

                prof_match = re.match(r"(\d+)/(\d+)", profil)
                if prof_match:
                    download = prof_match.group(1)
                    upload = prof_match.group(2)
                else:
                    download = ""
                    upload = ""

                results["uni"][uni_id] = {
                    "profil": {
                        "commande": {
                            "upload": upload,
                            "type": type_trad,
                            "class": class_trad,
                            "download": download,
                        }
                    }
                }
        return results
    else:
        return {"uni": {}}


def extract_port_parts(port_str):
    try:
        parts = port_str.strip().split("/")
        if len(parts) >= 3:
            # On prend les 3 derniers éléments
            slot, port, onu = parts[-3], parts[-2], parts[-1]
            return slot, port, onu
    except Exception:
        pass

    return "", "", ""


def get_data(data, id_service):
    commentaire_data = get_commentaire_data(data)
    if not isinstance(commentaire_data, dict):
        commentaire_data = {"uni": {}}

    items = data.get("items", [])
    if not items:
        return {}

    # Port OLT (non SPOF) utilisé pour extraire les infos de port/slot/onu
    olt_item = next(
        (
            item
            for item in items
            if item.get("equipement", "").lower().startswith("olt")
            and item.get("port", "").upper() != "SPOF"
        ),
        None,
    )

    # Initialisation de la structure tronc_livraison
    tronc_livraison = []

    # Extraction des ports de livraison avec lag == 55
    tronc_items_with_lag = [
        item
        for item in items
        if item.get("type_acces") == "Port de Livraison" and item.get("lag") == 55
    ]

    # Construction de la liste détaillée avec le bon champ
    tronc_livraison = [
        {
            "equipement": item.get("equipement", ""),
            "port": item.get("port", ""),
            "tronc": item.get("interface_livraison_camera", ""),
        }
        for item in tronc_items_with_lag
    ]

    # UNIs
    uni_ids_list = list(commentaire_data.get("uni", {}).keys())
    uni_ids = ";".join(sorted(uni_ids_list, key=int)) if uni_ids_list else ""

    port_str = olt_item.get("port", "") if olt_item else ""
    slot, port_num, onu = extract_port_parts(port_str)

    resultat = {
        "id_service": id_service,
        "ws": "ws-diag-gpon",
        "port": port_num,
        "olt": olt_item.get("equipement") if olt_item else "",
        "uni_id": uni_ids,
        "tronc_livraison": tronc_livraison,
        "uni": commentaire_data.get("uni", {}),
        "subscriber_id": id_service,
        "onu_id": onu,
        "slot": slot,
    }
    return resultat


def FTTHNCS_JSON(id_service):
    resultRefPro = get_data_refpro(id_service)
    result = get_data(resultRefPro, id_service)
    return result, resultRefPro


def extraire_contenu_json(data):
    namespaces = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "diagGpon": "diagGpon",
    }
    try:
        root = ET.fromstring(data)
        json_element = root.find(".//diagGpon:json", namespaces)
        if json_element is not None:
            return json_element.text
        else:
            return None  # ou une erreur personnalisée
    except ET.ParseError:
        return None  #


def diag_gpon_NCS(id_service):
    id_service_clean = id_service.replace("_Details", "")
    data, resultRefPro = FTTHNCS_JSON(id_service_clean)
    # Appel de la fonction (à noter que diag_gpon est une fonction, donc il faut l'appeler)
    Retour = diag_gpon_FTTHNCS(data, resultRefPro,id_service)
    NCS_List = []
    NCS_List.append(Retour)

    return NCS_List

def Parameter_MAC(data, id_service):
    items = data.get("items", [])

    # 1. Récupérer les informations des UNIs depuis les commentaires
    commentaire_data = get_commentaire_data(data)
    uni_data = commentaire_data.get("uni", {})

    svlan = ""
    community = ""

    # Gestion des ports de livraison
    if "COVP" in id_service:
        # Plusieurs ports de livraison pour COVP (lag == 55 et type_acces Port de Livraison)
        tronc_items = [
            item
            for item in items
            if item.get("lag") == 55 and item.get("type_acces", "") == "Port de Livraison"
        ]
    else:
        # Cas standard : un seul port de livraison OLT (max id_technique)
        tronc_items = [
            item
            for item in items
            if item.get("equipement", "").lower().startswith("olt")
            and item.get("type_acces") == "Port de Livraison"
        ]

    # Sélectionner le(s) port(s) de livraison
    if "COVP" in id_service:
        # Liste complète
        port_livraison = [
            {
                "equipement": find_dns(item.get("equipement")),
                "id_technique": item.get("id_technique"),
            }
            for item in tronc_items
        ] if tronc_items else None

        # Extraction community et svlan à partir du premier port de livraison
        if tronc_items:
            commentaire_id_tech = tronc_items[0].get("commentaire_id_tech", "")
            match = re.search(r"Community\s+(\d+)", commentaire_id_tech)
            community = match.group(1) if match else ""

            match = re.search(r"SVLAN\s+(\d+)", commentaire_id_tech)
            svlan = match.group(1) if match else ""
    else:
        # Un seul port (celui avec le plus grand id_technique)
        tronc_item = max(tronc_items, key=lambda x: x.get("id_technique", 0)) if tronc_items else None

        port_livraison = None
        if tronc_item:
            port_livraison = {
                "equipement": find_dns(tronc_item.get("equipement")),
                "id_technique": tronc_item.get("id_technique"),
            }
            commentaire_id_tech = tronc_item.get("commentaire_id_tech", "")
            match = re.search(r"Community\s+(\d+)", commentaire_id_tech)
            community = match.group(1) if match else ""

            match = re.search(r"SVLAN\s+(\d+)", commentaire_id_tech)
            svlan = match.group(1) if match else ""

    # Gestion des ports de collecte (même pour tous les cas)
    collecte_items = [
        item
        for item in items
        if (
            (item.get("equipement", "").lower().startswith("olt") or item.get("lag") == 55)
            and item.get("port", "").upper() != "SPOF"
            and (
                ("COVP" in id_service and item not in tronc_items)
                or ("COVP" not in id_service and item != tronc_item)
            )
        )
    ]

    collecte_item = max(collecte_items, key=lambda x: x.get("id_technique", 0)) if collecte_items else None

    port_collecte = None
    if collecte_item:
        port_collecte = {
            "equipement": find_dns(collecte_item.get("equipement")),
            "id_technique": collecte_item.get("id_technique"),
            "SVLAN": svlan,
            "community": community,
        }

    # Construction finale du résultat
    result = {
        "port_livraison": port_livraison,
        "port_collecte": port_collecte,
    }

    # Traitement des UNIs
    if uni_data:
        unis = {}
        for uni_id, infos in uni_data.items():
            cmd = infos.get("profil", {}).get("commande", {})
            unis[uni_id] = {
                "type": cmd.get("type", ""),
                "class": cmd.get("class", ""),
                "download_Mbps": cmd.get("download", ""),
                "upload_Mbps": cmd.get("upload", ""),
            }
        result["unis"] = unis
    else:
        result["unis"] = {}

    return result
