# -*- coding: utf-8 -*-

# 
# @file	    AddCheckTools.py
#

# LIBRAIRIES
import subprocess, socket, mysql.connector, re, requests
from mysql.connector import Error
from zeep import Client
from zeep.exceptions import Fault
from requests.auth import HTTPBasicAuth
from scripts.Salesforce import QuerySF
from scripts.Get_equipment_ws import GetEquipementPSS
from scripts.FindDNS import find_dns
from scripts.GetIp import get_ip

# METHODES

# Check d'un device dans Spectrum
def DeviceInSpectrum(equipement, communaute):
    user, password = 'api_spectrum', "Lg27w6Wv"
    url = ''
    equipement = find_dns(equipement)
    dsp_match = re.search(r'(\w{3}).axione.fr', equipement)
    ihub = False

    if communaute == 'ihub':
        ihub = True
    
    if dsp_match:
        dsp = dsp_match.group(1)
    else:
        return { 'spectrum': f"Domain {equipement}.axione.fr inconnu de Spectrum ou non pris en compte par le script" }
    #

    landscape_map = {
        "0x2000000": ["adn", "lim", "ain", "bcb", "blz", "cap", "cha", "emo", "ext", "fin", "jur", "lna", "loi", "mtr", "nie", "npc", "rbx", "t72", "th2", "tfo", "infra", "ctf", "hsn", "uki", "sqy"],
        "0x3000000": ["adf", "ais", "amp", "art", "bfo", "bou", "cfe", "gab", "gon", "hpy", "lan", "mal", "mel", "odi", "par", "pau", "qui", "sar", "tou", "vau", "vie", "wimax", "y78", "eur", "enn", "lat", "urw", "mgr", "enu"]
    }

    if ihub:
        url = f"http://spectrum.m2m.axione.fr/spectrum/restful/devices?attr=0x1006e&attr=0x12c03&throttlesize=10000&landscape=0x5000000"
    else:
        landscape = next((key for key, values in landscape_map.items() if dsp in values), None)

        if landscape is None:
            return { 'spectrum': f"Domaine {dsp}.axione.fr inconnu de Spectrum ou non pris en compte par le script" }
        #

        url = f"http://spectrum.m2m.axione.fr/spectrum/restful/devices?attr=0x1006e&attr=0x12c03&throttlesize=10000&landscape={landscape}"
        
        if dsp == "mtr":
            url = "http://spectrum.m2m.axione.fr/spectrum/restful/devices?attr=0x1006e&attr=0x12c03&throttlesize=10000"
        #
    #

    try:
        response = requests.get(url, auth=HTTPBasicAuth(user, password), timeout=20)
        content = response.text

        if equipement in content:
            if "preprod" in content.split(equipement)[1].split("model")[0]:
                if ihub:
                    return { 'spectrum ihub': f"{equipement} dans Spectrum en preprod" }
                else:
                    return { 'spectrum': f"{equipement} dans Spectrum en preprod" }
                #
            else:
                if ihub:
                    return { 'spectrum ihub': f"{equipement} dans Spectrum en prod" }
                else:
                    return { 'spectrum': f"{equipement} dans Spectrum en prod" }
                #
            #
        else:
            if ihub:
                return { 'spectrum ihub': f"{equipement} absent de Spectrum" }
            else:
                return { 'spectrum': f"{equipement} absent de Spectrum" }
            #
        #
    except requests.RequestException as e:
        return { 'spectrum': f"Erreur lors de la requête à Spectrum : {e}" }
    #
#

