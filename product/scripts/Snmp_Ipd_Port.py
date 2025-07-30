#==============================================================================================Bibliotheque 
#import pysnmp
import sys
import re
import subprocess
import math
import json
from math import log10
#==============================================================================================Mapping des données
speed_mapping = {
    "10": "10 Mbps",
    "100": "100 Mbps",
    "1000": "1 Gbps",
    "2500": "2.5 Gbps",
    "10000": "10 Gbps",
    "25000": "25 Gbps",
    "40000": "40 Gbps",
    "100000": "100 Gbps",
    "4294967295": "Vitesse inconnue ou bug SNMP"
}

type_sfp_mapping = {
        "0": "unknown",
        "1": "sc",
        "2": "gbic",
        "3": "solderedToMotherboard",
        "4": "sfp",
        "5": "pin300XBI",
        "6": "xenpak",
        "7": "xfp",
        "8": "xff",
        "9": "xfpe",
        "10": "xpak",
        "11": "x2",
        "12": "dwdmSfp",
        "13": "qSfp",
        "14": "invalid",
    }
type_sfp_mapping2 = {
        "0":"unknown",
        "1":"sc",
        "2":"gbic",
        #3:"SFP",
        "4":"esfp",
        "5":"copper",
        "6":"xfp",
        "7":"xenpak",
        "8":"transp  order",
        "9":"cfg",  

    }  
type_sfp_mapping3 = {
        "0":"unknown",
        "1":"gbic",
        "2":"moduleConnectorSolderedToMotherboard",
        "3":"SFP",
        "4":"xbi",
        "5":"xenpak",
        "6":"XFP",
        "7":"xff",
        "8":"xfpe",
        "9":"xpak",
        "10":"x2",
        "11":"DWDMSFP",
        "12":"qsfp",
        "13":"qsfpPlus",
        "14":"cfp",  
        }  
optical_mode_mapping = {
            "1": "notSupported",
            "2": "singleMode",
            "3": "multiMode5",
            "4": "multiMode6",
            "5": "noValue"
        }
type_connecteur_mapping = {
            "0": "unknown",
            "1": "sc",
            "2": "fiberChannel-Style1-CopperConnector",
            "3": "fiberChannel-Style2-CopperConnector",
            "4": "bnc_tnc",
            "5": "fiberChannelCoaxialHeaders",
            "6": "fiberJack",
            "7": "LC",
            "8": "mt-rj",
            "9": "mu",
            "10": "sg",
            "11": "opticalPigtail",
            "20": "hssdcll",
            "21": "copperPigtail"
            }
type_connecteur_mapping2 = {

            "0":"unknown",
            "1":"SC",
            "2":"fiberChannel-Style1-CopperConnector",
            "3":"fiberChannel-Style2-CopperConnector",
            "4":"bncortnc",
            "5":"fiberChannelCoaxialHeaders",
            "6":"fiberJack",
            "7":"LC",
            "8":"mt-rj",
            "9":"mu",
            "10":"sg",
            "11":"opticalPigtail",
            "32":"hssdcII",
            "33":"copperPigtail",
            "128":"copperGigE",
        }

#===============================================================================================Fonction pour les connexion
def net_snmp_olt_huawei(ip_equipement, oid):
    """
    Effectue une requête SNMP sur un equipement Huawei OLT avec l'OID specifie en utilisant la commande snmpget.
    
    Args:
        ip_equipement (str): Adresse IP de l'equipement SNMP.
        oid (str): OID e interroger.
        
    Returns:
        str: Valeur de l'OID interroge, ou None en cas d'erreur.
    """
    # Initialisation de la variable de retour
    return_value = None
    
    # Construction de la commande SNMP
    command = ['snmpget', '-v', '2c', '-c', 'Cpdeacpdea', ip_equipement, oid]
    
    try:
        # Execution de la commande SNMP et recuperation de la sortie
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        
        # Analyse de la sortie pour obtenir la valeur de l'OID
        lines = output.strip().split('\n')
        if len(lines) > 0:
            # La derniere ligne de la sortie contient la valeur de l'OID
            return_value = lines[-1].split(' ')[-1]
    
    except subprocess.CalledProcessError as e:
        # En cas d'erreur lors de l'execution de la commande SNMP
        print('Erreur lors de l\'execution de la commande SNMP:', e.output)
    
    # Retourner la valeur de l'OID ou None en cas d'erreur
    print(command)
    return return_value

def net_snmp(ip_equipement, oid):
    """
    Effectue une requête SNMP sur un equipement donne avec l'OID specifie en utilisant la commande snmpget.
    
    Args:
        ip_equipement (str): Adresse IP de l'equipement SNMP.
        oid (str): OID e interroger.
        
    Returns:
        str: Valeur de l'OID interroge, ou None en cas d'erreur.
    """
    # Initialisation de la variable de retour
    return_value = None
    
    # Construction de la commande SNMP avec les parametres specifies
    command = ['snmpget', '-v', '2c', '-c', 'cpdea', ip_equipement, oid]
    
    try:
        # Execution de la commande SNMP et recuperation de la sortie
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        
        # Analyse de la sortie pour obtenir la valeur de l'OID
        lines = output.strip().split('\n')
        if len(lines) > 0:
            # La derniere ligne de la sortie contient la valeur de l'OID
            return_value = lines[-1].split(' ')[-1]
    
    except subprocess.CalledProcessError as e:
        # En cas d'erreur lors de l'execution de la commande SNMP
        print('Erreur lors de l\'execution de la commande SNMP:', e.output)
    # Retourner la valeur de l'OID ou None en cas d'erreur
    return return_value

