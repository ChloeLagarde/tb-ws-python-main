# -*- coding: utf-8 -*-

# 
# @file		ServiceEssonne.py
#

# LIBRAIRIES
import requests, json, re, os, subprocess, shutil, mysql.connector, random, string
from datetime import datetime
import xml.etree.ElementTree as ET
from mysql.connector import connection
from scripts.SSH import *
from scripts.Commeett import *

# VARIABLES
AIR_URL = "https://api.airtable.com/v0/"
AIR_TOKEN_ENU = "pat9kcTXAnla1VhIC.fc80a5c2a4fe359d02b1ff1b9b265df3f1619e7cc0d27b40a6691556a47ce7f6"
AIR_TOKEN_DIF = "patOZV1LCse7av2rT.2f5315543caa5a07eecdd49a308159b882721eca192ff8116e87dc1edf17f1c6"

GIT_URL = "https://gitlab.m2m.axione.fr/axione-dif-ingenierie/essonne-numerique"
GIT_TOKEN = "glpat-ywGWr3r_aK7Jb2v87JYy"

AX_PROXY = "proxy.query.consul:80"

RDB_USER = "ame"
RDB_PASS = "-G4xVj43="

results = { # Tableau des résultats retournés sur l'API
    'configs': {
        'vpnl2': None,
        'ports': None,
        'vpnip': None,
        'qos': None
    },
    'rsp': {
        'acces': {
            'status': None,
            'pe': None,
            'cpe': None
        },
        'service': {
            'status': None,
            'pe': None,
            'cpe': None,
            'vprn': None,
            'ipoe subscriber': None,
            'ipoe vprn hub': None,
            'ipoe vprn spoke': None,
            'ipoe subnet': None,
            'ipoe': None,
            'vpnl2': None,
            'lwm': None,
            'voip': None
        }
    },
    'acces': {
        'ip': None,
        'login': None,
        'password': None,
        'radius': None
    },
    'service': {
        'ip': None,
        'login': None,
        'password': None,
        'radius': None
    },
    'commeett': {}
}

# METHODES

# Publics

# Vérifier les téléphones Commeett
# @param: str
# @return: json
def check_service_voip_commeett(service_voip_id):
    global results

    acces_id_match = re.search(r'ESNU\-VOIP\-\d+', service_voip_id)

    if acces_id_match:
        j_data = airtable('appeoq8CRibQP538a/tblVi8SozQWiduxmI?', 'filterByFormula=fldjz6DiiQgnojlNJ%3D%22' + service_voip_id + '%22&view=viwS8W850FyIWCuvL') # Airtable get table services

        if 'records' in j_data and j_data['records']:
            for record in j_data['records']:
                if record['fields']:
                    ligne = record['fields']

                    results['commeett'] = Commeett(ligne['nom_site'])
                #
            #
        #
        else:
            return {'error': 'VOIP non présent dans la table ou non activé.'}
        #
    else:
        return {'error': 'Type de VOIP inconnu'}
    #

    return results
#

# Créer un accès
# @param: str
# @return: json
def create_acces_essonne_numerique(acces_id):
    global results

    acces_id_match = re.search(r'ESNU\-ACCES\-\d+', acces_id)

    if acces_id_match:
        j_data = airtable('appeoq8CRibQP538a/tblv62Lm7DQXWdrYr?', 'filterByFormula=fld4p6PwUXMj3gV5d%3D%22' + acces_id + '%22&view=viwnvMUirvjffSLcf') # Airtable get table acces

        if 'records' in j_data and j_data['records']:
            for record in j_data['records']:
                if record['fields']:
                    ligne = record['fields']

                    configs_ports = gitlab(create_yaml_ports_olt('', '0.0.0.0', 0, 0, 0, ligne['type accès'], acces_id), 'OLT/ports_OLT.yaml')
                    configs_ports = configs_ports.replace(f'Configs service OLT pour collecte PPP\n\n', f'')
                    configs_ports = configs_ports.replace(f'0/0/0', f'<#PORT>/<#PON>/<#ONU>')
                    configs_ports = configs_ports.replace(f'\n\n', f'\n')
                    configs_ports_ipoe = []
                    for line in configs_ports.splitlines():
                        configs_ports_ipoe.append(line)
                        if "vlan-id 500" in line:
                            configs_ports_ipoe.append(line.replace("vlan-id 500", "vlan-id 101"))
                            configs_ports_ipoe.append(line.replace("vlan-id 500", "vlan-id 102"))
                        #
                    #
                    configs_ports = "\n".join(configs_ports_ipoe)
                    results['configs']['ports'] = configs_ports
                #
            #
        #
        else:
            return {'error': 'Accès non présent dans la table ou ne comporte pas le bon nom.'}
        #
    else:
        return {'error': 'Type d\'accès inconnu'}
    #

    return results
#

# Créer un service
# @param: str, ?str, ?str, ?str
# @return: json
def create_service_essonne_numerique(service_id, maj_rsp_only = 'no', mac_addr = None, subnet_vpnsur = None, mep_id = None):
    global results
    sql_connector28 = None
    cursor = None

    service_id_match = re.search(r'ESNU\-(INTE|VPNIP|LAN|WIFI|VOIP|LWM|VPNIOT|VPNSUR|VPNL2MPT|VPNL2P2P)\-\d{6}', service_id)

    if service_id_match:
        type_service = {
            'INTE': 'Internet',
            'VPNIOT': 'VPNIP IOT',
            'VPNSUR': 'VPNIP Sureté',
            'LWM': 'LAN et WIFI managé',
            'VPNL2MPT': 'VPN Ethernet Multi-Point',
            'VPNL2P2P': 'VPN Ethernet Point à Point'
        }.get(service_id_match.group(1), service_id_match.group(1))
        
        airtable_results = read_from_airtable(service_id)
        if isinstance(airtable_results, (str, bytes, bytearray)):
            json_content = None
            try:
                json_content = json.loads(airtable_results)
            except json.JSONDecodeError:
                return {'error': f'{str(airtable_results)}'}
            #

            service_name = ''
            if type_service == 'VPNIP IOT':
                service_name = 'LORA'
            elif type_service == 'VPNIP Sureté':
                service_name = 'SURETE'
            #

            olt_name = json_content['equipement']

            try:
                sql_connector28 = connection.MySQLConnection(user=RDB_USER, password=RDB_PASS, host='10.1.80.77', database='geco', port=3306, charset='utf8')
            except mysql.connector.Error:
                return {'error': 'Connexion à la vma-prdrdb-28 refusée.'}
            #

            sql_query = "SELECT * FROM referenciel_alcatel WHERE node LIKE %s"
            data = (f'{olt_name}%',)
            cursor = sql_connector28.cursor()
            cursor.execute(sql_query, data)
            ref_alcatel_result = cursor.fetchone()
            if ref_alcatel_result:
                olt_ip = ref_alcatel_result[1]
                port_cpe = json_content['port'].split('/')
                test_ssh_configs_ports = ssh(olt_name, [ f'show equipment ont interface 1/1/{int(port_cpe[2])}/{int(port_cpe[3])}/{int(port_cpe[4])}' ])[ f'show equipment ont interface 1/1/{int(port_cpe[2])}/{int(port_cpe[3])}/{int(port_cpe[4])}' ]
                #if service_name == 'LORA' or service_name == 'SURETE':
                #if re.search(r'Error : instance does not exist', test_ssh_configs_ports):
                configs_ports = gitlab(create_yaml_ports_olt(service_name, olt_ip, int(port_cpe[2]), int(port_cpe[3]), (int(port_cpe[4]) if len(port_cpe) > 4 else None), json_content['type_ont'], json_content['ref_site']), 'OLT/ports_OLT.yaml')
                configs_ports = configs_ports.replace(f'Configs service OLT pour collecte PPP', f'#### {olt_name}')
                configs_ports = configs_ports.replace(f'Configs service OLT pour collecte IPOE', f'#### {olt_name}')
                results['configs']['ports'] = configs_ports

                if not re.search(r'VPN Ethernet', type_service):
                    if type_service == 'VPNIP':
                        configs_vpnip = gitlab(create_yaml_retail(json_content['gfu'], json_content['vprn'], 'oui' if re.match('[5-6]{1}[0-9]{2}', json_content['vlan_bgp']) else 'non', json_content['vlan_bgp'], 'non', 0, 0), 'Retail PPP/retail_ppp.yaml')
                        configs_vpnip = configs_vpnip.replace(f'\nCONFIG SERVICE RETAIL PPP BNG', '')
                        configs_vpnip = configs_vpnip.replace(f'\nbng-', '#### bng-')
                        results['configs']['vpnip'] = configs_vpnip
                    #

                    if not re.search(r'\-\-\-', json_content['offre']):
                        configs_qos = gitlab(create_yaml_qos(type_service, int(json_content['offre'].replace('M', '').replace('G', ''))), 'Profils QOS/qos_bng.yaml')
                        configs_qos = configs_qos.replace(f'Configurations QoS BNG', f'#### bng-sac91-01, bng-sac91-02, bng-log77-01, bng-log77-02')
                        configs_qos = configs_qos.replace(f'Profil', f'# Profil')
                        configs_qos = configs_qos.replace(f'#### Spécifiques services IPOE LORA/Sureté ###', '#### Profil spécifiques services IPOE\n')
                        results['configs']['qos'] = configs_qos
                    #
                #
            else:
                return {'error': "OLT non détecté dans le Référentiel Alcatel, activation logique non possible."}
            #

            #if maj_rsp_only == 'yes':
            maj_rsp(json_content, type_service, mac_addr, subnet_vpnsur, mep_id) # Ajout des données dans RSP
            #
            results['netbox'] = 'Ajout KO dans Netbox' # Ajout dans Netbox
        else:
            return {'error': airtable_results}
        #
    else:
        return {'error': 'Type de service inconnu'}
    #

    return results
