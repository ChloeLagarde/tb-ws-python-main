#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

# 
# @file		WholesaleEssonne.py
#

# LIBRAIRIES
import re, os, subprocess, shutil, mysql.connector
from mysql.connector import connection

# VARIABLES
GIT_URL = "https://gitlab.m2m.axione.fr/axione-dif-ingenierie/essonne-numerique"
GIT_TOKEN = "glpat-ywGWr3r_aK7Jb2v87JYy"

AX_PROXY = "proxy.query.consul:80"

RDB_USER = "ame"
RDB_PASS = "-G4xVj43="

# METHODES

# Créer le template gitlab wholesale
# @param: str
# @return: yaml
def create_yaml(service_name, olt_name, ip_mgmt_olt, bng_a, ip_bng_a, bng_s, ip_bng_s, edg_a, ip_edg_a, lag_edg_a, edg_b, ip_edg_b, lag_edg_b):
    vlan_olt = 500 if service_name == 'PPP' else 501
    type_equipment = 'olt' if re.match('olt-', olt_name) else 'edg'

    return f"""# Wholesale (auto-généré)
# {olt_name}

type_authent_collecte : {service_name}                                    # indiquer si la collecte est en PPP pour le VPN IP ou en IPOE pour LORA/Sureté Elec : peut prendre les valeurs 'PPP', 'IPOE'
service_ipoe : 'Lora'                                           # peut prendre les valeurs 'Lora' , 'Surete'
type_collecte_wholesale: {type_equipment}                                    # indiquer si la collecte du CPE se fait sur un OLT ou sur un EDG d'aggregation : peut prendre les valeurs 'olt', 'edg'

abreviation_projet: EN                                          # valeur fixe - ne pas changer pour Essonne Numérique - identique à celle du YAML Radius
id_PP : 91                                                      # valeur fixe - ne pas changer pour Essonne Numérique
id_vprn : 700                                                   # valeur fixe - ne pas changer pour Essonne Numérique
AS_vprn : 65070                                                 # valeur fixe - ne pas changer pour Essonne Numérique
subnet_intf_unnumbered : 100.68.0.200/29                        # valeur fixe - ne pas changer pour Essonne Numérique
subnet_redundant_intf : [100.68.0.100/31, 100.68.0.102/31]      # valeur fixe - ne pas changer pour Essonne Numérique

### Spécifique à un CPE collecté sur OLT

olt: {olt_name}
ip_mgmt_olt: {ip_mgmt_olt}

id_vpls_olt : {vlan_olt}                                               # peut prendre les valeurs '500' , '501' // VPN-IP (PPP) = 500 et LORA/SURETE (IPOE) = 501
id_vlan_olt : {vlan_olt}                                               # peut prendre les valeurs '500' , '501' // VPN-IP (PPP) = 500 et LORA/SURETE (IPOE) = 501
id_vlan_interne_olt : [101, 102]                                # Spécifique à collecte IPOE LORA et Sureté - peut prendre les valeurs '102' pour Lora' , et '101' pour Sureté

interco_edgs_olt:               # valeur incrémentale sur les BNG (show pw-port) : 1 pw-port/OLT
- edg: {edg_a}
  ip_system_edg: {ip_edg_a}
  lag_edg: {lag_edg_a}
- edg: {edg_b}
  ip_system_edg: {ip_edg_b}
  lag_edg: {lag_edg_b}

### Spécifique à un CPE collecté sur EDG (les champs peuvent etre laissés vides si la collecte du CPE se fait sur un OLT)

edg_racco_cpe : edg-sac91-01
ip_system_edg_cpe: 10.50.0.8
port_racco_cpe: 1/1/9
port_descr_additionnel: CPE CD91 - CD91 DC Primaire              # optionnel - laisser vide pour ne rien ajouter à la description
acces: 1g                                                        # peut prendre les valeurs '1g' ou '10g'
sfp_cwdm4: oui                                                   # peut prendre les valeurs 'oui' ou 'non'
id_vlan_wholesale_cpe: 500                                       # valeur fixe - ne pas changer pour Essonne Numérique
zone_edg: sud                                                    # peut prendre les valeurs 'nord' ou 'sud'

### Commun aux 2 types de collecte Wholesale (sur OLT/sur EDG)

cple_bng:                   # cf. STD de plaque EN § Zonage OLT/BNG
- bng: {bng_a}
  ip_system_bng: {ip_bng_a}
  statut_bng: actif
- bng: {bng_s}
  ip_system_bng: {ip_bng_s}
  statut_bng: standby
"""
#