#===============================================================================================Classes pour SNMP_ipd
class MA5800:
    @staticmethod
    def send_snmp_command(ip_equipement, oid):
        command = ['snmpget', '-v', '2c', '-c', 'Cpdeacpdea', ip_equipement, oid]
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True).strip()
            return output.split(' ')[-1] if output else None
        except subprocess.CalledProcessError as e:
            print('Erreur lors de l\'execution de la commande SNMP:', e.output)
            return None

    @staticmethod
    def get_value(oid, port_numerique, ip_equipement):
        oid = oid + str(port_numerique)
        return MA5800.send_snmp_command(ip_equipement, oid)

    @staticmethod
    def Get_admin_status(port_numerique, ip_equipement):
        result = MA5800.get_value(".1.3.6.1.2.1.2.2.1.7.", port_numerique, ip_equipement)
        return result 

    @staticmethod
    def Get_oper_status(port_numerique, ip_equipement):
        result = MA5800.get_value(".1.3.6.1.2.1.2.2.1.8.", port_numerique, ip_equipement)
        return  result

    @staticmethod
    def Get_mtu_value(port_numerique, ip_equipement):
        return MA5800.get_value(".1.3.6.1.2.1.2.2.1.4.", port_numerique, ip_equipement)

    @staticmethod
    def Get_speed_value(port_numerique, ip_equipement):
        result = MA5800.get_value(".1.3.6.1.2.1.31.1.1.1.15.", port_numerique, ip_equipement)
        return speed_mapping.get(result, "Erreur")

    @staticmethod
    def Get_type_sfp(port_numerique, ip_equipement):
        result = MA5800.get_value(".1.3.6.1.4.1.2011.5.14.6.1.1.1.", port_numerique, ip_equipement)
        return type_sfp_mapping.get(result, "type non trouvé")

    @staticmethod
    def Get_longueur_onde(port_numerique, ip_equipement):
        result = MA5800.get_value(".1.3.6.1.4.1.2011.5.14.6.1.1.15.", port_numerique, ip_equipement)
        return f"{result}nm" if result and result > "0" else "unknown"

    @staticmethod
    def Get_optical_compliance(port_numerique, ip_equipement):
        result = MA5800.get_value(".1.3.6.1.4.1.2011.5.14.6.3.1.45.", port_numerique, ip_equipement)
        return f"{result}km" if result and result.isdigit() and int(result) > 0 else "unknown"

    @staticmethod
    def Get_vendor_name(port_numerique, ip_equipement):
        # Joindre les éléments de l'oid en une chaîne
        oid = ".1.3.6.1.4.1.2011.5.14.6.1.1.11." + str(port_numerique)
        command = ['snmpget', '-v', '2c', '-c', 'Cpdeacpdea', ip_equipement, oid]
        
        # Exécution de la commande et récupération de la sortie
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        vendor_name = output.split('STRING: ')[1].strip().strip('"')
        
        return vendor_name

    @staticmethod
    def Get_puissance_optique(oid, port_numerique, ip_equipement):
        result = MA5800.get_value(oid, port_numerique, ip_equipement)
        return round(float(int(result) * 0.000001), 2) if result else None

    @staticmethod
    def Get_Alarm(oid, port_numerique, ip_equipement):
        result = MA5800.get_value(oid, port_numerique, ip_equipement)
        return round(float(int(result) * 0.000001), 2) if result else None
  
class NE:
    """
    Classe regroupant les méthode concernant les cas d'équipement en "NE20", "NE40" ,"NE8000" 
    """
    def __init__(self) -> None:
        pass

    def Get_optical_mode(index , ip_equipement):

        #Rajout a la variable de oid la valeur du port numerique
        oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.1."+str(index)
        #envoie de la requete snmp via les parametres
        result = net_snmp(ip_equipement, oid)
        #en fonction de la valeur de result lui attribuer une valeur dans la mappage des donnees du type optique
        optical_mode = optical_mode_mapping.get(result, "type non trouvee")

        return optical_mode
    
    def Get_type_sfp(index , ip_equipement):

        #Rajout a la variable de oid la valeur du port numerique
        oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.10."+str(index)
        #envoie de la requete snmp via les parametres
        result = net_snmp(ip_equipement, oid)
        #en fonction de la valeur de result lui attribuer une valeur dans la mappage des donnees du type sfp
        type_sfp = type_sfp_mapping2.get(result, "unknown")

        return type_sfp

    def Get_type_connecteur(index , ip_equipement):

        oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.12."+str(index)
        result = net_snmp(ip_equipement, oid)
        if result:
            type_connecteur = type_connecteur_mapping.get(result, "Aucune donnée")

        else : 
            type_connecteur ="aucune donnee"

        return type_connecteur
    
    def Get_longueur_onde(index , ip_equipement):

        #Rajout a la variable de oid la valeur du port numerique
        oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.2."+str(index)
        #envoie de la requete snmp via les parametres
        result = net_snmp(ip_equipement, oid)

        #si  le resultat est superieur a 0 alors rajouter a result les caracrere nm
        if result is not None and result > "0" :
            longueur_onde = str(result)+"nm"
        #sinon il reçoi la chaine de caractere unknown
        else :
            longueur_onde = "unknown"

        return longueur_onde
    
    def Get_optical_compliance(index,ip_equipement):

        #Rajout a la variable de oid la valeur du port numerique
        oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.3."+str(index)
        #envoie de la requete snmp via les parametres
        result = net_snmp(ip_equipement, oid)
        optical_compliance=""

        if result is not None and result.isdigit():
            result = int(result)
            if result == 0:
                optical_compliance = "unknown"
            #si result est supérieur à 0 alors diviser le resultat par 1000 et rajouter km
            elif result > 0:
                optical_compliance = str(result / 1000) + "km"
        
        return optical_compliance

    def Get_vendor_name( index, ip_equipement):

        # Rajout à la variable oid la valeur du port numérique
        oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.24." + str(index)
        # Envoie de la requête SNMP via les paramètres
        result = net_snmp(ip_equipement, oid)
        vendor_name = result 
        return vendor_name
    
    def Get_vendor_pn(index,ip_equipement):

        #Rajout a la variable de oid la valeur du port numerique
        oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.25." +str(index)
        #envoie de la requete snmp via les parametres
        result = net_snmp(ip_equipement, oid)
        vendor_pn=result

        return vendor_pn
    
    def Get_puissance_optique(oid, index, ip_equipement):

        oid = oid + str(index)
        result = net_snmp(ip_equipement, oid)

        # Vérifier si result est une chaîne de caractères contenant un nombre
        try:
            puissance_optique = float(result) / 100
        except (ValueError, TypeError):
            puissance_optique = None  # Ou une valeur par défaut, selon votre besoin

        return puissance_optique

    def Get_alarm_warning(oid, index, ip_equipement):

        oid = oid + str(index)
        result = net_snmp(ip_equipement, oid)

        # Vérifier si result est une chaîne de caractères contenant un nombre
        try:
            alarm_warning = float(result) / 100
        except (ValueError, TypeError):
            alarm_warning = None  # Ou une valeur par défaut, selon votre besoin

        return alarm_warning
    