#

###########

# Private

# Ouvrir un fichier Airtable et le lire
# @param: str
# @return: json
def read_from_airtable(id_service):
    j_data = airtable('appeoq8CRibQP538a/tblVi8SozQWiduxmI?', 'filterByFormula=fldjz6DiiQgnojlNJ%3D%22' + id_service + '%22&view=viwhY134WxDN8TtW6') # Airtable get table services
    #j_data = airtable('appeoq8CRibQP538a/tblVi8SozQWiduxmI?', 'filterByFormula=fldjz6DiiQgnojlNJ%3D%22' + id_service + '%22&view=viwS8W850FyIWCuvL') # Airtable get table services

    if 'records' in j_data and j_data['records']:
        for record in j_data['records']:
            if record['fields']:
                ligne = record['fields']

                if ligne.get('équipement_d_accès', '') != '' and ligne.get('port_de_raccordement', '') != '':
                    if ligne.get('link_codes_offres', ['']) != '' and ligne.get('link_sites', ['']) != '' and ligne.get('link_CPE', ['']) != '' and ligne.get('ONT', ['']) != '' and ligne.get('Client', ['']) != '' and ligne.get('id_accès/ref_cmd_axione/ref_prestation_prise', ['']) != '' and ligne.get('link_GFU_associé', ['']) != '':
                        offre = airtable('appeoq8CRibQP538a/tblOuo5mROSHhNWaa/', ligne['link_codes_offres'][0])['fields']['offre_debit'] if ligne.get('link_codes_offres', '') != '' else None
                        site = airtable('appeoq8CRibQP538a/tblOuo5mROSHhNWaa/', ligne['link_sites'][0])['fields']['📋 id_site_client']
                        type_cpe = airtable('appeoq8CRibQP538a/tblggTBiKzULY7hnI/', airtable('appeoq8CRibQP538a/tbltND0m69FenJqzW/', ligne['link_CPE'][0])['fields']['Device'][0])['fields']['device']
                        type_ont = airtable('appeoq8CRibQP538a/tblggTBiKzULY7hnI/', airtable('appeoq8CRibQP538a/tblPGF4deyI8xLuAb/', ligne['ONT'][0])['fields']['Device'][0])['fields']['device']
                        ref_adherent = airtable('appeoq8CRibQP538a/tblV648itUw6KIT82/', ligne['Client'][0])['fields']['code_adherent']
                        ref_site = airtable('appeoq8CRibQP538a/tblv62Lm7DQXWdrYr/', ligne['id_accès/ref_cmd_axione/ref_prestation_prise'][0])['fields']['id_acces/ref_cmd_axione/ref_prestation_prise']
                        ref_cpe_acces = airtable('appeoq8CRibQP538a/tblVi8SozQWiduxmI/', ligne['link_CPE'][0])['fields']['ID_CPE']
                        id_gfu = airtable('appeoq8CRibQP538a/tblAhWlAMbRF7VNle/', ligne['link_GFU_associé'][0])['fields']['ID_GFU']
                        gfu = airtable('appeoq8CRibQP538a/tblAhWlAMbRF7VNle/', ligne['link_GFU_associé'][0])['fields']['nom_gfu']
                        categorie_site = airtable('appeoq8CRibQP538a/tblHcgNdO7CLTY2ZE/', ligne['link_sites'][0])['fields']['categorie_site']
                        nom_adherent = airtable('appeoq8CRibQP538a/tblV648itUw6KIT82/', ligne['Client'][0])['fields']['raison_sociale_adherent'][0]
                        
                        if offre is None:
                            if ligne['nature_du_service'] == 'VPNIOT':
                                offre = '10M'
                            elif ligne['nature_du_service'] == 'VPNSUR':
                                offre = '200M'
                            elif ligne['nature_du_service'] == 'LWM':
                                offre = '40M'
                            elif ligne['nature_du_service'] == 'VOIP':
                                offre = '50M'
                            else:
                                offre = '---'
                            #
                        #
                        offre = offre.replace(' Gbp/s', 'G').replace(' Mbp/s', 'M')
                        (vprn_bgp, vlan_bgp) = (0, 0)
                        if not re.search(r'VPNL2', ligne['nature_du_service']):
                            (vprn_bgp, vlan_bgp) = read_from_wiki(gfu)
                        #

                        if type_cpe == 'C8300-1N1S-4T2X':
                            type_cpe = 'C8300'
                        elif type_cpe == 'C8200-1N-4T':
                            type_cpe = 'C8200'

                        if ligne.get('id_service', '') != '' and ligne.get('nature_du_service', '') != '' and site != '' and ligne.get('nom_site', [''])[0] != '':
                            return json.dumps({
                                'id_service': ligne['id_service'],
                                'techno': ligne['nature_du_service'],
                                'offre': offre,
                                'site': site, 
                                'abonne': ligne['nom_site'][0],
                                'equipement': ligne['équipement_d_accès'],
                                'port': ligne['port_de_raccordement'],
                                'type_cpe': type_cpe,
                                'type_ont': type_ont,
                                'ref_adherent': ref_adherent,
                                'ref_site': ref_site,
                                'ref_cpe_acces': ref_cpe_acces,
                                'gfu': gfu,
                                'id_gfu': id_gfu,
                                'vprn': vprn_bgp,
                                'vlan_bgp': vlan_bgp,
                                'categorie_site': categorie_site,
                                'nom_adherent': nom_adherent
                            })
                        else:
                            return {'error': 'Des données (id_service, nature, site) sont manquantes dans Airtable.'}
                        #
                    else:
                        return {'error': 'Des données sont manquantes dans Airtable.'}
                    #
                else:
                    return {'error': 'La chaîne de liaison est inexistante dans Airtable.'}
                #
            #
        #
    else:
        return {'error': 'Service non présent dans la table ou déjà activé.'}
    #

    return None
#

