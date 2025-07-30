import sys
import re
import subprocess
import time
from datetime import datetime, timedelta
import json

def snmp_ipd_vpls(equipement, vpls, type_equipement):
    import subprocess
    import re
    import time
    from datetime import datetime, timedelta

    commande = ""
    resultat = ""
    result = ""
    mac = ""
    peer = ""
    port_vlan = ""
    temps_total = 0
    mac_et_port = ""
    tab_text = []
    MAC_SAP = []
    MAC_SDP = []

    slot_to_card = {
        "1/1/5": "1/1/1",
        "1/1/6": "1/1/2",
        "1/1/7": "1/1/3",
        "1/1/8": "1/1/4",
        "1/1/9": "1/1/5",
        "1/1/10": "1/1/6",
        "1/1/11": "1/1/7",
        "1/1/12": "1/1/8",
    }

    if any(ne in type_equipement for ne in ["NE20", "NE40", "NE8000"]):
        print("PAS DISPONIBLE POUR LE MOMMENT")
        return

    oid = f".1.3.6.1.4.1.6527.3.1.2.4.2.4.1.11.{vpls}"
    result = net_snmpwalk(equipement, oid)
    lines = result.split("\n")

    for line in lines:
        if line.strip():
            parts = line.split("=")
            macdecimal_part = parts[0].strip()
            MACdec = macdecimal_part.split(".")
            if len(MACdec) < 17:
                print(f"Erreur : Pas assez d'éléments pour la MAC décimale dans {macdecimal_part}")
                continue

            MACdecimal = ".".join(MACdec[-6:])
            MAC = [hex(int(x))[2:].zfill(2) for x in MACdec[-6:]]
            MAChex = ":".join(MAC)

            commande = f"snmpwalk -c cpdea -v2c {equipement} 1.3.6.1.2.1.1.3.0"
            result = subprocess.getoutput(commande)
            match = re.search(r"Timeticks: \((\d+)\)", result)
            time_uptime = int(match.group(1))
            time_now = int(time.time())

            match = re.search(r"\((.*?)\)", line)
            time_vpls = int(match.group(1))
            time_calcul = int(time_uptime) - int(time_vpls)
            time_calcul = int(time_now) - (int(time_calcul) / 100) + 1
            dt_calcule = datetime.fromtimestamp(time_calcul) + timedelta(seconds=1)
            date_test = dt_calcule.strftime("%m/%d/%Y %H:%M:%S")

            result = Getportnum(vpls, MACdecimal, equipement)
            port_num = traitement_result(result)

            result = GetVlan(vpls, MACdecimal, equipement)
            vlan = traitement_result(result)

            vpls_oid = (
                f".1.3.6.1.4.1.6527.3.1.2.4.2.4.1.7.{vpls}.{MACdecimal}"
            )
            result = net_snmp(equipement, vpls_oid)
            sdp = traitement_result(result)

            port_nom = ""
            resultat = obtenir_resultat_snmp(equipement)
            lines_port = resultat.strip().split("\n")

            for line_port in lines_port:
                if f"iso.3.6.1.2.1.2.2.1.2.{port_num}" in line_port:
                    port_num_part = (
                        line_port.split("STRING:")[1]
                        .strip()
                        .split(",")[0]
                        .strip()
                    )
                    if ":" in port_num_part:
                        parts = port_num_part.split(":")
                        lt = parts[0]
                        rest_value = parts[1]
                        port_final = slot_to_card.get(rest_value)
                        port_nom = lt + ":" + port_final
                    else:
                        port_nom = port_num_part
                    break

            if port_nom and port_nom != "0":
                source_id = f"sap:{port_nom}:{vlan}"
                MAC_SAP.append({
                    "Adresse MAC": MAChex,
                    "Source identifier": source_id,
                    "Date": date_test,
                    "MAC DECIMAL": MACdecimal,
                    "Equipement": equipement,
                    "VPLS": vpls,
                    "Type Equipement": type_equipement
                })
            else:
                source_id = f"sdp:{sdp}:{vpls}"
                MAC_SDP.append({
                    "Adresse MAC": MAChex,
                    "Source identifier": source_id,
                    "Date": date_test,
                    "MAC DECIMAL": MACdecimal,
                    "Equipement": equipement,
                    "VPLS": vpls,
                    "Type Equipement": type_equipement
                })

    return {
        "MAC_SAP": MAC_SAP,
        "MAC_SDP": MAC_SDP
    }


def traitement_donnee(line):
    match = re.search(r"=.*?(\d+ days, \d+:\d+:\d+\.\d+)$", line)
    if match:
        return match.group(1).strip()
    else:
        return None


def traitement_result(result):
    decoded_data = result.decode("utf-8")
    lines = decoded_data.split("\n")

    for line in lines:
        parts = line.split("=", 1)
        if len(parts) > 1:
            subparts = parts[1].split(":", 1)
            if len(subparts) > 1:
                return subparts[1].strip()


def net_snmpwalk(ip_equipement, oid):
    community = "ihub" if ip_equipement.startswith("olt") else "cpdea"
    command = ["snmpwalk", "-c", community, "-v2c", ip_equipement, oid]
    result = subprocess.run(command, stdout=subprocess.PIPE, universal_newlines=True)
    return result.stdout


def net_snmp(ip_equipement, oid):
    community = "ihub" if ip_equipement.startswith("olt") else "cpdea"
    command = ["snmpget", "-c", community, "-v2c", ip_equipement, oid]
    result = subprocess.run(command, stdout=subprocess.PIPE)
    return result.stdout.strip()


def Getportnum(vpls, MACdecimal, equipement):
    vpls_oid = (
        f".1.3.6.1.4.1.6527.3.1.2.4.2.4.1.5.{vpls}.{MACdecimal}"
    )
    result = net_snmp(equipement, vpls_oid)
    return result


def GetVlan(vpls, MACdecimal, equipement):
    vpls_oid = (
        f".1.3.6.1.4.1.6527.3.1.2.4.2.4.1.6.{vpls}.{MACdecimal}"
    )
    result = net_snmp(equipement, vpls_oid)
    return result


def obtenir_resultat_snmp(equipement):
    community = "ihub" if equipement.startswith("olt") else "cpdea"
    commande = f"snmpwalk -c {community} -v2c {equipement} 1.3.6.1.2.1.2.2.1.2"
    resultat = subprocess.getoutput(commande)
    return resultat