class ELSE :
    def Get_type_sfp (port_numerique , ip_equipement):
       
        #Rajout a la variable de oid la valeur du port numerique
        oid=".1.3.6.1.4.1.6527.3.1.2.2.4.2.1.25.1."+str(port_numerique)
        #envoie de la requete snmp via les parametres
        result = net_snmp(ip_equipement, oid)
        #en fonction de la valeur de result lui attribuer une valeur dans la mappage des donnees du type sfp
        type_sfp = type_sfp_mapping3.get(result, "type non trouvee")

        return type_sfp

    def Get_type_connecteur( port_numerique , ip_equipement):

        oid=".1.3.6.1.4.1.6527.3.1.2.2.4.2.1.30.1."+str(port_numerique)
        result = net_snmp(ip_equipement, oid)
        if result:
            type_connecteur=type_connecteur_mapping2.get(result, "inconnue")
        else :
            type_connecteur="aucune donnee"

        return type_connecteur
    
    def Get_longueur_onde(port_numerique , ip_equipement):

        oid=".1.3.6.1.4.1.6527.3.1.2.2.4.2.1.27.1."+str(port_numerique)
        result = net_snmp(ip_equipement , oid)
        
        longueur_ondes = str(result)+ "nm"

        return longueur_ondes

    def Get_puissance_optique(oid, port_numerique, ip_equipement):
        oid = oid + str(port_numerique)
        result = net_snmp(ip_equipement, oid)

        if result is None:  # Vérification si result est None
            return "None"

        try:
            result = float(result)
            if result <= 0:  # Vérification avant le logarithme
                return "None"
        except ValueError:
            return "None"

        puissance_optique = 10 * math.log10(result / 10 / 1000)
        return str(round(puissance_optique, 2))

    def Get_alarm_warning(oid, port_numerique, ip_equipement):
        oid = oid + str(port_numerique)
        result = net_snmp(ip_equipement, oid)
        
        if result is None:
            return "None"

        try:
            result = float(result)
        except ValueError:
            return "None"

        if result == 0:
            return "0"

        if result < 0:
            return "None"

        alarm_warning = 10 * math.log10(result / 10 / 1000)
        return str(round(alarm_warning, 2))
    
    def  Get_optical_compliance (port_numerique , ip_equipement):

        oid= ".1.3.6.1.4.1.6527.3.1.2.2.4.2.1.26.1."+str(port_numerique)
        result= net_snmp(ip_equipement , oid)
        optical_compliance=""
        if result is not None and "noSuch" in result:
            optical_compliance = None
    
        return optical_compliance

def Get_admin_status(port_numerique, ip_equipement):
    oid = ".1.3.6.1.2.1.2.2.1.7." + str(port_numerique)
    result = net_snmp(ip_equipement, oid)

    if result:
        # Extraire et convertir proprement la valeur
        if "INTEGER:" in str(result):
            valeur_str = result.split("INTEGER:")[-1].strip()
        else:
            valeur_str = str(result).strip()

        try:
            valeur = int(valeur_str)
            return "up" if valeur == 1 else "down"
        except ValueError:
            return "inconnu"
    else:
        return result

def Get_opper_status(port_numerique, ip_equipement):
    oid = ".1.3.6.1.2.1.2.2.1.8." + str(port_numerique)
    result = net_snmp(ip_equipement, oid)

    if result:
        if "INTEGER:" in str(result):
            valeur_str = result.split("INTEGER:")[-1].strip()
        else:
            valeur_str = str(result).strip()

        try:
            valeur = int(valeur_str)
            return "up" if valeur == 1 else "down"
        except ValueError:
            return "inconnu"
    else:
        return result


def Get_mtu_value(port_numerique , ip_equipement):
    
    #Rajout a la variable de oid la valeur du port numerique
    oid=".1.3.6.1.2.1.2.2.1.4." +str(port_numerique)
    #envoie de la requete snmp via les parametres
    result = net_snmp(ip_equipement , oid)
    mtuValue = result

    return mtuValue