# Créer le template gitlab wholesale
# @param: str
# @return: json
def generate_config_wholesale_enu(olt_name):
    sql_connector28 = None
    sql_connector56 = None
    cursor = None
    yaml_ppp = None
    yaml_ipoe = None
    config_ppp = None
    config_ipoe = None

    if olt_name is not None:
        if re.search(r'olt-[\w\d]{5}-\d{2}', olt_name):
            try:
                sql_connector28 = connection.MySQLConnection(user=RDB_USER, password=RDB_PASS,
                                                        host='10.1.80.77',
                                                        database='geco',
                                                        port=3306,
                                                        charset='utf8')
            except mysql.connector.Error:
                return {'error': 'Connection closed to 10.1.80.77'}
            #

            sql_query = "SELECT * FROM referenciel_alcatel WHERE node LIKE %s"
            data = (olt_name + '%',)
            cursor = sql_connector28.cursor()
            cursor.execute(sql_query, data)
            ref_alcatel_result = cursor.fetchone()
            if ref_alcatel_result:
                olt_ip = ref_alcatel_result[1]
                olt_dns = ref_alcatel_result[2]
                olt_zone = ref_alcatel_result[4]

                sql_query = "SELECT pp, node, port, zone_boucle, type_boucle, topologie, debit, plage_ip, last_updated FROM 7x50_ports WHERE node LIKE %s AND plage_ip = %s"
                data = ('edg-%', olt_ip,)
                cursor = sql_connector28.cursor()
                cursor.execute(sql_query, data)
                ports_7x50 = cursor.fetchall()

                if ports_7x50:
                    edg_dns = []
                    edg_name = []
                    edg_port = []
                    edg_ip = []
                    edg_zone = []
                    bng_dns = []
                    bng_ip = []

                    for row in ports_7x50:
                        pp, node, port, zone_boucle, type_boucle, topologie, debit, plage_ip, last_updated = row

                        edg_name.append(node)
                        edg_port.append(port)
                        edg_zone.append(zone_boucle)

                        sql_query = "SELECT ip, node FROM referenciel_alcatel WHERE node LIKE %s"
                        data = (node + '%',)
                        cursor = sql_connector28.cursor()
                        cursor.execute(sql_query, data)
                        ref_alcatel_result_edg = cursor.fetchone()

                        edg_dns.append(ref_alcatel_result_edg[1])
                        edg_ip.append(ref_alcatel_result_edg[0])
                    #

                    edg_a = edg_name[0]
                    ip_edg_a = edg_ip[0]
                    edg_b = edg_name[1]
                    ip_edg_b = edg_ip[1]

                    try:
                        sql_connector56 = connection.MySQLConnection(user=RDB_USER, password=RDB_PASS,
                                                                host='10.1.80.229',
                                                                database='essonne_numerique',
                                                                port=3306,
                                                                charset='utf8')
                    except mysql.connector.Error:
                        return {'error': 'Connection closed to 10.1.80.229'}
                    #

                    sql_query = "SELECT bng_1, bng_2 FROM couple_bng WHERE zone = %s"
                    data = (olt_zone,)
                    cursor = sql_connector56.cursor()
                    cursor.execute(sql_query, data)
                    couple_bng_result = cursor.fetchone()
                    
                    for cpl_bng in couple_bng_result:
                        sql_query = "SELECT dns_bng, ip_bng FROM bng WHERE id_bng = %s"
                        data = (cpl_bng,)
                        cursor = sql_connector56.cursor()
                        cursor.execute(sql_query, data)
                        bng_result = cursor.fetchone()
                        bng_dns.append(bng_result[0])
                        bng_ip.append(bng_result[1])
                    #

                    bng_a = bng_dns[0].split('.')[0]
                    ip_bng_a = bng_ip[1]
                    bng_s = bng_dns[1].split('.')[0]
                    ip_bng_s = bng_ip[1]
                    if edg_zone[0] == edg_zone[1]:
                        lag_edg_a = edg_zone[0]
                        lag_edg_b = edg_zone[1]
                    else:
                        return {'error': 'Bad request into essonne_numerique.bng table'}
                    #

                    olt_trigramme = olt_name.split('-')[1].upper()
                    pw_port = olt_ip.split('.')[-1]

                    if olt_trigramme and olt_ip and bng_a and ip_bng_a and bng_s and ip_bng_s and pw_port and edg_a and ip_edg_a and lag_edg_a and edg_b and ip_edg_b and lag_edg_b:
                        template_yaml_ppp = create_yaml('PPP', olt_name, olt_ip, bng_a, ip_bng_a, bng_s, ip_bng_s, edg_a, ip_edg_a, lag_edg_a, edg_b, ip_edg_b, lag_edg_b)
                        template_yaml_ipoe = create_yaml('IPOE', olt_name, olt_ip, bng_a, ip_bng_a, bng_s, ip_bng_s, edg_a, ip_edg_a, lag_edg_a, edg_b, ip_edg_b, lag_edg_b)

                        sql_query = "SELECT COUNT(*) FROM olt WHERE node = %s"
                        data = (olt_name,)
                        cursor.execute(sql_query, data)
                        olt_check = cursor.fetchone()

                        if olt_check[0] < 1:
                            sql_query = "INSERT INTO olt VALUES(%s, %s, %s, %s, %s, %s, %s, NULL, NULL)"
                            data = (olt_name, olt_zone, edg_a, ip_edg_a, edg_b, ip_edg_b, pw_port,)
                            cursor.execute(sql_query, data)
                            sql_connector56.commit()
                        #

                        sql_query = "SELECT * FROM olt WHERE node = %s"
                        data = (olt_name,)
                        cursor.execute(sql_query, data)
                        olt_result = cursor.fetchone()

                        if olt_result:                            
                            REPO_URL = f"https://oauth2:{GIT_TOKEN}@gitlab.m2m.axione.fr/axione-dif-ingenierie/essonne-numerique.git"
                            git_path = "essonne-numerique/DIF Réseau/Configs/Services/Wholesale"

                            if not os.path.exists("essonne-numerique"):
                                subprocess.run(["git", "clone", REPO_URL, 'essonne-numerique'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            else:
                                shutil.rmtree("essonne-numerique")
                                subprocess.run(["git", "clone", REPO_URL, 'essonne-numerique'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                            subprocess.run(["git", "checkout", "main"], cwd='essonne-numerique', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            yaml_file_path = os.path.join(git_path, "services_wholesale.yaml")
                            os.chmod(yaml_file_path, 0o755)
                            cfg_file_path = os.path.join(git_path, "config_svc_wholesale.txt")
                            os.chmod(cfg_file_path, 0o755)

                            # Générération config PPP
                            with open(yaml_file_path, 'w', encoding='utf-8') as file:
                                file.write(template_yaml_ppp)
                            #

                            yaml_ppp = template_yaml_ppp

                            script_path = os.path.join(git_path, "generate_cfg_svc_wholesale.py")
                            os.chmod(script_path, 0o755)

                            if os.path.exists(script_path):
                                subprocess.run(["python3", "generate_cfg_svc_wholesale.py", "-y", "services_wholesale.yaml", "-t", "template_cfg_svc_wholesale.j2", "-o", "config_svc_wholesale.txt"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

                                status_result = subprocess.run(["git", "status", "--porcelain"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
                                status_lines = status_result.stdout.splitlines()
                                status_lines_filtered = [
                                    line for line in status_lines 
                                    if not line.endswith(".sh") and (line.strip().startswith("A ") or line.strip().startswith("M "))
                                ]
                                if status_lines_filtered:
                                    subprocess.run(["git", "add", "services_wholesale.yaml", "config_svc_wholesale.txt"], cwd=git_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                                    commit_result = subprocess.run(["git", "commit", "-m", f"Auto-update {olt_name} script AME"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                    cfg_file_content = None
                                    with open(cfg_file_path, 'r', encoding='utf-8') as f:
                                        cfg_file_content = f.read()
                                    #
                                    cfg_file_content = re.sub(r'(?m)^\s+', '', cfg_file_content)
                                    cfg_file_content = cfg_file_content.replace(f'configure service ', f'\nconfigure service ')
                                    cfg_file_content = cfg_file_content.replace(f'admin save', f'\nadmin save\n')
                                    cfg_file_content = cfg_file_content.replace(f'------------------------------------------------------------------------------------', f'')
                                    cfg_file_content = cfg_file_content.replace(f'Configuration service wholesale OLT - ', f'#### ')
                                    cfg_file_content = cfg_file_content.replace(f'Configs service wholesale EDG - ', f'#### ')
                                    cfg_file_content = cfg_file_content.replace(f'Configs service wholesale BNG - ', f'#### ')
                                    config_ppp = cfg_file_content

                                    sql_query = "UPDATE olt SET configs_ppp = %s WHERE node = %s"
                                    data = (cfg_file_content, olt_name,)
                                    cursor.execute(sql_query, data)
                                    sql_connector56.commit()
                                #
                            else:
                                return {'error': 'An error occured during gitlab configuration ppp mode'}
                            #

                            # Génération config IPOE
                            with open(yaml_file_path, 'w', encoding='utf-8') as file:
                                file.write(template_yaml_ipoe)
                            #

                            yaml_ipoe = template_yaml_ipoe

                            script_path = os.path.join(git_path, "generate_cfg_svc_wholesale.py")
                            os.chmod(script_path, 0o755)

                            if os.path.exists(script_path):
                                subprocess.run(["python3", "generate_cfg_svc_wholesale.py", "-y", "services_wholesale.yaml", "-t", "template_cfg_svc_wholesale.j2", "-o", "config_svc_wholesale.txt"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

                                status_result = subprocess.run(["git", "status", "--porcelain"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
                                status_lines = status_result.stdout.splitlines()
                                status_lines_filtered = [
                                    line for line in status_lines 
                                    if not line.endswith(".sh") and (line.strip().startswith("A ") or line.strip().startswith("M "))
                                ]
                                if status_lines_filtered:
                                    subprocess.run(["git", "add", "services_wholesale.yaml", "config_svc_wholesale.txt"], cwd=git_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                                    commit_result = subprocess.run(["git", "commit", "-m", f"Auto-update {olt_name} script AME"], cwd=git_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                    cfg_file_content = None
                                    with open(cfg_file_path, 'r', encoding='utf-8') as f:
                                        cfg_file_content = f.read()
                                    #
                                    cfg_file_content = re.sub(r'(?m)^\s+', '', cfg_file_content)
                                    cfg_file_content = cfg_file_content.replace(f'configure service ', f'\nconfigure service ')
                                    cfg_file_content = cfg_file_content.replace(f'admin save', f'\nadmin save\n')
                                    cfg_file_content = cfg_file_content.replace(f'------------------------------------------------------------------------------------', f'')
                                    cfg_file_content = cfg_file_content.replace(f'Configuration service wholesale OLT - ', f'#### ')
                                    cfg_file_content = cfg_file_content.replace(f'Configs service wholesale EDG - ', f'#### ')
                                    cfg_file_content = cfg_file_content.replace(f'Configs service wholesale BNG - ', f'#### ')
                                    config_ipoe = cfg_file_content

                                    sql_query = "UPDATE olt SET configs_ipoe = %s WHERE node = %s"
                                    data = (cfg_file_content, olt_name,)
                                    cursor.execute(sql_query, data)
                                    sql_connector56.commit()
                                #
                            else:
                                return {'error': 'An error occured during gitlab configuration ipoe mode'}
                            #

                            shutil.rmtree("essonne-numerique")

                            return {
                                'yaml ppp': f'{yaml_ppp}',
                                'yaml ipoe': f'{yaml_ipoe}',
                                'config ppp': f'{config_ppp}',
                                'config ipoe': f'{config_ipoe}',
                            }
                        else:
                            return {'error': 'Olt device is missing into geco.olt table'}
                        #
                    else:
                        return {'error': 'Yaml template unavailable'}
                    #
                else:
                    return {'error': 'Bad request into geco.7x50_ports table'}
                #
            else:
                return {'error': 'Bad request into geco.referentiel_alcatel table'}
            #
        else:
            return {'error': 'Olt name is not good'}
        #
    else:
        return {'error': 'Olt name is required'}
    #
#