# Connexion au Gitlab
# @param: str, str
# @return: str
def gitlab(template, filename):
    cfg_file_content = None

    REPO_URL = f"https://oauth2:{GIT_TOKEN}@gitlab.m2m.axione.fr/axione-dif-ingenierie/essonne-numerique.git"
    git_path = os.path.dirname(f"essonne-numerique/DIF Réseau/Configs/Services/{filename}")
    file = filename.split('/')[1].replace('.yaml', '')

    if not os.path.exists("essonne-numerique"):
        subprocess.run(["git", "clone", REPO_URL, 'essonne-numerique'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    else:
        shutil.rmtree("essonne-numerique")
        subprocess.run(["git", "clone", REPO_URL, 'essonne-numerique'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    subprocess.run(["git", "checkout", "main"], cwd='essonne-numerique', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    yaml_file_path = os.path.join(git_path, f"{file}.yaml")
    os.chmod(yaml_file_path, 0o755)
    cfg_file_path = os.path.join(git_path, f"{file}_cfg.txt")
    os.chmod(cfg_file_path, 0o755)

    with open(yaml_file_path, 'w', encoding='utf-8') as f:
        f.write(template)
    #

    sh_file = "generate_svc_cfg.sh"
    j2_file = "template_cfg_ports_olt_essonne.j2"
    if re.search(r'Retail\sPPP', git_path):
        sh_file = "generate_cfg_svc_retail_ppp.py"
        j2_file = "template_cfg_svc_retail.j2"
    elif re.search(r'Profils\sQOS', git_path):
        sh_file = "generate_cfg_qos.sh"
    #
    script_path = os.path.join(git_path, f"{sh_file}")
    os.chmod(script_path, 0o755)

    if os.path.exists(script_path):
        if not re.search(r'\.py', sh_file):
            subprocess.run(["sed", "-i", "s/\r$//", f"{sh_file}"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            subprocess.run(["bash", f"{sh_file}"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        else:
            subprocess.run(["python3", f"{sh_file}", "-y", f"{file}.yaml", "-t", f"{j2_file}", "-o", f"{file}_cfg.txt"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        #

        status_result = subprocess.run(["git", "status", "--porcelain"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
        status_lines = status_result.stdout.splitlines()
        status_lines_filtered = [
            line for line in status_lines 
            if not line.endswith(".sh") and (line.strip().startswith("A ") or line.strip().startswith("M "))
        ]

        if status_lines_filtered:
            subprocess.run(["git", "add", f"{file}.yaml", f"{file}_cfg.txt"], cwd=git_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            commit_result = subprocess.run(["git", "commit", "-m", f"Auto-update script AME"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if commit_result.returncode == 0:
                subprocess.run(["git", "push"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            #
            with open(cfg_file_path, 'r', encoding='utf-8') as f:
                cfg_file_content = f.read()
            #
            cfg_file_content = re.sub(r'(?m)^\s+', '', cfg_file_content, flags=re.MULTILINE)
            cfg_file_content = re.sub(r'^[#-]+$', '', cfg_file_content, flags=re.MULTILINE)
            cfg_file_content = cfg_file_content.replace(f'configure service ', f'\nconfigure service ')
            cfg_file_content = cfg_file_content.replace(f'admin save', f'\nadmin save\n')
            cfg_file_content = cfg_file_content.replace(f'################## A ne créer qu\'UNE SEULE FOIS par BNG - si non existant (toujours vérifier pour option acces internet et voip) ##################', '')
            cfg_file_content = cfg_file_content.replace(f'############################## A créer pour CHAQUE NOUVEAU GFU sur les BNG ##############################', '')
        #
    #
    shutil.rmtree("essonne-numerique")

    return cfg_file_content
#

# Appeler l'API Airtable
# @param: array
# @return: json
def airtable(endpoint, parameters):
    airtableProxies = {
        "http": f"{AX_PROXY}",
        "https": f"{AX_PROXY}",
    }

    airtableTokenHeaders = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Bearer {AIR_TOKEN_ENU}',
    }

    try:
        response = requests.get(f"{AIR_URL}" + endpoint + f"{parameters}", headers=airtableTokenHeaders, proxies=airtableProxies, verify=False)
        if re.search(r"200", str(response), re.IGNORECASE):
            return json.loads(response.text)
        else:
            return {'error': str(response)}
        #
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}
    #
#

# Appeler l'API Wiki
# @param: str
# @return: int
def read_from_wiki(nom_client):
    wikiProxies = {
        "http": f"{AX_PROXY}",
        "https": f"{AX_PROXY}",
    }

    try:
        response = requests.get('https://wiki.int.axione.fr/api.php?action=parse&page=AME:Referentiel_VPRN&format=json&prop=text', proxies=wikiProxies, verify=False)
        if re.search(r"200", str(response), re.IGNORECASE):
            data = json.loads(response.text)["parse"]["text"]["*"]
            pattern = re.compile(r"<td>(\d+)</td>\s*<td>\d*</td>\s*<td>(.*?)</td>\s*<td>(\d{0,4})</td>")
            vprn_data = {match.group(1): (match.group(2).strip(), match.group(3)) for match in pattern.finditer(data)}
            for vprn_id, (description, vlan_id) in vprn_data.items():
                if nom_client.lower() in description.lower():
                    return [vprn_id, vlan_id]
                #
            #
        else:
            return 0
        #
    except requests.exceptions.RequestException as e:
        return 0
    #
#

# Génération d'un password
# @param: void
# @return: string
def generate_password_ppp():
    digits = string.digits
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    special_characters = '$@%-!'
    all_characters = digits + lowercase + uppercase + special_characters
    password = [random.choice(all_characters) for _ in range(14)]
    password.append(random.choice(special_characters))
    random.shuffle(password)
    return ''.join(password)
#

# Génération d'un host CPE
# @param: str, str
# @return: str
def generate_cpe_hostname(equipement, port):
    cpe_regex_equipement = re.search(r'\w+\-([\w\d]{5})\-(\d{2})', equipement)
    cpe = None
    if re.match('edg-', equipement):
        cpe_regex_port = re.search(r'(\d+)\/(\d+)\/(\d+)', port)
        cpe = 'cpe-' + cpe_regex_equipement.group(1) + '-' + cpe_regex_equipement.group(2) + (cpe_regex_port.group(1) + cpe_regex_port.group(2) + (cpe_regex_port.group(3) if int(cpe_regex_port.group(3)) >= 10 else '0' + cpe_regex_port.group(3)) + '1')
    else:
        cpe_regex_port = re.search(r'[\d+\/]{0,2}\d+\/(\d+)\/(\d+)\/(\d+)', port)
        cpe = 'cpe-' + cpe_regex_equipement.group(1) + '-' + cpe_regex_equipement.group(2)
        if re.search(r'\d+\/\d+\/\d+\/\d+\/\d+', port):
            cpe += cpe_regex_port.group(1) + (cpe_regex_port.group(2) if int(cpe_regex_port.group(2)) >= 10 else '0' + cpe_regex_port.group(2)) + (cpe_regex_port.group(3) if int(cpe_regex_port.group(3)) >= 10 else '0' + cpe_regex_port.group(3))
        else:
            cpe += '0' + cpe_regex_port.group(2) + (cpe_regex_port.group(3) if int(cpe_regex_port.group(3)) >= 10 else '0' + cpe_regex_port.group(3)) + '1'
        #
    #

    return cpe
#

# Génération des IP
# @param: str, str
# @return: str
def set_ip(host, descr):
    descr = descr.replace('\'', ' ')

    soapHeaders = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'majIpam#request'
    }
    
    soapBody = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:maj="majIpam">
        <soapenv:Header/>
        <soapenv:Body>
            <maj:request>
                <hostname>{host}.enu</hostname>
                <description>{descr}</description>
            </maj:request>
        </soapenv:Body>
    </soapenv:Envelope>
    """
    
    response = requests.post('https://ws.m2m.axione.fr/ws-maj-ipam/', data=soapBody, headers=soapHeaders, verify=False)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        json_response = json.loads(root.find('.//{majIpam}retour').text)
        return json_response.get('retour')
    else:
        return None
#

# Ajouter un ID de service dans RSP
# @param: array
# @return: bool
def maj_rsp(json, type_service, mac_addr = None, subnet_vpnsur = None, mep_id = None):
    global results
    referer = 'https://ws-ords.m2m.axione.fr'

    # Vérification nom accès
    if re.match(r'ESNU-ACCES-\d+', json['ref_site']):

        # Vérification présence accès dans RSP
        response = requests.get(f'https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/ref_sp?who={json["ref_site"]}', headers={'Referer': referer}, verify=False)
        response.raise_for_status()
        data = response.json()
        if data['items']:

            # Création du DNS CPE
            cpe = generate_cpe_hostname(json['equipement'], json['port'])

            # Maj des champs accès
            rspData = {
                'p_id_service': f"{json['ref_site']}",
                'p_abonne': f"{json['abonne']}",
                "p_adherent": f"{json['ref_adherent']}",
                "p_gfu": f"{json['id_gfu']}/{json['gfu']}",
                'p_categorie_site': f"{json['categorie_site']}"
            }
            try:
                response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                results['rsp']['acces']['status'] = f'Maj du service {json["ref_site"]} OK dans RSP'
            except requests.exceptions.RequestException as e:
                results['rsp']['acces']['status'] = f'Maj du service {json["ref_site"]} NOK dans RSP'
            #

            if json['type_cpe'] != 'U92':

                results['acces']['ip'] = set_ip(f'{cpe}', json['abonne'] + ' - ' + json['ref_cpe_acces'])

                # Ajout du password PPP sur l'accès
                if data['items'][0].get('id_technique') is not None and data['items'][0].get('commentaire_id_tech') is not None:
                    login = data['items'][0].get('id_technique')
                    password = data['items'][0].get('commentaire_id_tech')
                    results['acces']['login'] = login
                    results['acces']['password'] = password
                    results['acces']['radius'] = create_radius_request(json['gfu'], json["ref_cpe_acces"], password, results['acces']['ip'], int(json['offre'].replace('M', '').replace('G', '')), '901', json['ref_cpe_acces'], None, None)
                else:
                    password_ppp = generate_password_ppp()
                    rspData = {
                        'p_id_service': f"{json['ref_site']}",
                        'p_idtechnique': f"{json['ref_cpe_acces']}@essonnenumerique.com",
                        'p_type_idtechnique': 'LOGIN',
                        'p_commentaire_idtechnique': f"{password_ppp}",
                    }
                    try:
                        response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                        results['acces']['login'] = f"{json['ref_cpe_acces']}@essonnenumerique.com"
                        results['acces']['password'] = f"{password_ppp}"
                    except requests.exceptions.RequestException as e:
                        results['acces']['password'] = f'{e}'
                    #

                    results['acces']['radius'] = create_radius_request(json['gfu'], json["ref_cpe_acces"], password_ppp, results['acces']['ip'], int(json['offre'].replace('M', '').replace('G', '')), '901', json['ref_cpe_acces'], None, None)
                #
            #

            vlan_livraison_l2 = None
            if data['items'][0].get('vlan'):
                vlan_livraison_l2 = data['items'][0].get('vlan')
            #
        
            # Ajout dans RSP d'un nouveau service
            rspData = {
                "p_id_service": json["id_service"],
                "p_dsp": "ESSONNE NUMERIQUE", 
                "p_fai": "SYNDICAT MIXTE OUVERT ESSONNE NUMERIQUE",
                "p_ABONNE": f"{json['abonne']}",
                "p_equipementier": "ALCATEL", 
                "p_operateur_tiers": "",
                "p_technologie": type_service,
                "p_statut": "En service",
                "p_profil": f"{json['offre']}",
                "p_ID_SERVICE_EXTERNE": f"{json['site']}",
                "p_ADHERENT": f"{json['ref_adherent']}",
                "p_SERVICES_LIES": f"{json['ref_site']}",
                "p_GFU": f"{json['id_gfu']}/{json['gfu']}",
                "p_CATEGORIE_SITE": f"{json['categorie_site']}"
            }
            try:
                response = requests.post('https://refsp.m2m.axione.fr/ordscomxdsl/pwksrefpro/rsp_add_id_service', data=rspData, verify=False)
                results['rsp']['service']['status'] = f'Ajout OK service {json["id_service"]} dans RSP'
            except requests.exceptions.RequestException as e:
                results['rsp']['service']['status'] = f'Ajout KO service {json["id_service"]} dans RSP'
            #

            # Ajout des EDG/OLT
            if re.match('olt-', json['equipement']):
                acces_logique = 'Accès - équipement Axione NOKIA 7360 FX-4'
            elif re.match('edg-', json['equipement']):
                acces_logique = 'Accès - équipement Axione NOKIA 7250 IXR'
            #
            acces_physique = '10GBase-LR' if json['type_cpe'] == 'C8300' else '1000Base-LX'
            debit = json['offre']
            rspData = {
                "p_id_service": f"{json['id_service']}",
                "p_equipement_port": f"{json['equipement']}",
                "p_port": f"{json['port']}" if re.search(r'\d+\/\d+\/\d+\/\d+\/\d+', json['port']) else f"ethernet-line:{json['port']}",
                "p_acces_logique": f"{acces_logique}",
                "p_acces_physique": f"{acces_physique}",
                "p_debit_cir": f"{debit}",
                "p_debit_burst": f"{debit}"
            }
            try:
                response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                results['rsp']['service']['pe'] = f'Ajout OK {json["equipement"]} {json["port"]} dans RSP'
            except requests.exceptions.RequestException as e:
                results['rsp']['service']['pe'] = f'Ajout KO {json["equipement"]} {json["port"]} dans RSP'
            #

            rspData = {
                "p_id_service": f"{json['ref_site']}",
                "p_equipement_port": f"{json['equipement']}",
                "p_port": f"{json['port']}" if re.search(r'\d+\/\d+\/\d+\/\d+\/\d+', json['port']) else f"ethernet-line:{json['port']}",
                "p_acces_logique": f"{acces_logique}",
                "p_acces_physique": f"{acces_physique}",
                "p_debit_cir": "---",
                "p_debit_burst": "---"
            }
            try:
                response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                results['rsp']['acces']['pe'] = f'Ajout OK {json["equipement"]} {json["port"]} dans RSP {json["ref_site"]}'
            except requests.exceptions.RequestException as e:
                results['rsp']['acces']['pe'] = f'Ajout KO {json["equipement"]} {json["port"]} dans RSP {json["ref_site"]}'
            #

            # Ajout des CPE
            if json['type_cpe'] and json['type_cpe'] != 'U92':
                port_cpe = ''
                if json['type_cpe'] == 'C8300':
                    port_cpe = '0/0/5'
                elif json['type_cpe'] == 'C8200':
                    port_cpe = '0/0/3'
                else:
                    port_cpe = '0/1/0'
                    if json['techno'] == 'INTE':
                        port_cpe = '0/1/1'
                    elif json['type_cpe'] == 'C1111-4P' and json['techno'] == 'VPNIOT':
                        port_cpe = '0/1/2'
                    elif json['type_cpe'] == 'C1111-4P' and json['techno'] == 'VPNSUR':
                        port_cpe = '0/1/3'
                    elif json['type_cpe'] == 'C1111-8P' and json['techno'] == 'VPNIOT':
                        port_cpe = '0/1/6'
                    elif json['type_cpe'] == 'C1111-8P' and json['techno'] == 'VPNSUR':
                        port_cpe = '0/1/7'
                #
                acces_logique = 'Accès - équipement client CISCO ' + json['type_cpe']
                rspData = {
                    "p_id_service": f"{json['id_service']}",
                    "p_equipement_port": f"{cpe}",
                    "p_port": f"{port_cpe}",
                    "p_acces_logique": f"{acces_logique}",
                    "p_acces_physique": f"{acces_physique}",
                    "p_debit_cir": f"{debit}",
                    "p_debit_burst": f"{debit}"
                }
                try:
                    response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                    results['rsp']['service']['cpe'] = f'Ajout OK {cpe} {port_cpe} dans RSP'
                except requests.exceptions.RequestException as e:
                    results['rsp']['service']['cpe'] = f'Ajout KO {cpe} {port_cpe} dans RSP'
                #

                rspData = {
                    "p_id_service": f"{json['ref_site']}",
                    "p_equipement_port": f"{cpe}",
                    "p_port": f"{port_cpe}",
                    "p_acces_logique": f"{acces_logique}",
                    "p_acces_physique": f"{acces_physique}",
                    "p_debit_cir": "---",
                    "p_debit_burst": "---"
                }
                try:
                    response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                    results['rsp']['acces']['cpe'] = f'Ajout OK {cpe} {port_cpe} dans RSP {json["ref_site"]}'
                except requests.exceptions.RequestException as e:
                    results['rsp']['acces']['cpe'] = f'Ajout KO {cpe} {port_cpe} dans RSP {json["ref_site"]}'
                #
            #

            # Ajout des ID techniques
            if json['techno'] == 'INTE' or json['techno'] == 'VPNIP' or json['techno'] == 'LWM':
                id_vpls = '1703' if json['techno'] == 'INTE' and (json['vlan_bgp'] == '' or json['vlan_bgp'] == 0) else json['vprn']
                id_vpls = '902' if json['techno'] == 'LWM' else id_vpls
                rspData = {
                    'p_id_service': f"{json['id_service']}",
                    'p_idtechnique': id_vpls,
                    'p_type_idtechnique': 'VPRN',
                    'p_commentaire_idtechnique': '',
                }
                try:
                    response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                    results['rsp']['service']['vprn'] = f'Ajout OK du VPRN {id_vpls} dans RSP'
                except requests.exceptions.RequestException as e:
                    results['rsp']['service']['vprn'] = f'Ajout KO du VPRN {id_vpls} dans RSP'
                #

                if (json['techno'] == 'INTE' and (json['vlan_bgp'] == '' or json['vlan_bgp'] == 0)) or json['techno'] != 'INTE':

                    # Vérification présence password
                    response_service = requests.get(f'https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/ref_sp?who={json["id_service"]}', headers={'Referer': referer}, verify=False)
                    response_service.raise_for_status()
                    data_service = response_service.json()

                    if json['type_cpe'] == 'U92':
                        results['service']['ip'] = set_ip('Kontron', json['id_service'])
                        results['acces']['ip'] = results['service']['ip']
                    else:
                        results['service']['ip'] = set_ip(json['equipement'], json['id_service'])
                    #
                    service_login = None
                    service_password = None

                    # Ajout du password PPP sur le service
                    for item in data_service['items']:
                        if re.search(r'essonnenumerique\.com', item.get('id_technique')) and item.get('commentaire_id_tech') is not None:
                            results['service']['login'] = item.get('id_technique')
                            service_login = results['service']['login']
                            results['service']['password'] = item.get('commentaire_id_tech')
                            service_password = results['service']['password']
                            if json['gfu'] != 'CCVE':
                                results['service']['radius'] = create_radius_request(json['gfu'], json["id_service"], results['service']['password'], results['service']['ip'], int(json['offre'].replace('M', '').replace('G', '')), id_vpls, json['ref_cpe_acces'], None, None)
                            #
                            break
                    else:
                        password_ppp = generate_password_ppp()
                        rspData = {
                            'p_id_service': f"{json['id_service']}",
                            'p_idtechnique': f"{json['id_service']}@essonnenumerique.com",
                            'p_type_idtechnique': 'LOGIN',
                            'p_commentaire_idtechnique': f"{password_ppp}",
                        }
                        try:
                            response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                            results['service']['login'] = f"{json['id_service']}@essonnenumerique.com"
                            service_login = results['service']['login']
                            results['service']['password'] = f"{password_ppp}"
                            service_password = results['service']['password']
                        except requests.exceptions.RequestException as e:
                            results['service']['login'] = None
                            results['service']['password'] = None
                        #

                        if json['gfu'] != 'CCVE':
                            results['service']['radius'] = create_radius_request(json['gfu'], json["id_service"], password_ppp, results['service']['ip'], int(json['offre'].replace('M', '').replace('G', '')), id_vpls, json['ref_cpe_acces'], None, None)
                        #
                    #

                    # Si Kontron
                    if json['type_cpe'] == 'U92':
                        rspData = {
                            'p_id_service': f"{json['ref_site']}",
                            'p_idtechnique': service_login,
                            'p_type_idtechnique': 'LOGIN',
                            'p_commentaire_idtechnique': service_password,
                        }
                        try:
                            response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                            results['acces']['login'] = service_login
                            results['acces']['password'] = service_password
                        except requests.exceptions.RequestException as e:
                            results['acces']['password'] = f'{e}'
                        #
                    #
                else:
                    results['service']['radius'] = f'Pas de configuration radius pour {json["id_service"]} en activation vDOM'
                #
            elif json['techno'] == 'VPNIOT' or json['techno'] == 'VPNSUR':
                rspData = {
                    'p_id_service': f"{json['id_service']}",
                    'p_idtechnique': mac_addr,
                    'p_type_idtechnique': 'SUBSCRIBER',
                    'p_commentaire_idtechnique': '',
                }
                try:
                    response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                    results['rsp']['service']['ipoe subscriber'] = f'Ajout OK du SUBSCRIBER {mac_addr} dans RSP'
                except requests.exceptions.RequestException as e:
                    results['rsp']['service']['ipoe subscriber'] = f'Ajout KO du SUBSCRIBER {mac_addr} dans RSP'
                #

                if json['techno'] == 'VPNSUR':
                    rspData = {
                        'p_id_service': f"{json['id_service']}",
                        'p_idtechnique': subnet_vpnsur,
                        'p_type_idtechnique': 'SUBNET',
                        'p_commentaire_idtechnique': '',
                    }
                    try:
                        response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                        results['rsp']['service']['ipoe subnet'] = f'Ajout OK du SUBNET {subnet_vpnsur} dans RSP'
                    except requests.exceptions.RequestException as e:
                        results['rsp']['service']['ipoe subnet'] = f'Ajout KO du SUBNET {subnet_vpnsur} dans RSP'
                    #
                #

                id_vpls = '1705' if json['techno'] == 'VPNIOT' else '1704'
                rspData = {
                    'p_id_service': f"{json['id_service']}",
                    'p_idtechnique': id_vpls,
                    'p_type_idtechnique': 'VPRN',
                    'p_commentaire_idtechnique': 'Hub',
                }
                try:
                    response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                    results['rsp']['service']['ipoe vprn hub'] = f'Ajout OK du VPRN {id_vpls} dans RSP'
                except requests.exceptions.RequestException as e:
                    results['rsp']['service']['ipoe vprn hub'] = f'Ajout KO du VPRN {id_vpls} dans RSP'
                #

                id_vpls = '1715' if json['techno'] == 'VPNIOT' else '1714'
                rspData = {
                    'p_id_service': f"{json['id_service']}",
                    'p_idtechnique': id_vpls,
                    'p_type_idtechnique': 'VPRN',
                    'p_commentaire_idtechnique': 'Spoke',
                }
                try:
                    response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                    results['rsp']['service']['ipoe vprn spoke'] = f'Ajout OK du VPRN {id_vpls} dans RSP'
                except requests.exceptions.RequestException as e:
                    results['rsp']['service']['ipoe vprn spoke'] = f'Ajout KO du VPRN {id_vpls} dans RSP'
                #

                if json['techno'] == 'VPNSUR':
                    rspData = {
                        'p_id_service': f"{json['id_service']}",
                        'p_idtechnique': subnet_vpnsur,
                        'p_type_idtechnique': 'SUBNET',
                        'p_commentaire_idtechnique': '',
                    }
                    try:
                        response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                        results['rsp']['service']['ipoe subnet'] = f'Ajout OK du VPRN {subnet_vpnsur} dans RSP'
                    except requests.exceptions.RequestException as e:
                        results['rsp']['service']['ipoe subnet'] = f'Ajout KO du VPRN {subnet_vpnsur} dans RSP'
                    #
                #

                results['service']['radius'] = create_radius_request(json['gfu'], json['id_service'], '', set_ip(json['equipement'], mac_addr + ' - ' + json['id_service']), int(json['offre'].replace('M', '').replace('G', '')), id_vpls, json['ref_cpe_acces'], mac_addr, subnet_vpnsur)
            #elif json['techno'] == 'LWM':
                #results['rsp']['service']['lwm subnet'] = set_ip(json['equipement'], json['id_service'])
            elif json['techno'] == 'VOIP':
                results['rsp']['service']['voip'] = set_ip(json['equipement'], json['id_service'])
            elif json['techno'] == 'VPNL2MPT':
                if vlan_livraison_l2 is not None:
                    rspData = {
                        'p_id_service': f"{json['id_service']}",
                        'p_idtechnique': vlan_livraison_l2,
                        'p_type_idtechnique': 'VPLS',
                        'p_commentaire_idtechnique': '',
                    }
                    try:
                        response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                        results['rsp']['service']['vpnl2'] = f'Ajout OK du VLAN {vlan_livraison_l2} dans RSP'
                    except requests.exceptions.RequestException as e:
                        results['rsp']['service']['vpnl2'] = f'Ajout OK du VLAN dans RSP'
                    #

                    results['configs']['vpnl2'] = create_config_vpnl2(json['equipement'], json['port'], cpe, port_cpe, json['id_service'], json['id_gfu'], mep_id, vlan_livraison_l2)
                else:
                    results['rsp']['service']['vpnl2'] = f'VLAN KO dans RSP {json["ref_site"]}'
                #
            else:
                results['rsp']['service']['status'] = f'Référence KO dans RSP {json["id_service"]}'
            #
        else:
            results['rsp']['acces']['status'] = f'Référence KO dans RSP {json["ref_site"]}'
        #

        if json['techno'] != 'VPNL2MPT':
            rspData = {
                'p_id_service': f"{json['id_service']}",
                'p_idtechnique': '700',
                'p_type_idtechnique': 'VPRN',
                'p_commentaire_idtechnique': '',
            }
            try:
                response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
                results['rsp']['service']['wholesale'] = f'Ajout OK du VPRN 700 dans RSP'
            except requests.exceptions.RequestException as e:
                results['rsp']['service']['wholesale'] = f'Ajout KO du VPRN 700 dans RSP'
            #
        #
    else:
        results['rsp']['acces']['status'] = f'Référence d\'accès KO dans RSP'
    #
#

###########

# Protected

# Créer la conf vpnl2
# @param: str, str, str, str, str, str
# @return: str
def create_config_vpnl2(olt_name, olt_port, cpe_name, cpe_port, id_service, gfu, mep_id, vlan_livraison):
    olt_port_split = olt_port.split('/')
    vlan_transport_slot = int(olt_port_split[2]) - 3
    vlan_transport_port = olt_port_split[3] if int(olt_port_split[3]) >= 10 else '0' + olt_port_split[3]
    vlan_transport = str(vlan_transport_slot) + vlan_transport_port + '1'

    return f"""#### {cpe_name}

configure terminal

object-group network RFC1918
10.0.0.0 255.0.0.0
172.16.0.0 255.240.0.0
192.168.0.0 255.255.0.0

object-group network RFC6598
100.64.0.0 255.192.0.0

ip access-list extended C_Data
10 permit ip any object-group RFC1918
20 permit ip any object-group RFC6598
ip access-list extended C_Internet
10 permit ip any any
ip access-list extended C_Voix
deny ip any any 
class-map match-any Class_VOIX
match protocol sip
match access-group name C_Voix
match dscp af31
match dscp ef
class-map match-any Class_Data
match access-group name C_Data
class-map match-any Class_Internet
match access-group name C_Internet
class-map match-any Lan_Wifi
match any
class-map match-any Lora
match any
class-map match-any EVC
match any
class-map match-any COS7
match ip dscp cs6
match dscp cs6
match dscp cs7
match protocol pppoe
match dscp 57
class-map match-any COS5
match qos-group 5
class-map match-any COS4
match qos-group 4
class-map match-any COS3
match qos-group 3
class-map match-any COS2
match qos-group 2
class-map match-any COS0
match qos-group 0
policy-map LAN_VPN_IP_QoS
class Class_VOIX
set qos-group 5
set dscp ef
class Class_Data
set qos-group 2
set dscp cs2
class Class_Internet
set dscp default
set qos-group 0
policy-map LAN_Lora_QoS
class Lora
set qos-group 4
policy-map WAN_QoS
class COS7
set cos 7
set ip precedence 7
policy-map Shaper_out_WAN
class class-default
shape average 10000000
service-policy WAN_QoS
policy-map LAN_EVC_QoS
class EVC
set qos-group 4
policy-map LAN_Wifi_QoS
class Lan_Wifi
set qos-group 3
policy-map LAN_Internet_QoS
class Class_VOIX
set qos-group 5
set dscp ef
class Class_Internet
set dscp default
set qos-group 0
bba-group pppoe global
control-packets vlan cos 7
service-group 1
service-policy output Shaper_out_WAN
class-map match-any Class_L2_VOIX
match cos 7
match cos 6
match cos 5
class-map match-any Class_L2_Video
match cos 4
class-map match-any Class_L2_DATA
match cos 2
policy-map WAN_VPN_ETH_QoS
class Class_L2_VOIX
priority level 1
police cir 50000000 bc 31250
conform-action transmit
exceed-action drop
class Class_L2_Video
priority level 2
police cir 200000000
conform-action transmit
exceed-action drop
class Class_L2_DATA
bandwidth remaining percent 75
class class-default
bandwidth remaining percent 25
policy-map Shaper_L2_WAN_UP
class class-default
shape average 980000000
service-policy WAN_VPN_ETH_QoS
class-map match-all INGRESS_1G
match any
policy-map POLICE_L2_WAN_DOWN
class INGRESS_1G
police 980000000 conform-action transmit exceed-action drop

bridge-domain {vlan_transport}
no mac learning

ethernet cfm ieee
ethernet cfm global
ethernet cfm traceroute cache
ethernet cfm traceroute cache size 200
ethernet cfm traceroute cache hold-time 60
ethernet cfm alarm notification all
ethernet cfm domain {gfu} level 2
service SRVC evc EVC{vlan_transport} vlan {vlan_transport} direction down
continuity-check
continuity-check interval 10s

ethernet evc EVC{vlan_transport}
oam protocol cfm domain {gfu}

ethernet service multi-line

interface GigabitEthernet{cpe_port}
description "{id_service}"
no ip address
negotiation auto
service instance {vlan_transport} ethernet
encapsulation default
rewrite ingress tag push dot1q {vlan_transport} symmetric
l2protocol forward stp vtp dtp dot1x
bridge-domain {vlan_transport}

interface GigabitEthernet0/0/2
mtu 1508
no ip address
load-interval 30
no negotiation auto
service instance {vlan_transport} ethernet EVC{vlan_transport}
encapsulation dot1q {vlan_transport}
service-policy input POLICE_L2_WAN_DOWN
service-policy output Shaper_L2_WAN_UP
l2protocol forward stp vtp dtp dot1x
bridge-domain {vlan_transport}
cfm mep domain {gfu} mpid {mep_id}
alarm notification all

interface GigabitEthernet0/0/2.500
group 1

snmp-server enable traps ethernet cfm cc mep-up mep-down cross-connect loop config
snmp-server enable traps ethernet cfm alarm

end

write memory
    
#### {olt_name}

configure vlan id {vlan_transport} mode cross-connect

configure bridge port {olt_port} max-unicast-mac 10
configure bridge port {olt_port} vlan-id {vlan_transport} tag single-tagged mac-learn-ctrl 2

configure service vpls {vlan_livraison} customer 1 create
description "VPN-ETHERNET-{gfu}-{vlan_livraison}"
service-mtu 9100
user-user-com
disable-learning
stp
shutdown
exit
ingress
qos 2
exit
sap lt:1/1/{olt_port_split[2]}:{vlan_transport} create
no shutdown
exit
sap lag-1:{vlan_livraison} create
no shutdown
exit
exit all

admin save

"""
#

# Créer le template gitlab ports
# @param: str
# @return: yaml
def create_yaml_ports_olt(service_name, ip_mgmt_olt, slot, port, onu, debit, ref_acces):
    template_carte_gpon = ''
    template_carte_p2p = ''

    type_collecte = 'PPP' if service_name == '' else 'IPOE'
    service_ipoe = 'Lora' if service_name == 'Lora' else 'Surete'
    type_ont = '4ports'
    if re.search(r'XGSPON|XS\-010', debit):
        type_ont = 'sfp_xgspon'
    elif re.search(r'GPON|G\-010', debit):
        type_ont = 'sfp_gpon'
    #
    
    if (slot >= 1 and slot <= 3) or slot == 0:
        template_carte_gpon = f"""ont:
- slot_id: {slot} # numéro du slot de la carte LT
  pon_id: {port} # n° du port PON de la carte LT 
  ont_id: {onu} # position logique de l'ONT dans l'arbre PON
  type_ont: {type_ont} # peut prendre les valeurs 'sfp_xgspon', 'sfp_gpon','4ports'
  serial_num: "ALCL:XXXXXXXX"
  desc1 : "{ref_acces}"
"""
    #

    if slot == 4:
        template_carte_p2p = f"""cartes:
- slot_id: {slot} # numéro du slot de la carte LT
  type_carte: 'felt-b' # peut prendre les valeurs 'fwlt-c', 'felt-b'
  port_id: [{port}] # carte FELT-B : liste des ports ethernet utilisés
  type_lien: ['1000basebx10d'] # carte FELT-B : débit des ports ethernet utilisés peut prendre les valeurs '10gbaselr', '1000basebx10d'
"""
    #

    return f"""# Ports OLT (auto-généré)

type_collecte : {type_collecte} # peut prendre les valeurs 'IPOE' pour du Lora & Sureté Elec, 'PPP' pour du VPN IP
service_ipoe : {service_ipoe} # peut prendre les valeurs 'Lora' , 'Surete'
type_racco_switch : 'CPE' # peut prendre les valeurs 'ONT4p/1p' pour un switch Lot2 directement raccordé sur ONT , 'CPE' pour un switch Lot2 raccordé sur CPE

ip_mgmt_olt : {ip_mgmt_olt}

{template_carte_gpon}

{template_carte_p2p}
"""
#

# Créer le template gitlab qos
# @param: str
# @return: yaml
def create_yaml_qos(type_service, debit):
    service = 'Transit Internet' if type_service == 'Internet' else 'VPN-IP'
    debit_chapeau = 10 if debit > 500 and debit < 10 else 1

    return f"""# Profil QOS (auto-généré)

abreviation_projet: EN    # valeur fixe - ne pas changer pour Essonne Numérique / identique à celle du YAML Radius
nom_service: {service}       # peut prendre les valeurs 'Transit Internet' ou 'VPN-IP'

# BP alloué au network control
debit_pir_nc: 10          # débit exprimé en Mbps / valeur fixe - ne pas changer pour Essonne Numérique
debit_cir_nc: 10          # débit exprimé en Mbps / valeur fixe - ne pas changer pour Essonne Numérique

# admin CPE et LAN&Wifi
id_ingress_admin: 40      # valeur fixe - ne pas changer pour Essonne Numérique
id_egress_admin: 40       # valeur fixe - ne pas changer pour Essonne Numérique

debit_pir_admin: 40       # débit exprimé en Mbps / valeur fixe - ne pas changer pour Essonne Numérique
debit_cir_admin: 40       # débit exprimé en Mbps / valeur fixe - ne pas changer pour Essonne Numérique

# Service
id_ingress_service: {debit}
id_egress_service : {debit}
debit_pir_assu: {debit}        # débit exprimé en Mbps
debit_cir_assu: {debit}        # débit exprimé en Mbps
debit_pir_voix: 50         # débit exprimé en Mbps / valeur fixe - ne pas changer pour Essonne Numérique
debit_cir_voix: 50         # débit exprimé en Mbps / valeur fixe - ne pas changer pour Essonne Numérique

debit_chapeau: {debit_chapeau}           # débit exprimé en Gbps / peut prendre les valeurs '1' ou '10' / débit > 500M alors = 10
"""
#

# Créer le template gitlab retail
# @param: str
# @return: yaml
def create_yaml_retail_ipoe(service_name):
    id_vprn_hub = 995 if service_name == 'LORA' else 996
    id_vprn_spoke = 995 if service_name == 'LORA' else 996
    qos_hub = 995 if service_name == 'LORA' else 996
    name_vprn_spoke = 'VPRN-LORA-SPOKE' if service_name == 'LORA' else 'VPRN-SURETE-SPOKE'
    name_vprn_hub = 'VPRN-LORA-HUB' if service_name == 'LORA' else 'VPRN-SURETE-HUB'

    return f"""# Retail IPOE (auto-généré)

liste_bng:
- bng: bng-sac91-01
  ip_system_bng: 10.50.0.1
- bng: bng-sac91-02
  ip_system_bng: 10.50.0.2
- bng: bng-log77-01
  ip_system_bng: 10.50.0.3
- bng: bng-log77-02
  ip_system_bng: 10.50.0.4

id_PP : 91                                        # ne pas changer pour Essonne Numérique
as_number: 65004                                  # AS du service : 65005 pour Lora / 65004 pour Sureté Electronique

id_topologie :      
  fullmesh: '000'                                 # ne pas changer pour Essonne Numérique
  hub: '010'                                      # ne pas changer pour Essonne Numérique
  spoke: '020'                                    # ne pas changer pour Essonne Numérique
  gw: '100'                                       # ne pas changer pour Essonne Numérique

prefixes:
  lan_wan_lora: 100.76.16.0/23                    # ne pas changer pour Essonne Numérique : subnet LORA
  lan_wan_surete: [10.224.0.0/11, 100.76.0.0/20]  # ne pas changer pour Essonne Numérique : subnets Sureté Electronique

vprns:
  wholesale:
    - id: 700                                     # ne pas changer pour Essonne Numérique
  spoke:
    - id: {id_vprn_spoke}                                    # id vprn spoke qui collecte tous les services IPOE 
      name: {name_vprn_spoke}                     # pas d'espace, 32 caracteres max
      dhcp:
        subnet: 100.76.0.0/20
      interfaces:
        loopback:
          address: 100.76.15.254                 # derniere IP du pool
        dhcp: 
          address: 100.76.15.253                 # avant-derniere IP du pool
  hub:
    - id: {id_vprn_hub}                                   # id vprn hub interconnecté avec le DC (vDOM) 
      name: {name_vprn_hub}                      # pas d'espace, 32 caracteres max
      interfaces:
          subnet_interco_vDOM: 100.68.0.0/29     # subnet interco vDOM pour le service IPOE (Lora ou Sureté)
          sap:
            lag: 10                               # ne pas changer pour Essonne Numérique
            vlan: 309                             # à définir avec FreePro
            qos: {qos_hub}                              # numéro profil QOS : 995 pour LORA / 996 pour Sureté
          peer_as_bgp: 65200                      # AS FreePro  
"""
#

# Créer le template gitlab retail
# @param: str
# @return: yaml
def create_yaml_retail(nom_gfu, id_vprn, option_internet, option_internet_vlan, option_voip, id_vprn_hub = 0, id_vprn_spoke = 0):
    type_topologie_vpnip = 'fullmesh'
    if id_vprn_hub != 0 and id_vprn_spoke != 0:
        type_topologie_vpnip = 'h&s'
    #

    return f"""# Retail (auto-généré)

type_topologie_vpnip: '{type_topologie_vpnip}'                      # peut prendre les valeurs 'fullmesh' ou 'h&s'

nom_GFU_adherent: {nom_gfu.replace(' ', '-')}                    # Nom du GFU (projet) de l'Adhérent - à séparer par des "-" si necessaire et non des espaces

# ne pas changer pour Essonne Numérique #
liste_bng:
- bng: bng-sac91-01
  ip_system_bng: 10.50.0.1
- bng: bng-sac91-02
  ip_system_bng: 10.50.0.2
- bng: bng-log77-01
  ip_system_bng: 10.50.0.3
- bng: bng-log77-02
  ip_system_bng: 10.50.0.4

id_PP : 91                                        
as_number: 65000                                  # AS du service : 65000 pour VPN IP
AS_CPE: 65100  
AS_ADMIN: 65090
AS_VOIP: 65001 

id_topologie :      
  fullmesh: '000'
  hub: '010'     
  spoke: '020'   
  gw: '100'      

prefixes:
  loopback_unnumbered: 100.68.0.201/32            
  subnet_ip_cpe_pro: 100.124.0.0/19               # = IP_Admin_Pro = IP_INTERCO_CPE_PRO
  subnet_loopback_cpe: 100.124.32.0/19            # = IP_Service = Loopback CPE
##########################################

vprns:
  # ne pas changer pour Essonne Numérique #
  wholesale:
    - id: 700                                     
  admin_cpe:
    - id: 901
      vlan_ppp: 500
  voip:
    - id : 1701
  ##########################################
  hub:      
    - id: {id_vprn_hub}                                    # id VPRN hub - valeur incrémentale à partir de 2000
  spoke:
    - id: {id_vprn_spoke}                                    # id VPRN spoke qui collecte les sites distants (services PPP) - valeur incrémentale à partir de 2000
  fullmesh:
   - id: {id_vprn}                                     # valeur incrémentale à partir de 2000

##########################################
################ OPTIONS #################
##########################################
option_voip: {option_voip}                              # valeur par défaut - changer à "non" si aucune solution de telephonie n'est souhaitée
acces_internet: {option_internet}                           # valeur par défaut - changer à "oui" si service VPN IP avec sortie Internet par vDOM
interfaces:
 # ne pas changer pour Essonne Numérique #
 peer_as_bgp: 65200
 subnet_interco_vDOM: 100.68.0.0/29          
 sap:
   lag: 10                                   
   qos: 999                                  # numéro profil QOS : 999 pour VPN IP
 ##########################################
   vlan: {option_internet_vlan}                                 # à définir avec FreePro

# cas site centraux pour une topologie fullmesh
sites_centraux: 'non'                       # valeur par défaut - changer à "non" si service VPN IP avec sortie Internet par vDOM à la place
ip_cpe_centraux: [100.68.1.1, 100.68.1.2]   # @IP WAN = IP_INTERCO_CPE (@ qui monte le PPP) des CPE centraux
couple_bng: [bng-sac91-01, bng-log77-01]    # BNG où sont raccordés les CPE centraux
"""
#

# Génération d'un radius
# @param: str
# @return: str
def create_radius_request(gfu, username, password, ip, debit, id_vprn, id_cpe, mac_addr = None, subnet_vpnsur = None): 
    radius = None
    dns_a = '85.31.192.22' if re.search(r'\-INTE\-', username) else '100.64.0.66'
    dns_s = '85.31.193.22' if re.search(r'\-INTE\-', username) else '100.64.0.71'
    bgp_policy = ''
    if re.search(r'\-INTE\-', username):
        bgp_policy = 'bgp-sub-policy-cpe-int-transit'
    elif re.search(r'\-LWM\-', username):
        bgp_policy = 'bgp-sub-policy-cpe-lan-wifi'
    elif re.search(r'\-VPNIP\-', username):
        bgp_policy = 'bgp-sub-policy-cpe-vpn-ip'
    #
    debit_chapeau = 10 if debit > 500 and debit < 10 else 1
    profil = 'SLA_ADMIN'
    if not re.search(r'\-CPE\-', username):
        if re.search(r'\-INTE\-', username):
            profil = f'SLA_TRANSIT_{debit}M' if debit_chapeau == 1 else f'SLA_TRANSIT_{debit}G'
        elif re.search(r'\-VPNIP\-', username):
            profil = f'SLA_VPNIP_{debit}M' if debit_chapeau == 1 else f'SLA_VPNIP_{debit}G'
        #
    #

    if gfu == 'CD91 Hors College' and profil != 'SLA_ADMIN':
        profil += '_OSM_CD91'
    #

    if not ip and not id_cpe:
        return 'IP or ID_CPE is missing !'
    #

    if re.search(r'\-VPNIOT\-', username):
        radius = f"""INSERT INTO radcheck (username, attribute, op, value) SELECT '{mac_addr}', 'Auth-Type', ':=', 'Accept' WHERE NOT EXISTS (SELECT 1 FROM radcheck WHERE username = '{mac_addr}' AND attribute = 'Auth-Type' AND value = 'Accept');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Service-Type', ':=', 'Framed-User' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Service-Type' AND value = 'Framed-User');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Framed-IP-Address', ':=', '{ip}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Framed-IP-Address' AND value = '{ip}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Framed-IP-Netmask', ':=', '255.255.254.0' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Framed-IP-Netmask' AND value = '255.255.254.0');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Retail-Serv-Id', ':=', '1715' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Retail-Serv-Id' AND value = '1715');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Subsc-ID-Str', ':=', '{id_cpe}-IPOE' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Subsc-ID-Str' AND value = '{id_cpe}-IPOE');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Lease-Time', ':=', '7200' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Lease-Time' AND value = '7200');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Primary-Dns', ':=', '100.64.0.66' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Primary-Dns' AND value = '100.64.0.66');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Secondary-DNS', ':=', '100.64.0.71' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Secondary-DNS' AND value = '100.64.0.71');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Default-Router', ':=', '100.76.17.254' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Default-Router' AND value = '100.76.17.254');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Subsc-Prof-Str', ':=', 'RMS_250M' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Subsc-Prof-Str' AND value = 'RMS_250M');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-SLA-Prof-Str', ':=', 'SLA_LORA_10M' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-SLA-Prof-Str' AND value = 'SLA_LORA_10M');
"""
    elif re.search(r'\-VPNSUR\-', username):
        radius = f"""INSERT INTO radcheck (username, attribute, op, value) SELECT '{mac_addr}', 'Auth-Type', ':=', 'Accept' WHERE NOT EXISTS (SELECT 1 FROM radcheck WHERE username = '{mac_addr}' AND attribute = 'Auth-Type' AND value = 'Accept');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Service-Type', ':=', 'Framed-User' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Service-Type' AND value = 'Framed-User');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Framed-IP-Address', ':=', '{ip}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Framed-IP-Address' AND value = '{ip}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Framed-IP-Netmask', ':=', '255.255.240.0' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Framed-IP-Netmask' AND value = '255.255.240.0');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Retail-Serv-Id', ':=', '1714' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Retail-Serv-Id' AND value = '1714');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Subsc-ID-Str', ':=', '{id_cpe}-IPOE' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Subsc-ID-Str' AND value = '{id_cpe}-IPOE');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Lease-Time', ':=', '7200' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Lease-Time' AND value = '7200');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Primary-Dns', ':=', '100.64.0.66' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Primary-Dns' AND value = '100.64.0.66');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Secondary-DNS', ':=', '100.64.0.71' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Secondary-DNS' AND value = '100.64.0.71');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Default-Router', ':=', '100.76.15.254' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Default-Router' AND value = '100.76.15.254');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-Subsc-Prof-Str', ':=', 'RMS_250M' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-Subsc-Prof-Str' AND value = 'RMS_250M');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Alc-SLA-Prof-Str', ':=', 'SLA_SURETE_200M' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Alc-SLA-Prof-Str' AND value = 'SLA_SURETE_200M');