def Get_speed_value(port_numerique, ip_equipement):
    # Utilisation de ifHighSpeed (en Mbit/s)
    oid = ".1.3.6.1.2.1.31.1.1.1.15." + str(port_numerique)

    # Envoie de la requête SNMP via les paramètres
    result = net_snmp(ip_equipement, oid)

    # Utilisation du mapping pour obtenir la vitesse correspondante
    speed_value = speed_mapping.get(result, "Vitesse inconnue")

    return speed_value


def calculate_index(port_parts):
    if int(port_parts[1]) == 1: 
        return str(int(port_parts[2]) + 16847105)
    elif int(port_parts[1]) == 2:
        return str(int(port_parts[2]) + 16912641)
    else:
        return str(int(port_parts[2]) + 16978177)
#==============================================================================================SNMP olt port
def snmp_ipd_port(equipement_dns , port , type_equipement):
    description = ""
    admin_status = ""
    oper_status = ""
    mtu = ""
    speed = ""
    type_sfp = ""
    type_connecteur = ""
    longueur_onde = ""
    puissance_optique_TX = ""
    puissance_optique_RX = ""
    low_alarm_TX = ""
    low_warning_TX = ""
    high_warning_TX = ""
    high_alarm_TX = ""
    low_alarm_RX = ""
    low_warning_RX = ""
    high_warning_RX = ""
    high_alarm_RX = ""
    optical_compliance = ""
    optical_mode = ""
    vendor_name = ""
    vendor_pn = ""
    validation_donnee_TX = ""
    validation_donnee_RX = ""
    #division de la valeur recuperer dans port à chaque / 

    match = re.match(r'GigabitEthernet(\d+)/(\d+)/(\d+)',port)
    if match :
        port_parts = match.groups()
        index = calculate_index(port_parts)
    match = re.match(r'access-(\d+)-(\d+)-(\d+)-(\d+)',port)
    if match:
        port_parts = port.split('-')[1:]
        index = calculate_index(port_parts)

    match = re.match(r'(\d+)/(\d+)/(\d+)', port)
    if match:
        port_parts = port.split('/')
        index = calculate_index(port_parts)

    port_ne20 = "GigabitEthernet" + port
    optical_mode=""
    vendor_name =""
    vendor_pn=""
    ip_equipement = equipement_dns 

    # Vérifier le type d'équipement
    if "MA5800" in type_equipement:
        # Construire la commande SNMP pour obtenir les descriptions de port
        commande = f"snmpwalk -c Cpdeacpdea -v2c {equipement_dns} 1.3.6.1.2.1.2.2.1.2"
    else:
        commande = f"snmpwalk -c cpdea -v2c {equipement_dns} 1.3.6.1.2.1.2.2.1.2"

    # Exécuter la commande SNMP, obtenir le résultat, le décoder et diviser par les sauts de ligne
    resultat = subprocess.check_output(commande, shell=True).decode().split('\n')

    port_numerique = None
    description = None

    for line in resultat:
        # Vérifier si la variable 'port' est présente dans la ligne actuelle
        if port in line:
            # Extraire l'OID de la ligne
            oids = line.split('=')[0].strip()

            # Extraire la valeur numérique du port depuis l'OID
            try:
                port_numerique = int(oids.rsplit('.', 1)[-1])
            except ValueError:
                continue

            # Extraire la description de la ligne
            match = re.search(r'\"(.*)\"', line)
            description = match.group(1) if match else None

            # Vérifier si une description a été trouvée
            if description:
                # Identifier si c'est une interface Ethernet ou 10-Gig Ethernet
                if description.startswith("10-Gig Ethernet"):
                    _, _, desc_reste = description.partition(",")
                    description = f"10-Gig Ethernet, {desc_reste.strip()}"
                elif "Ethernet" in description:
                    _, _, desc_reste = description.partition(",")
                    description = desc_reste.strip()

                # Extraire uniquement la partie entre \"
                match_interface = re.search(r'\\"([^\\"]+)\\"', description)
                if match_interface:
                    description = match_interface.group(1)  # Ne garde que le texte entre \"

            # Sortir de la boucle après avoir trouvé et traité les informations pertinentes
            break

    # Vérifier si la chaîne "GigabitEthernet" est présente dans la ligne
    if "GigabitEthernet" in line:
        # Construire la commande SNMP pour obtenir l'alias du port
        commande = f"snmpget -c cpdea -v2c {equipement_dns} 1.3.6.1.2.1.31.1.1.1.18.{port_numerique}"
        
        # Exécuter la commande SNMP et obtenir le résultat
        result = subprocess.getoutput(commande)

        # Initialiser la variable 'description' à None
        description = None

        # Rechercher une correspondance avec le motif regex dans le résultat
        match = re.search(r'"(.*?)"', result)

        # Si une correspondance est trouvée, extraire la description
        if match:
            description = match.group(1)

    # Verifie si le type d'equipement ne contient pas la chaîne "MA5800"
    if type_equipement =="MA5800" :
        # Recuperez l'etat administratif (adminstatus) du port
        adminstatus=MA5800.Get_admin_status(port_numerique , ip_equipement)
        
        operstatus=MA5800.Get_oper_status(port_numerique , ip_equipement)

        # Recuperez la MTU du port
        mtu = MA5800.Get_mtu_value(port_numerique , ip_equipement)
        # Recuperez la vitesse du port
        speed=MA5800.Get_speed_value(port_numerique , ip_equipement)

        # Creez la variable de statut en combinant adminstatus et operstatus
        status = str(adminstatus) + "-" + str(operstatus)

        type_sfp = MA5800.Get_type_sfp(port_numerique , ip_equipement)

        longueur_onde = MA5800.Get_longueur_onde(port_numerique , ip_equipement)
        
        optical_compliance = MA5800.Get_optical_compliance(port_numerique , ip_equipement)

        # Recuperer le nom du vendeur
        vendor_name = MA5800.Get_vendor_name(port_numerique , ip_equipement)

        oid =".1.3.6.1.4.1.2011.5.14.6.4.1.4."
        puissance_optique_TX = MA5800.Get_puissance_optique(oid , port_numerique , ip_equipement)

        oid = ".1.3.6.1.4.1.2011.5.14.6.4.1.5."
        puissance_optique_RX = MA5800.Get_puissance_optique(oid , port_numerique , ip_equipement)

        if puissance_optique_TX is not None:
            oid =".1.3.6.1.4.1.2011.5.14.6.9.1.1."
            low_alarm_TX = MA5800.Get_Alarm(oid , port_numerique , ip_equipement)

            oid = ".1.3.6.1.4.1.2011.5.14.6.9.1.2."
            high_alarm_TX = MA5800.Get_Alarm(oid , port_numerique , ip_equipement)

            oid =".1.3.6.1.4.1.2011.5.14.6.9.1.4."
            low_alarm_RX = MA5800.Get_Alarm(oid , port_numerique , ip_equipement)

            oid = ".1.3.6.1.4.1.2011.5.14.6.9.1.3."
            high_alarm_RX = MA5800.Get_Alarm(oid , port_numerique , ip_equipement)

    else :
        # Construit l'OID pour le statut administratif
        adminstatus = Get_admin_status(port_numerique ,ip_equipement)

        # Construit l'OID pour le statut operationnel
        operstatus = Get_opper_status(port_numerique , ip_equipement)

        # Construit l'OID pour l'unite de transfert maximale (MTU)
        mtu = Get_mtu_value(port_numerique , ip_equipement)

        # Construit l'OID pour la vitesse du port
        speed = Get_speed_value (port_numerique , ip_equipement)

        # Cree une chaîne de statut combinee avec le statut administratif et operationnel
        status = str(adminstatus) + "-" + str(operstatus)

        if "NE20" in type_equipement or "NE40" in type_equipement or "NE8000" in type_equipement:
            # Recuperez le mode optique
            optical_mode = NE.Get_optical_mode( index , ip_equipement)

            type_sfp=NE.Get_type_sfp( index , ip_equipement)

            # Recuperation de la longueur d'onde en convertissant la sortie SNMP
            type_connecteur =NE.Get_type_connecteur(index  , ip_equipement)

            longueur_onde = NE.Get_longueur_onde(index, ip_equipement)

            optical_compliance = NE.Get_optical_compliance(index , ip_equipement)

            vendor_name =NE.Get_vendor_name( index, ip_equipement)

            vendor_pn = NE.Get_vendor_pn( index , ip_equipement)

            # Recuperer la puissance optique TX
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.9." 
            puissance_optique_TX = NE.Get_puissance_optique(oid ,index ,ip_equipement)

            # Recuperer la puissance optique RX
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.8." 
            puissance_optique_RX = NE.Get_puissance_optique(oid ,index ,ip_equipement)     

            if puissance_optique_TX is not None:
                # Recuperation du le seuil bas d'alarme pour la puissance optique TX
                oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.15." 
                low_alarm_TX = NE.Get_alarm_warning(oid ,index,ip_equipement)

                # Recuperation du le seuil bas d'avetissement pour la puissance optique TX
                oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.22."
                low_warning_TX = NE.Get_alarm_warning(oid ,index,ip_equipement)

                # Recuperation du le seuil haut d'avertissement pour la puissance optique TX
                oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.23."
                high_warning_TX =NE.Get_alarm_warning(oid ,index,ip_equipement)

                # Recuperation du le seuil haut d'alarme pour la puissance optique TX
                oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.16."
                high_alarm_TX = NE.Get_alarm_warning(oid ,index,ip_equipement)   

                # Recuperation du le seuil bas d'alarme pour la puissance optique RX
                oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.13."
                low_alarm_RX = NE.Get_alarm_warning(oid ,index,ip_equipement)

                # Recuperation du le seuil bas d'avertissement pour la puissance optique RX
                oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.20."
                low_warning_RX =NE.Get_alarm_warning(oid ,index,ip_equipement)

                # Recuperation du le seuil haut d'avertissement pour la puissance optique RX
                oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.21."
                high_warning_RX = NE.Get_alarm_warning(oid ,index,ip_equipement)
                
                # Recuperation du le seuil haut d'alarme pour la puissance optique RX
                oid=".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.14."
                high_alarm_RX = NE.Get_alarm_warning(oid ,index,ip_equipement)

        else :
            type_sfp = ELSE.Get_type_sfp (port_numerique , ip_equipement)

            type_connecteur = ELSE.Get_type_connecteur(port_numerique , ip_equipement)

            longueur_onde = ELSE.Get_longueur_onde(port_numerique , ip_equipement)

            oid = ".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.16.1."
            puissance_optique_TX = ELSE.Get_puissance_optique(oid , port_numerique , ip_equipement)

            oid = ".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.21.1."
            puissance_optique_RX = ELSE.Get_puissance_optique(oid, port_numerique , ip_equipement)
    
            if puissance_optique_TX is not None:  

                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.17.1."
                low_warning_TX=ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)

                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.18.1."
                low_alarm_TX=ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)

                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.19.1."
                high_warning_TX=ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)

                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.20.1."
                high_alarm_TX=ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)

                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.22.1."
                low_warning_RX = ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)
                
                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.23.1."
                low_alarm_RX = ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)

                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.24.1."
                high_warning_RX = ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)

                oid=".1.3.6.1.4.1.6527.3.1.2.2.4.31.1.25.1."
                high_alarm_RX = ELSE.Get_alarm_warning(oid , port_numerique , ip_equipement)

            oid=".1.3.6.1.4.1.6527.3.1.2.2.4.2.1.26.1."
            optical_compliance = ELSE.Get_optical_compliance(port_numerique , ip_equipement)

    if low_alarm_TX is not None and low_alarm_TX != 'None' \
            and high_alarm_TX is not None and high_alarm_TX != 'None' \
            and low_alarm_RX is not None and low_alarm_RX != 'None' \
            and high_alarm_RX is not None and high_alarm_RX != 'None' \
            and puissance_optique_TX is not None and puissance_optique_TX != 'None' \
            and puissance_optique_RX is not None and puissance_optique_RX != 'None':

        low_alarm_TX = float(low_alarm_TX)
        high_alarm_TX = float(high_alarm_TX)
        low_alarm_RX = float(low_alarm_RX)
        high_alarm_RX = float(high_alarm_RX)
        puissance_optique_TX = float(puissance_optique_TX)
        puissance_optique_RX = float(puissance_optique_RX)

    # Comparaisons et assignations des validations
    if low_alarm_TX <= puissance_optique_TX <= high_alarm_TX:
        validation_donnee_TX = 1
    else:
        validation_donnee_TX = 0

    if low_alarm_RX <= puissance_optique_RX <= high_alarm_RX:
        validation_donnee_RX = 1
    else:
        validation_donnee_RX = 0
    if speed == "100 Gbps":

        Optical_Power_100G_Value = Optical_Power_100G(port,equipement_dns)
        info = {
            "description": description,
            "admin status": adminstatus,
            "oper status": operstatus,
            "mtu": mtu,
            "speed": speed,
            "type_sfp": type_sfp,
            "type_connecteur": type_connecteur,
            "longueur_onde": longueur_onde,
            "Puissance_Optique100G": Optical_Power_100G_Value,
            "optical_compliance": optical_compliance,
            "optical_mode": optical_mode,
            "vendor_name": vendor_name,
            "vendor_pn": vendor_pn,
            "Port_num": port_numerique,
            "dns_equipement": equipement_dns,
            "port": port
        }
    else:
        info = {
            "description": description,
            "admin status": adminstatus,
            "oper status": operstatus,
            "mtu": mtu,
            "speed": speed,
            "type_sfp": type_sfp,
            "type_connecteur": type_connecteur,
            "longueur_onde": longueur_onde,
            "puissance_optique_TX": puissance_optique_TX,
            "Validation_Puissance_Optique_TX": validation_donnee_TX,
            "puissance_optique_RX": puissance_optique_RX,
            "Validation_Puissance_Optique_RX": validation_donnee_RX,
            "low_alarm_TX": low_alarm_TX,
            "low_warning_TX": low_warning_TX,
            "high_warning_TX": high_warning_TX,
            "high_alarm_TX": high_alarm_TX,
            "low_alarm_RX": low_alarm_RX,
            "low_warning_RX": low_warning_RX,
            "high_warning_RX": high_warning_RX,
            "high_alarm_RX": high_alarm_RX,
            "optical_compliance": optical_compliance,
            "optical_mode": optical_mode,
            "vendor_name": vendor_name,
            "vendor_pn": vendor_pn,
            "Port_num": port_numerique,
            "dns_equipement": equipement_dns,
            "port": port
        }

    # Conversion de toutes les valeurs en str()
    return { cle: str(valeur) if not isinstance(valeur, (dict, list)) else valeur for cle, valeur in info.items() }

