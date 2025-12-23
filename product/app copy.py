# -*- coding: utf-8 -*-

# 
# @file		app.py
#

# LIBRAIRIES
import re, subprocess, shlex
from flask import Flask, request, jsonify
from scripts.Get_equipment_ws import *
from flask_restx import Api, Resource, fields, Namespace, reqparse
from scripts.Ekinops.scriptEkinopsPrincipal import *
from scripts.Nokia.scriptNokiaPrincipal import *
from scripts.OLT.OLT import *
from scripts.EssonneNumerique.Logs import *
from scripts.EssonneNumerique.Services import *
from scripts.EssonneNumerique.Wholesale import *
from scripts.PBB.ClassPBBWeb import *
from scripts.PBB.Service import *
from scripts.SocleNational.ServicesSocle import *

# FLASK
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
api = Api(app, version='1.7', title='WS TB Python')

# NAMESPACE
ns_service = Namespace('service', description='Endpoints pour la gestion d\'un service')
ns_equipment = Namespace('equipment', description='Endpoints pour la gestion des équipements')
ns_tool = Namespace('tool', description='Endpoints pour la gestion avec les outils')
ns_command = Namespace('command', description='Endpoints pour l\'exécution des commandes')
ns_logs = Namespace('logs', description='Endpoints pour la visualisation des logs')

# MODELES
service_model = ns_service.model('Service', { 'id': fields.String(required=True, description='ID de service') })
equipments_model = ns_equipment.model('Equipment', { 'name': fields.String(required=True, description='Nom de l\'equipement') })
service_model_json_post = ns_service.model("Body_create_service", { # Ajout d'un service
    "equipement": fields.String(required=False, description="Nom de l'équipement"),
    "port": fields.String(required=False, description="Port de l'équipement"),
    "vprn": fields.String(required=False, description="ID du VPRN"),
    "techno": fields.String(required=False, description="Technologie"),
    "type_cpe": fields.String(required=False, description="Type de CPE"),
    "type_ont": fields.String(required=False, description="Type d'ONT"),
    "adherent": fields.String(required=False, description="Adhérent"),
    "ref_acces": fields.String(required=False, description="Référence d'accès"),
    "vlan_bgp": fields.Integer(required=False, description="VLAN BGP utilisé pour le vDOM"),
    "mep": fields.Integer(required=False, description="Mep ID d'un service VPNL2")
})
service_model_rsp_addservice_json_post = ns_service.model("Body_add_id_service", { # Ajout d'un ID service
    "dsp": fields.String(required=True, description="DSP"),
    "fai": fields.String(required=True, description="Nom FAI"),
    "abonne": fields.String(required=True, description="Nom abonné"),
    "equipementier": fields.String(required=True, description="Equipementier"),
    "operateur_tiers": fields.String(required=True, description="Type ID technique"),
    "techno": fields.String(required=True, description="Commentaire ID technique"),
    "statut": fields.String(required=True, description="ID technique"),
    "profil": fields.String(required=True, description="Type ID technique"),
    "id_service_externe": fields.String(required=False, description="Commentaire ID technique"),
    "adherent": fields.String(required=False, description="ID technique"),
    "services_liees": fields.String(required=False, description="Type ID technique"),
    "gfu": fields.String(required=False, description="Commentaire ID technique"),
    "categorie_site": fields.String(required=False, description="Commentaire ID technique")
})
service_model_rsp_idtechnique_json_post = ns_service.model("Body_maj_rsp_by_idtechnique", { # Ajout d'un ID Tech
    "id_tech": fields.String(required=True, description="ID technique"),
    "type_id_tech": fields.String(required=True, description="Type ID technique"),
    "commentaire": fields.String(required=True, description="Commentaire ID technique")
})
service_model_rsp_addendpoint_json_post = ns_service.model("Body_maj_rsp_add_endpoint", { # Ajout d'un endpoint
    "equipement": fields.String(required=True, description="Nom d'équipement"),
    "port_equipement": fields.String(required=True, description="Port de l'équipement"),
    "acces_logique": fields.String(required=True, description="Accès logique"),
    "acces_physique": fields.String(required=True, description="Accès physique"),
    "debit_cir": fields.String(required=True, description="Débit CIR"),
    "acces_logique": fields.String(required=True, description="Débit BURST"),
})