# Ajout d'un device dans Spectrum
def AddInSpectrum(ip, equipement, communaute):
    user, password = 'api_spectrum', "Lg27w6Wv"
    equipement = find_dns(equipement)
    dsp_match = re.search(r'(\w{3}).axione.fr', equipement)
    ihub = False
    landscape, mh_container = '', ''

    if communaute == 'ihub':
        ihub = True
    #
    
    if dsp_match:
        dsp = dsp_match.group(1)
    else:
        return { 'spectrum': f"Domain {equipement}.axione.fr inconnu de Spectrum ou non pris en compte par le script" }
    #

    # Connexion à la base de données
    conn = mysql.connector.connect(host="10.1.80.229", user="spectrum", password="spectrum", database="spectrum")
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT spectroserver, landscape, mh_container FROM new_container_dsp WHERE dsp = '{dsp}';")
    result = cursor.fetchone()

    if result:
        landscape = result['landscape']
        mh_container = result['mh_container']
    else:
        if ihub:
            return { 'spectrum ihub ajout': f"{equipement} échec requête bdd Spectrum" }
        else:
            return { 'spectrum ajout': f"{equipement} échec requête bdd Spectrum" }
        #
    #

    cursor.close()
    conn.close()
    url = f"https://spectrum.m2m.axione.fr/spectrum/restful/model?landscapeid={landscape}&agentport=161&ipaddress={ip}&attr=0x1006e&val={equipement}&parentmh={mh_container}&commstring=%23v2%2f{communaute}&attr=0x12c03&val=preprod&retry=1&timeout=1000"
    response = requests.post(url, auth=(user, password), proxies={'https': 'http://10.1.80.5:80'}, timeout=20)

    if 'error="Success"' in response.text:
        if ihub:
            return { 'spectrum ihub ajout': f"{equipement} ajout dans Spectrum OK" }
        else:
            return { 'spectrum ajout': f"{equipement} ajout dans Spectrum OK" }
        #
    else:
        if ihub:
            return { 'spectrum ihub ajout': f"{equipement} échec ajout dans Spectrum" }
        else:
            return { 'spectrum ajout': f"{equipement} échec ajout dans Spectrum" }
        #
    #    
#

# Ajout d'un device dans Cacti
def AddInCacti(description, ip, template, avail, version, community, id):
    NAMESPACE = 'https://ws-cacti.m2m.axione.fr/cacti/'
    ENDPOINT = 'https://ws-cacti.m2m.axione.fr/cacti/'

    description = description.replace('.axione.fr', '')
    soap = None
    client = Client(wsdl=ENDPOINT, transport=None)
    soap = client.create_service(f"{NAMESPACE}wsdl", ENDPOINT)

    if soap:
        try:
            som = soap.addDevice(description=description, ip=ip, template=template, avail=avail, version=version, community=community, id=id)
            codeRetour, intitulecodeRetour = som.result, som.paramsout

            if id == 0:
                if intitulecodeRetour == "Success":
                    return { 'cacti ajout': f"Ajout OK du device {description} dans cacti" }
                else:
                    return { 'cacti ajout': f"Ajout KO du device {description} dans cacti" }
            elif id > 0:
                return { 'cacti ajout': "Verbose query OK" }
            #

        except Fault as e:
            return { 'cacti ajout': str(e) }
        #
    else:
        return { 'cacti ajout': "Impossible de se connecter à Cacti" }
    #
#

