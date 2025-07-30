# -*- coding: utf-8 -*-

# 
# @file		Commeett.py
#

# LIBRAIRIES
import requests, json, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# VARIABLES
AX_PROXY = "proxy.query.consul:80"

def Commeett(enterprise_name):
    results = {}
    try:
        token = get_token()
        id_enterprise = get_id_enterprise(token, enterprise_name)

        if id_enterprise:
            status_data = fetch_statuses(token, id_enterprise)
            phone_data = fetch_phones(token, id_enterprise)
            results = match_phones_with_statuses(phone_data, status_data)
        else:
            results = { 'error': f"{enterprise_name} non référencé dans la plateforme Commeett ou ne possède pas le bon nom." }
        #
    #

    except Exception as e:
        results = { 'error': f"{e}." }
    #

    return results
#

def get_token():
    url = "https://voip-en01.telephonie.essonnenumerique.com/api/token"
    proxies = {
        "http": f"{AX_PROXY}",
        "https": f"{AX_PROXY}",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cHVibGljLWFwaTo="
    }
    data = {
        "grant_type": "password",
        "username": "ame-active@axione.fr",
        "password": "Ame@Pyrite64",
        "scope": ""
    }
    response = requests.post(url, headers=headers, data=data, proxies=proxies, verify=False)
    response.raise_for_status()
    return response.json()["access_token"]
#

def fetch_statuses(token, enterprise_id):
    url = f"https://voip-en01.telephonie.essonnenumerique.com/realtime/topics/lines?enterprise={enterprise_id}&token={token}&ngsw-bypass=true"
    proxies = {
        "http": f"{AX_PROXY}",
        "https": f"{AX_PROXY}",
    }
    headers = {
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, proxies=proxies, verify=False, stream=True)
    response.raise_for_status()

    for line in response.iter_lines():
        if line and line.startswith(b"data:"):
            try:
                payload = line.decode().removeprefix("data:").strip()
                return json.loads(payload)
            except Exception as e:
                print("Erreur de parsing JSON:", e)
                return {}
    return {}
#

def fetch_phones(token, enterprise_id):
    url = "https://voip-en01.telephonie.essonnenumerique.com/api/phones"
    proxies = {
        "http": f"{AX_PROXY}",
        "https": f"{AX_PROXY}",
    }
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    params = {
        "order[inUsePorts]": "asc",
        "exclude-not-allocatable": "true",
        "resources-for-enterprise": enterprise_id, # Utilisation de l'ID de l'entreprise
        "page": "1"
    }
    response = requests.get(url, headers=headers, params=params, proxies=proxies, verify=False)
    response.raise_for_status()
    return response.json()
#

def get_id_enterprise(token, enterprise_name):
    url = "https://voip-en01.telephonie.essonnenumerique.com/api/enterprises"
    proxies = {
        "http": f"{AX_PROXY}",
        "https": f"{AX_PROXY}",
    }
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    params = {
        "name": enterprise_name
    }
    response = requests.get(url, headers=headers, params=params, proxies=proxies, verify=False)
    response.raise_for_status()
    enterprises = response.json()
    if enterprises:
        return enterprises[0].get('id')
    #
    return None
#

def match_phones_with_statuses(phones_data, statuses_data):
    known_lines = {}
    results = {
        "connected": [],
        "not_connected": [],
        "unknown": []
    }

    for outer_key, inner_dict in phones_data.items():
        if isinstance(inner_dict, dict):
            for inner_key, phone in inner_dict.items():
                if isinstance(phone, dict):
                    mac = phone.get("mac", "MAC inconnue")

                    phone_type = phone.get("phoneType", {})
                    phone_name = phone_type.get("name", "Nom de téléphone inconnu")

                    phone_ports = phone.get("phonePorts", [])
                    for port in phone_ports:
                        line = port.get("line", {})
                        pv_number = line.get("privateNumber")
                        pb_number = line.get("publicNumbers")
                        line_name = line.get("name")
                        if pv_number:
                            known_lines[str(pv_number)] = {
                                "mac": mac,
                                "phone_name": phone_name,
                                "private_line": str(pv_number),
                                "public_line": str(pb_number[0].get('number')) if pb_number else None,
                                "line_name": line_name
                            }
                        #
                    #
                #
            #
        #
    #

    voip_numbers = set()
    for status in statuses_data.get("statuses", []):
        pv_number = str(status.get("privateNumber", ""))
        is_connected = status.get("isConnected", False)
        voip_numbers.add(pv_number)

        if pv_number in known_lines:
            line_info = known_lines[pv_number]
            entry = {
                "mac": line_info["mac"],
                "private": line_info["private_line"],
                "public": line_info["public_line"],
                "name": line_info['line_name'],
                "type_tel": line_info['phone_name']
            }
            if is_connected:
                results["connected"].append(entry)
            else:
                results["not_connected"].append(entry)
            #
        #
    #

    for pv_number, line_info in known_lines.items():
        if pv_number not in voip_numbers:
            entry = {
                "mac": line_info["mac"],
                "private": line_info["private_line"],
                "public": line_info["public_line"],
                "name": line_info['line_name'],
                "type_tel": line_info['phone_name']
            }
            results["unknown"].append(entry)
        #
    #

    return results
#

print(Commeett('HOTEL DE VILLE ( LE MEREVILLOIS)'))