#=============================================================================================SNMP_olt_port
def snmp_olt_port(equipement_dns ,port_equipement, type_equipement ,version):
    commande = None
    result =""
    port_numerique = ""
    slot = None
    type_slot = ""
    adminstatus ="down"
    operstatus ="down"
    status = ""
    port=""
    oltSlotBuilder =""

    if "-" in port_equipement:
        port=port_equipement.split('-')
    if "/"in port_equipement :
        port = port_equipement.split('/')

    if len(port) >= 3:
        # Construisez le slot
        slot = "1/1/" + str(port[-1])

    oltIndexToSlot = {
        "1/1/1" : "4355",
        "1/1/2" : "4356",
        "1/1/3" : "4357",
        "1/1/4" : "4358",
        "1/1/5" : "4359",
        "1/1/6" : "4360",
        "1/1/7" : "4361",
        "1/1/8" : "4362"       
    }

    if (version == "R5.6" or re.search(r'R6.2', version)) and type_slot == "NELT-B":
        oltSlotBuilder = [
            [67108864, 100663296, 134217728, 167772160, 1086324736, 1088421888, 1090519040, 1092616192],
            [67117056,100671488,134225920,167780352,1086325248,1088422400,1090519552,1092616704],
            [67125248,100679680,134234112,167788544,1086325760,1088422912,1090520064,1092617216],
            [67133440,100687872,134242304,167796736,1086326272,1088423424,1090520576,1092617728],
            [67141632,100696064,134250496,167804928,1086326784,1088423936,1090521088,1092618240],
            [67149824,100704256,134258688,167813120,1086327296,1088424448,1090521600,1092618752],
            [67158016,100712448,134266880,167821312,1086327808,1088424960,1090522112,1092619264],
            [67166208,100720640,134275072,167829504,1086328320,1088425472,1090522624,1092619776],
            [67174400,100728832,134283264,167837696,1086328832,1088425984,1090523136,1092620288],
            [67182592,100737024,134291456,167845888,1086329344,1088426496,1090523648,1092620800],
            [67190784,100745216,134299648,167854080,1086329856,1088427008,1090524160,1092621312],
            [67198976,100753408,134307840,167862272,1086330368,1088427520,1090524672,1092621824],
            [67207168,100761600,134316032,167870464,1086330880,1088428032,1090525184,1092622336],
            [67215360,100769792,134324224,167878656,1086331392,1088428544,1090525696,1092622848],
            [67223552,100777984,134332416,167886848,1086331904,1088429056,1090526208,1092623360],
            [67231744,100786176,134340608,167895040,1086332416,1088429568,1090526720,1092623872],
            [67239936,100794368,134348800,167903232,1086332928,1088430080,1090527232,1092624384],
            [67248128,100802560,134356992,167911424,1086333440,1088430592,1090527744,1092624896],
            [67256320,100810752,134365184,167919616,1086333952,1088431104,1090528256,1092625408],
            [67264512,100818944,134373376,167927808,1086334464,1088431616,1090528768,1092625920],
            [67272704,100827136,134381568,167936000,1086334976,1088432128,1090529280,1092626432],
            [67280896,100835328,134389760,167944192,1086335488,1088432640,1090529792,1092626944],
            [67289088,100843520,134397952,167952384,1086336000,1088433152,1090530304,1092627456],
            [67297280,100851712,134406144,167960576,1086336512,1088433664,1090530816,1092627968],
            [67305472,100859904,134414336,167968768,1086337024,1088434176,1090531328,1092628480],
            [67313664,100868096,134422528,167976960,1086337536,1088434688,1090531840,1092628992],
            [67321856,100876288,134430720,167985152,1086338048,1088435200,1090532352,1092629504],
            [67330048,100884480,134438912,167993344,1086338560,1088435712,1090532864,1092630016],
            [67338240,100892672,134447104,168001536,1086339072,1088436224,1090533376,1092630528],
            [67346432,100900864,134455296,168009728,1086339584,1088436736,1090533888,1092631040],
            [67354624,100909056,134463488,168017920,1086340096,1088437248,1090534400,1092631552],
            [67362816,100917248,134471680,168026112,1086340608,1088437760,1090534912,1092632064],
            [67371008,100925440,134479872,168034304,1086341120,1088438272,1090535424,1092632576],
            [67379200,100933632,134488064,168042496,1086341632,1088438784,1090535936,1092633088],
            [67387392,100941824,134496256,168050688,1086342144,1088439296,1090536448,1092633600],
            [67395584,100950016,134504448,168058880,1086342656,1088439808,1090536960,1092634112]
        ]
    else :
        oltSlotBuilder = [
            [67108864,100663296,134217728,167772160,201326592,234881024,268435456,301989888],
            [67117056,100671488,134225920,167780352,201334784,234889216,268443648,301998080],
            [67125248,100679680,134234112,167788544,201342976,234897408,268451840,302006272],
            [67133440,100687872,134242304,167796736,201351168,234905600,268460032,302014464],
            [67141632,100696064,134250496,167804928,201359360,234913792,268468224,302022656],
            [67149824,100704256,134258688,167813120,201367552,234921984,268476416,302030848],
            [67158016,100712448,134266880,167821312,201375744,234930176,268484608,302039040],
            [67166208,100720640,134275072,167829504,201383936,234938368,268492800,302047232],
            [67174400,100728832,134283264,167837696,201392128,234946560,268500992,302055424],
            [67182592,100737024,134291456,167845888,201400320,234954752,268509184,302063616],
            [67190784,100745216,134299648,167854080,201408512,234962944,268517376,302071808],
            [67198976,100753408,134307840,167862272,201416704,234971136,268525568,302080000],
            [67207168,100761600,134316032,167870464,201424896,234979328,268533760,302088192],
            [67215360,100769792,134324224,167878656,201433088,234987520,268541952,302096384],
            [67223552,100777984,134332416,167886848,201441280,234995712,268550144,302104576],
            [67231744,100786176,134340608,167895040,201449472,235003904,268558336,302112768],
            [67239936,100794368,134348800,167903232,201457664,235012096,268566528,302120960],
            [67248128,100802560,134356992,167911424,201465856,235020288,268574720,302129152],
            [67256320,100810752,134365184,167919616,201474048,235028480,268582912,302137344],
            [67264512,100818944,134373376,167927808,201482240,235036672,268591104,302145536],
            [67272704,100827136,134381568,167936000,201490432,235044864,268599296,302153728],
            [67280896,100835328,134389760,167944192,201498624,235053056,268607488,302161920],
            [67289088,100843520,134397952,167952384,201506816,235061248,268615680,302170112],
            [67297280,100851712,134406144,167960576,201515008,235069440,268623872,302178304],
            [67305472,100859904,134414336,167968768,201523200,235077632,268632064,302186496],
            [67313664,100868096,134422528,167976960,201531392,235085824,268640256,302194688],
            [67321856,100876288,134430720,167985152,201539584,235094016,268648448,302202880],
            [67330048,100884480,134438912,167993344,201547776,235102208,268656640,302211072],
            [67338240,100892672,134447104,168001536,201555968,235110400,268664832,302219264],
            [67346432,100900864,134455296,168009728,201564160,235118592,268673024,302227456],
            [67354624,100909056,134463488,168017920,201572352,235126784,268681216,302235648],
            [67362816,100917248,134471680,168026112,201580544,235134976,268689408,302243840],
            [67371008,100925440,134479872,168034304,201588736,235143168,268697600,302252032],
            [67379200,100933632,134488064,168042496,201596928,235151360,268705792,302260224],
            [67387392,100941824,134496256,168050688,201605120,235159552,268713984,302268416],
            [67395584,100950016,134504448,168058880,201613312,235167744,268722176,302276608]
        ]

    port_numerique = oltSlotBuilder[int(port[-1])][int(port[-2])]

    # Construisez la commande SNMP pour obtenir le type de slot
    commande = f"snmpget -c cpdea -v2c {equipement_dns} 1.3.6.1.4.1.637.61.1.23.3.1.3.{oltIndexToSlot.get(slot)}"
    result = subprocess.getoutput(commande)

    # Utilisez une expression régulière pour extraire le type de slot
    match = re.search(r'STRING: "(.*)"', result)
    
    if match:
        type_slot = match.group(1)

    if (type_slot == "NELT-B" or type_slot == "FELT-B"):
        # Construisez la commande SNMP pour obtenir le statut administratif
        commande = f"snmpget -c cpdea -v2c {equipement_dns} 1.3.6.1.2.1.2.2.1.7.{port_numerique}"
        result1 = subprocess.getoutput(commande)

        # Recherchez la correspondance dans le résultat
        match = re.search(r'ifAdminStatus\.{0} = INTEGER: (\w+)'.format(port_numerique), result)
        adminstatus = match.group(1) if match else None

        # Construisez la commande SNMP pour obtenir le statut opérationnel
        commande = f"snmpget -c cpdea -v2c {equipement_dns} 1.3.6.1.2.1.2.2.1.8.{port_numerique}"
        result = subprocess.getoutput(commande)

        # Recherchez la correspondance dans le résultat
        match = re.search(r'ifOperStatus\.{0} = INTEGER: (\w+)'.format(port_numerique), result)
        operstatus = match.group(1) if match else None

        # Construisez le statut global
        status = f"{adminstatus}-{operstatus}"
        # Vérifiez si les correspondances ont été trouvées avant d'accéder aux groupes
        if adminstatus is not None and operstatus is not None:
            
            # Vérifiez le statut global
            if "down-" in status:
                status = "down-down"
            elif "up-" in status:
                pass 
            else:
                status = "down-down"

    # Affichez les résultats
    #return(f" status:{status}\n adminstatus :{adminstatus}\n operstatus :{operstatus}\n")
    
    return {"status":status, "adminstatus":adminstatus, "operstatus":result1}