INSERT INTO radreply (username, attribute, op, value) SELECT '{mac_addr}', 'Framed-Route', ':=', '{subnet_vpnsur} {ip}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{mac_addr}' AND attribute = 'Framed-Route' AND value = '{subnet_vpnsur} {ip}');
"""
    else:
        radius = f"""INSERT INTO radcheck (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Cleartext-Password', ':=', '{password}' WHERE NOT EXISTS (SELECT 1 FROM radcheck WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Cleartext-Password' AND value = '{password}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Service-Type', ':=', 'Framed-User' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Service-Type' AND value = 'Framed-User');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Framed-Protocol', ':=', 'PPP' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Framed-Protocol' AND value = 'PPP');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Framed-IP-Address', ':=', '{ip}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Framed-IP-Address' AND value = '{ip}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Framed-IP-Netmask', ':=', '255.255.255.255' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Framed-IP-Netmask' AND value = '255.255.255.255');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Alc-Retail-Serv-Id', ':=', '{id_vprn}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Alc-Retail-Serv-Id' AND value = '{id_vprn}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Alc-Subsc-Prof-Str', ':=', 'RMS_{debit_chapeau}G' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Alc-Subsc-Prof-Str' AND value = 'RMS_{debit_chapeau}G');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Alc-SLA-Prof-Str', ':=', '{profil}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Alc-SLA-Prof-Str' AND value = '{profil}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Alc-Primary-Dns', ':=', '{dns_a}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Alc-Primary-Dns' AND value = '{dns_a}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Alc-Secondary-DNS', ':=', '{dns_s}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Alc-Secondary-DNS' AND value = '{dns_s}');
INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Alc-Subsc-ID-Str', ':=', '{id_cpe}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Alc-Subsc-ID-Str' AND value = '{id_cpe}');
"""

    if bgp_policy != '':
        radius += f"""INSERT INTO radreply (username, attribute, op, value) SELECT '{username}@essonnenumerique.com', 'Alc-BGP-Policy', ':=', '{bgp_policy}' WHERE NOT EXISTS (SELECT 1 FROM radreply WHERE username = '{username}@essonnenumerique.com' AND attribute = 'Alc-BGP-Policy' AND value = '{bgp_policy}');"""
    #
            
    result = f"""#### vm-freeradius-prod-01

{radius}
"""

    return result
#