# PARSER
parser = reqparse.RequestParser()

# ROUTES

# Service
@ns_service.route('/<string:id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@ns_service.doc(params={'id': 'ID de service'},
responses={
    200: 'Success',
    400: 'Bad Request',
    404: 'Not Found'
})
class Service(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oServices = Services()
        self.oServicesSocle = ServicesSocle()
    #

    def get(self, id):
        """Vérifier un service"""
        # Si ESNU-VOIP match
        if re.search('ESNU-VOIP-', id):
            return self.oServices.MesVOIP(id)
        # Sinon si ESNU-LWM match
        elif re.search('ESNU-LWM-', id):
            return self.oServices.MesLWM(id)
        # Sinon
        else:
            return get_equipment_ws(id)
        #
    #

    @ns_service.expect(service_model_json_post, validate=False)
    def post(self, id):
        """Créer un service"""
        # ESSONNE NUMERIQUE
        # Si ESNU-ACCES match
        if re.search('ESNU-ACCES-', id):
            return self.oServices.CreationAcces(id)
        # Sinon si ESNU- match
        elif re.search('ESNU-', id):
            data = request.get_json(silent=True) or {}
            return self.oServices.Creation(id, data.get("mep"))

        # SOCLE NATIONAL
        # Sinon si AXIO- match
        #elif re.search(r'AXIO\-(FTTH|FTTB)', id):
        #    data = request.get_json(silent=True) or {}
        #    return self.oServicesSocle.Creation(id, data.get("mep"))
        # Sinon si SIPI-009-TEL-209 match
        elif re.search(r'\w{3,4}\-\d{3}\-\w{3,5}\-\d{3}', id):
            data = request.get_json(silent=True) or {}
            return self.oServicesSocle.Creation(id, data)
        #
    #

    @ns_service.deprecated
    def put(self, id):
        """Modifier un service"""
        if re.search('ESNU-', id):
            return 0 # self.oServices.Modification(id, request.args.get('mep'))
        #
    #

    def delete(self, id):
        """Résilier un service"""
        if re.search('ESNU-', id):
            return self.oServices.Resiliation(id)
        #
    #
#

# Service - Airtable
@ns_service.route('/airtable/<string:id>', methods=['GET'])
@ns_service.doc(params={'id': 'ID de service'},
responses={
    200: 'Success',
    400: 'Bad Request',
    404: 'Not Found'
})
class ServiceAirtable(Resource):
    def get(self, id):
        """Sortir des informations de Airtable"""
        oServices = Services()
        data = oServices.read_from_airtable(id, 'viwS8W850FyIWCuvL')
        if isinstance(data, (str, bytes, bytearray)):
            contents = None
            try:
                contents = json.loads(data)
            except json.JSONDecodeError:
                return {'error': f'{str(data)}'}, 400
            #
        else:
            data = oServices.read_from_airtable(id)
            if isinstance(data, (str, bytes, bytearray)):
                contents = None
                try:
                    contents = json.loads(data)
                except json.JSONDecodeError:
                    return {'error': f'{str(data)}'}, 400
                #
            else:
                return {'error': f'Le service est inexistant'}, 404
            #
        #
        return contents
    #
#

# Service - RSP - add_service
@ns_service.route('/rsp/add-service/<string:id>', methods=['POST'])
@ns_service.doc(params={'id': 'ID de service'},
responses={
    200: 'Success',
    400: 'Bad Request',
    404: 'Not Found'
})
class ServiceRSPaddservice(Resource):
    @ns_service.expect(service_model_rsp_addservice_json_post, validate=True)
    def post(self, id):
        """Ajouter un service dans RSP"""
        referer = 'https://ws-ords.m2m.axione.fr'
        data = request.get_json(silent=True) or {}

        rspData = {
            "p_id_service": id,
            "p_dsp": data.dsp,
            "p_fai": data.fai,
            "p_ABONNE": data.abonne,
            "p_equipementier": data.equipmentier, 
            "p_operateur_tiers": data.operateur_tiers,
            "p_technologie": data.techno,
            "p_statut": data.statut,
            "p_PROFIL": data.profil,
            "p_ID_SERVICE_EXTERNE": data.id_service_externe,
            "p_ADHERENT": data.adherent,
            "p_SERVICES_LIES": data.services_liees,
            "p_GFU": data.gfu,
            "p_CATEGORIE_SITE": data.categorie_site
        }
        try:
            response = requests.post('https://refsp.int.axione.fr/ordscomxdsl/pwksrefpro/rsp_add_id_service', data=rspData, headers={'Referer': referer}, verify=False)
            return f'Ajout OK {id} dans RSP'
        except requests.exceptions.RequestException as e:
            return f'Ajout KO {id} dans RSP'
        #
    #
#

# Service - RSP - id_technique
@ns_service.route('/rsp/id-technique/<string:id>', methods=['POST'])
@ns_service.doc(params={'id': 'ID de service'},
responses={
    200: 'Success',
    400: 'Bad Request',
    404: 'Not Found'
})
class ServiceRSPidtech(Resource):
    @ns_service.expect(service_model_rsp_idtechnique_json_post, validate=True)
    def post(self, id):
        """Ajouter un ID technique dans RSP"""
        referer = 'https://ws-ords.m2m.axione.fr'
        data = request.get_json(silent=True) or {}

        rspData = {
            'p_id_service': id,
            'p_idtechnique': data.id_tech,
            'p_type_idtechnique': data.type_id_tech,
            'p_commentaire_idtechnique': data.commentaire,
        }
        try:
            response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
            return f'Ajout OK de l\'id_technique {data.id_tech} {data.type_id_tech} {data.commentaire} dans RSP {id}'
        except requests.exceptions.RequestException as e:
            return f'Ajout KO de l\'id_technique {data.id_tech} {data.type_id_tech} {data.commentaire} dans RSP {id}'
        #
    #
#

# Service - RSP - id_technique
@ns_service.route('/rsp/add-endpoint/<string:id>', methods=['POST'])
@ns_service.doc(params={'id': 'ID de service'},
responses={
    200: 'Success',
    400: 'Bad Request',
    404: 'Not Found'
})
class ServiceRSPaddendpoint(Resource):
    @ns_service.expect(service_model_rsp_addendpoint_json_post, validate=True)
    def post(self, id):
        """Ajouter un équipement dans RSP"""
        referer = 'https://ws-ords.m2m.axione.fr'
        data = request.get_json(silent=True) or {}

        rspData = {
            "p_id_service": id,
            "p_equipement_port": data.equipement,
            "p_port": data.port_equipement,
            "p_acces_logique": data.acces_logique,
            "p_acces_physique": data.acces_physique,
            "p_debit_cir": data.debit_cir,
            "p_debit_burst": data.debit_burst
        }
        try:
            response = requests.post('https://ws-ords.m2m.axione.fr/ordscomxdsl/pwksrefpro/maj_rsp', data=rspData, headers={'Referer': referer}, verify=False)
            return f'Ajout OK de l\'endpoint {data.equipement} {data.port_equipement} dans RSP {id}'
        except requests.exceptions.RequestException as e:
            return f'Ajout KO de l\'endpoint {data.equipement} {data.port_equipement} dans RSP {id}'
        #
    #
#
    
# Equipement
@ns_equipment.route('/<string:name>', methods=['GET'])
class Equipment(Resource):
    @ns_equipment.doc(params={
        'name': "Nom de l'équipement ou ID de service",
        'port': "Numéro du port (optionnel)",
        'breakout': "Breakout du port (optionnel)"
    })
    def is_service_id(self, name):
        if not name or '-' not in name:
            return False
        
        # Récupérer la partie avant le premier tiret
        prefix = name.split('-')[0]
        
        # Vérifier si c'est 4 lettres (ID de service)
        if len(prefix) == 4 and prefix.isalpha():
            return True
        
        return False

    def get(self, name):
        """Vérifier un équipement"""
        # Vérifier d'abord si c'est un ID de service
        if self.is_service_id(name):
            # C'est un ID de service, utiliser ServiceEquipmentFetcher
            try:
                service_fetcher = ServiceEquipmentFetcher()
                result = service_fetcher.get_equipment_by_service_id(name)
                service_fetcher.close()
                return result
            except Exception as e:
                return {"error": f"Erreur lors de la récupération du service {name}: {str(e)}"}, 500
        
        # Sinon, traiter comme un nom d'équipement (logique existante)
        if '_' in name:
            name_parts = name.split('_', 1)
            equipment_name = name_parts[0]
            port_from_name = name_parts[1]
            port = request.args.get('port') or port_from_name
        else:
            equipment_name = name
            port = request.args.get('port')
        
        slot = request.args.get('breakout')

        # Sinon si wdm- match
        if re.match('wdm-', equipment_name):
            if IsNokia(equipment_name) == True:
                result = ScriptNokiaPrincipal(equipment_name)
            elif IsEkinops(equipment_name) == True:
                result = ScriptEkinopsPrincipal(equipment_name)
            else:
                equipment = NetworkEquipment(equipment_name, ip=port, slot=slot)
                result = equipment.get_equipment_info()
        else:
            equipment = NetworkEquipment(equipment_name, ip=port, slot=slot)
            result = equipment.get_equipment_info()
        
        if port and not re.match('wdm-', equipment_name):
            equipment = NetworkEquipment(equipment_name, ip=port, slot=slot)
            filtered_ports = equipment.get_port_info(ip=port, slot=slot)
            if not filtered_ports:
                return {"error": f"Port {port}{f'/{slot}' if slot else ''} non trouvé sur l'équipement {equipment_name}"}, 404
            
            filtered_result = {
                'equipment_info': result['equipment_info'],
                'ports': filtered_ports
            }
            return filtered_result
        
        return result
    #
#

# Détail d'équipement WDM
@ns_equipment.route('/<string:name>/details', methods=['GET'])
class EquipmentDetail(Resource):
    @ns_equipment.doc(params={'name': "nom de l'equipement", 'card_name': 'Nom de la carte', 'slot': 'Slot de la carte'})
    def get(self, name):
        """Vérifier le détail d'un équipement"""
        card_name = request.args.get('card_name')
        slot = request.args.get('slot')
        if card_name and slot:
            if "EMUX" in card_name:
                result = ScriptEmux(name, card_name, slot)
            elif "FRS02" in card_name:
                result = Script200FRS02(name, card_name, slot)
            elif "OABP-HCS" in card_name:
                result = ScriptOabphcs(name, card_name, slot)
            elif "OTDR" in card_name:
                result = ScriptOTDR(name, card_name, slot)
            elif "C1008MPLH" in card_name:
                result = ScriptC1008MPLH(name, card_name, slot)
            elif "C1008GE" in card_name:
                result = ScriptC1008GE(name, card_name, slot)
            elif "PM_O6006MP" in card_name:
                result = ScriptPM06(name, card_name, slot)
            elif "OAIL-HCS" in card_name:
                result = ScriptOAILHCS(name, card_name, slot)
            elif "1001RR" in card_name:
                result = Script1001RR(name, card_name, slot)
            elif "C1001HC" in card_name:
                result = ScriptC1001HC(name, card_name, slot)
            elif "PM404" in card_name:
                result = ScriptPM404(name, card_name, slot)
            elif any(x in card_name for x in ['OAB-E', 'OABP-E', 'OABPLC']):
                result = ScriptOAB(name, card_name, slot)
            elif "ROADM-FLEX" in card_name:
                result = ScriptROADM(name, card_name, slot)
            elif "OPM8" in card_name:
                result = ScriptOPM8(name, card_name, slot)
            elif any(x in card_name for x in ["11dPM12", "11QPA4B", "16P200", "130SCX", "8p20", "S4X400H", "S5AD400H", "S6AD600H", "S13X100R"]):
                result= ScriptTransponders(name, card_name, slot)
            elif "AHPLG" in card_name or "AHPHG" in card_name or "AM2032A" in card_name or "AM2625A" in card_name:
                result = ScriptAmplifiersGeneral(name, card_name, slot)
            elif "ASG" in card_name or "ASGLP " in card_name or "ASWG" in card_name:
                result = ScriptAmplifiersForAs(name, card_name, slot)
            elif "ROADM9R" in card_name or "IRDM20" in card_name :
                result = ScriptWavelengthRouter(name, card_name, slot)
            elif "RA2P" in card_name:
                result = ScriptRA2P(name, card_name, slot)
            elif "AAR-8A" in card_name:
                result = ScriptAAR8A(name, card_name, slot)
            elif "EC" in card_name:
                result = ScriptControllerCards(name, card_name, slot)
            elif "MCS8-16" in card_name or "USRPNL" in card_name or "SHFPNL" in card_name or "PF" in card_name:
                result = ScriptAutre(name, card_name, slot)
        else:
            if IsNokia(name):
                result = ScriptNokiaSecond(name)
            elif IsEkinops(name):
                result = ScriptEkinopsSecond(name)
        return result
    #
#

# Spectrum
@ns_tool.route('/spectrum/<string:name>&<string:community>', methods=['GET'])
class Spectrum(Resource):
    @ns_tool.doc(params={
        'name': "Nom de l'equipement",
        'community': "Communauté SNMP"
    })
    def get(self, name, community):
        result = DeviceInSpectrum(name, community)
        return result
    #
#

# Spectrum
@ns_tool.route('/spectrum/<string:ip>&<string:name>&<string:community>', methods=['POST'])
class Spectrum(Resource):
    @ns_tool.doc(params={
        'ip': "IP de l'equipement",
        'name': "Nom de l'equipement",
        'community': "Communauté SNMP"
    })
    def get(self, ip, name, community):
        result = AddInSpectrum(ip, name, community)
        return result
    #
#

# Cacti
@ns_tool.route('/cacti/<string:name>&<string:ip>&<string:type>', methods=['GET'])
class Cacti(Resource):
    @ns_tool.doc(params={
        'name': "Nom de l'equipement",
        'ip': "IP de l'équipement",
        'type': "Type de l'équipement"
    })
    def get(self, name, ip, type):
        result = DeviceInCacti(name, ip, type)
        return result
    #
#

# Netbox
@ns_tool.route('/netbox/<string:name>&<string:ip>&<string:type>', methods=['POST'])
class Netbox(Resource):
    @ns_tool.doc(params={
        'name': "Nom de l'equipement",
        'ip': "IP de l'équipement",
        'type': "Type de l'équipement"
    })
    def post(self, name, ip, type):
        result = DeviceInNetbox(name, ip, type)
        return result
    #
#

# Commandes
@ns_command.route('/snmp/<string:command>', methods=['GET'])
class Command(Resource):
    @ns_command.doc(params={'snmp': 'Commande SNMP'})
    def get(self, command):
        try:
            # Préparer et exécuter la commande en toute sécurité
            # On utilise shlex.split pour sécuriser l'exécution des arguments
            command_list = shlex.split(command)  # Sépare la commande en liste
            result = subprocess.run(command_list, capture_output=True, text=True)

            # Vérifier si la commande a été exécutée correctement
            if result.returncode == 0:
                output = result.stdout
                return jsonify({'status': 'success', 'output': output})
            else:
                error_message = result.stderr
                return jsonify({'status': 'error', 'error': error_message})
            #
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
        #
#

# Logs
@ns_logs.route('/<string:id>', methods=['GET'])
@ns_logs.doc(params={'id': 'ID de service'})
class LogsEssonne(Resource):
    def get(self, id):
        """Voir les logs d'un service Essonne Numérique"""
        result = GetLogs(id)
        return result
    #
#

# Logs - Name
@ns_logs.route('/search/<int:session>', methods=['GET'])
@ns_logs.doc(params={'session': 'Numéro de session'})
class LogsEssonneSession(Resource):
    def get(self, session):
        """Voir les logs via session d'un service Essonne Numérique"""
        result = GetLogs(session)
        return result
    #
#

# AFTER
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate')
    
    content_type = response.headers.get('Content-Type', '')
    if content_type.startswith('text/html') or content_type.startswith('application/json'):
        if 'charset=' not in content_type:
            response.headers['Content-Type'] = content_type + '; charset=utf-8'
        else:
            response.headers['Content-Type'] = re.sub(r'charset=[^;]+', 'charset=utf-8', content_type)
        #
    #
    return response
#

# PROGRAMME

if __name__ == '__main__':
    app.run(debug=True)

api.add_namespace(ns_service)
api.add_namespace(ns_equipment)
api.add_namespace(ns_tool)
api.add_namespace(ns_command)
api.add_namespace(ns_logs)