#=============================================================================================100G_Optical_Power

def convert_to_dbm(value):
    try:
        value = float(value)
        if value > 0:
            dbm = 10 * math.log10((value / 10) / 1000)
            return round(dbm, 2)
    except (ValueError, TypeError):
        pass
    return None

def get_oid_values(ip_device, port_num):
    oids = {
        "Puissance_Optique_TX": [
            f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.12.1.{port_num}.{i}" for i in range(1, 5)
        ],
        "Puissance_Optique_RX": [
            f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.17.1.{port_num}.{i}" for i in range(1, 5)
        ],
        "LowAlarmTX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.13.1.{port_num}.1"],
        "HighAlarmTX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.15.1.{port_num}.1"],
        "LowWarningTX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.14.1.{port_num}.1"],
        "HighWarningTX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.16.1.{port_num}.1"],
        "LowAlarmRX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.18.1.{port_num}.1"],
        "HighAlarmRX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.20.1.{port_num}.1"],
        "LowWarningRX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.19.1.{port_num}.1"],
        "HighWarningRX": [f".1.3.6.1.4.1.6527.3.1.2.2.4.66.1.21.1.{port_num}.1"]
    }

    results = {}

    # Récupération et stockage des seuils
    seuils = {}
    for seuil in ["LowAlarmTX", "HighAlarmTX", "LowWarningTX", "HighWarningTX",
                  "LowAlarmRX", "HighAlarmRX", "LowWarningRX", "HighWarningRX"]:
        value = net_snmp(ip_device, oids[seuil][0])
        dbm_value = convert_to_dbm(value) if value else None
        seuils[seuil] = dbm_value
        results[f"{seuil}_1"] = dbm_value

    # Traitement des puissances optiques et validation
    for key in ["Puissance_Optique_TX", "Puissance_Optique_RX"]:
        for i, oid in enumerate(oids[key], start=1):
            value = net_snmp(ip_device, oid)
            dbm_value = convert_to_dbm(value) if value else None
            results[f"{key}_{i}"] = dbm_value

            # Validation en fonction des seuils
            if dbm_value is not None:
                if "TX" in key:
                    is_valid = int(seuils["LowAlarmTX"] <= dbm_value <= seuils["HighAlarmTX"])
                    results[f"Validation_Puissance_Optique_TX_{i}"] = is_valid
                elif "RX" in key:
                    is_valid = int(seuils["LowAlarmRX"] <= dbm_value <= seuils["HighAlarmRX"])
                    results[f"Validation_Puissance_Optique_RX_{i}"] = is_valid

    return results

def get_port_num_from_ifName(ip_device,port_search):
    command = ['snmpwalk','-c','cpdea','-v2c',ip_device,'1.3.6.1.2.1.31.1.1.1.1']
    print(command)
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        lines = output.strip().split('\n')
        for line in lines:
            match = re.search(r'iso\.3\.6\.1\.2\.1\.31\.1\.1\.1\.1\.(\d+)\s+=\s+STRING:\s+"([^"]+)"', line)
            #match = re.search(r'IF-MIB::ifName\.(\d+) = STRING: (.+)', line)
            if match:
                num = int(match.group(1))
                name = match.group(2).strip()
                if name == port_search:
                    return num -1
                
        return None
    except subprocess.CalledProcessError as e :
        return None
    
def Optical_Power_100G(port,equipement_dns):
    port_num = get_port_num_from_ifName(equipement_dns, port)
    oid_values = get_oid_values(equipement_dns, port_num)
    return oid_values