# Check d'un device dans Cacti
def DeviceInCacti(equipement, ip, type):
    user, password = "geco", "ot=aiRe1du"
    equipement = find_dns(equipement).replace('.axione.fr', '')

    try:
        connection = mysql.connector.connect(
            host="10.1.81.99",
            database="cacti",
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            host_template_id_test = { "T280": 30, "ADVA": 56, "NE20": 82, "NE05": 96, "7360": 79, "MA5800": 90, "IPD": 42, "NE8000": 104, "CISCO": 10, "MX480": 83 }.get(type, None)

            query = f"SELECT * FROM host WHERE description like '%{equipement}%'"
            cursor.execute(query)
            row = cursor.fetchone()

            if not row:
                return { 'cacti': f"Le device {equipement} n'est pas dans cacti" }, None
            elif row['description'].find(equipement) != -1 and ip != row['hostname']:
                return { 'cacti': f"Le device {row['description']} est dans cacti mais avec une mauvaise ip : {row['hostname']}" }, row['id']
            elif row['description'].find(equipement) != -1 and ip == row['hostname'] and host_template_id_test != row['host_template_id']:
                return { 'cacti': f"Le device {row['description']} est dans cacti mais avec un mauvais Host Template" }, row['id']
            elif row['description'].find(equipement) != -1 and ip == row['hostname']:
                return { 'cacti': f"Le device {row['description']} est bien dans cacti" }, row['id']
            #

            cursor.close()
            connection.close()
        #
    except Error as e:
        return { 'cacti': str(e) }, None
    #
#

# Ajout d'un device dans Netbox
def DeviceInNetbox(equipement, ip, model):
    return_value = None
    netbox = []

    if equipement and ip and model:
        equipement_complet = equipement + '.axione.fr'
        donnees_brut_site_pss = GetEquipementPSS(equipement)
        donnees_brut_site_pss = re.sub(r'\{\}\[\]\"', '', donnees_brut_site_pss)
        
        site_equipement_complet = None
        if 'ABONNE' in netbox:
            site_equipement_complet = netbox['ABONNE']
        else:
            match = re.search(r'code_reference:([^,]+),type_de_site', donnees_brut_site_pss)
            if match:
                site_equipement_complet = match.group(1)
            #
        #
        
        if site_equipement_complet:
            site_equipement_complet = site_equipement_complet.replace('  ', ' ')
            site_equipement_complet = re.sub(r',autre_identifiant_site\:.*', '', site_equipement_complet)
        #
        
        geograf = "0.000000,0.000000"
        match = re.search(r'gpscoord1:(\d+\.\d+),gpscoord2:(\d+\.\d+),code_reference', donnees_brut_site_pss)
        if match:
            geograf_lat, geograf_lon = match.group(1), match.group(2)
            geograf_lat = re.search(r'(\d+\.\d{6})', geograf_lat).group(1)
            geograf_lon = re.search(r'(\d+\.\d{6})', geograf_lon).group(1)
            geograf = f"{geograf_lat},{geograf_lon}"
        #
        
        snmp_requis = 'oui'
        if re.search(r'(utl|clm|lgw|tmp)-', equipement):
            snmp_requis = 'non'
        #

        query = QuerySF(f"SELECT ADRESSE_1__c, CP__c FROM Prise_de_Commande__c WHERE Name = '{netbox['PDC']}'")
        client_addr = query.get("ADRESSE_1__c")
        client_cp = query.get("CP__c")
        
        if 'ACTION' not in netbox:
            netbox['ACTION'] = 'ajout'
        #
        
        if re.search(r'(nte|nce)-', equipement_complet) and not re.search(r'T-Marc|NE05|NE8000|GE\d+|XG\d+', netbox.get('TYPE_EQUIPEMENT', '')):
            netbox['TYPE_EQUIPEMENT'] = None
        #
        
        if geograf == '0.000000,0.000000':
            netbox['PATTERN'] = f"name={equipement_complet} ip={ip} type={netbox.get('TYPE_EQUIPEMENT')} site={site_equipement_complet} snmp={snmp_requis} action={netbox['ACTION']} geograf={geograf}"
        else:
            netbox['PATTERN'] = f"name={equipement_complet} ip={ip} type={netbox.get('TYPE_EQUIPEMENT')} site={site_equipement_complet} snmp={snmp_requis} action={netbox['ACTION']} geograf={geograf} addr={client_addr} cp={client_cp}"
        #
        
        r_cmd = subprocess.getoutput(f"python3 /usr/local/scripts/geco/script_add_in_netbox.py \"{netbox['PATTERN']}\"")
        r_cmd = r_cmd.replace('\n', '').replace('\r', '').replace('{', '').replace('}', '').replace('[', '').replace(']', '').replace('\"', '')
        
        if re.search(r'Successfully (created|updated)', r_cmd):
            return_value = f"OK;{equipement_complet};{ip};{netbox.get('TYPE_EQUIPEMENT')};{site_equipement_complet};{snmp_requis};{netbox['ACTION']};{geograf} => {r_cmd}"
        else:
            return_value = f"KO;{equipement_complet};{ip};{netbox.get('TYPE_EQUIPEMENT')};{site_equipement_complet};{snmp_requis};{netbox['ACTION']};{geograf} => {r_cmd}"
        #
    else:
        return { 'netbox': 'Equipement, IP ou model manquant' }
    #
    
    return { 'netbox': return_value }
#