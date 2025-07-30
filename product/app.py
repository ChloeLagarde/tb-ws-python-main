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
from scripts.OLT.ServiceEssonne import *
from scripts.PBB.ClassPBBWeb import *
from scripts.PBB.Service import *


# FLASK
app = Flask(__name__)
api = Api(app, version='1.5', title='WS TB Python')

# NAMESPACE
ns_service = Namespace('service', description='Endpoints pour la gestion d\'un service')
ns_equipment = Namespace('equipment', description='Endpoints pour la gestion des équipements')
ns_tool = Namespace('tool', description='Endpoints pour la gestion avec les outils')
ns_command = Namespace('command', description='Endpoints pour l\'exécution des commandes')

# MODELES
service_model = ns_service.model('Service', { 'id': fields.String(required=True, description='ID de service') })
equipments_model = ns_equipment.model('Equipment', { 'name': fields.String(required=True, description='Nom de l\'equipement') })

# PARSER
parser = reqparse.RequestParser()

# ROUTES

# ID service
@ns_service.route('/<string:id>', methods=['GET', 'POST'])
class ServiceGET(Resource):
    @ns_service.doc(params={
        'id': 'ID de service',
        'maj_rsp': 'Mise à jour de RSP',
        'mac': 'Adresse MAC d\'un service VPNIOT',
        'subnet': 'Subnet IP d\'un service VPNSUR',
        'mep': 'Mep ID d\'un service VPNL2',
    })
    def get(self, id):
        # Si ESNU-ACCES match
        if re.match('ESNU-ACCES-', id):
            return create_acces_essonne_numerique(id)
        # Sinon si ESNU- match
        elif re.match('ESNU-', id):
            return create_service_essonne_numerique(id, request.args.get('rsp'), request.args.get('mac'), request.args.get('subnet'), request.args.get('mep'))
        # Sinon
        else:
            return get_equipment_ws(id)
        #
    #
    def post(self, id):
        # Si ESNU-ACCES match
        if re.match('ESNU-VOIP-', id):
            return check_service_voip_commeett(id)
        #
    #
#
    
# Equipement
@ns_equipment.route('/<path:name>', methods=['GET'])
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

        if re.match('olt-', equipment_name):
            result = OLT(equipment_name)
        # Sinon si wdm- match
        elif re.match('wdm-', equipment_name):
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
        
        if port and not re.match('olt-|wdm-', equipment_name):
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
@ns_tool.route('/netbox/<string:name>&<string:ip>&<string:type>', methods=['PUT'])
class Netbox(Resource):
    @ns_tool.doc(params={
        'name': "Nom de l'equipement",
        'ip': "IP de l'équipement",
        'type': "Type de l'équipement"
    })
    def put(self, name, ip, type):
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

# AFTER
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate')
    return response

# PROGRAMME

if __name__ == '__main__':
    app.run(debug=True)

api.add_namespace(ns_service)
api.add_namespace(ns_equipment)
api.add_namespace(ns_tool)
api.add_namespace(ns_command)
