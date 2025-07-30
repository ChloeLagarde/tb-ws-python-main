import re
import subprocess
from scripts.Test_SWA import test_swa
from scripts.SnmpRequests import *

def net_snmp(host, oid):
    return_value = None
    command = ['snmpget', '-v', '2c', '-c', 'cpdea', host, oid]
    
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        lines = output.strip().split('\n')
        if len(lines) > 0:
            return_value = lines[-1].split(' ')[-1]
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande SNMP pour l'OID {oid} : {e.output}")
    
    return output

def extract_integer(snmp_response):
    """Extrait un entier à partir d'une réponse SNMP sous forme de chaîne."""
    match = re.search(r'INTEGER:\s*(-?\d+)', snmp_response)
    if match:
        return match.group(1)  # Retourne uniquement le nombre sous forme de chaîne
    return None

def extract_counter32(result):
    match = re.search(r"Counter32:\s*(\d+)",result)
    if match:
        valeur = match.group(1)
        return valeur
    else:
        return result

speed_duplex_mapping2 = {
            "1" : "10MB-full",
            "2" : "10MB-half",
            "3" : "100MB-full",
            "4" : "100MB-half",
            "5" : "1000MB-full",
            "6" : "1000MB-half",
            "7" : "auto",
            "8" : "auto-10MB-full",
            "9" : "auto-10MB-half",
            "10" : "auto-100MB-full",
            "11" : "auto-100MB-half",
            "12" : "auto-1000MB-full",
            "13" : "auto-1000MB-half",
            "14" : "negotiating",
            "15" : "auto-1000MB-full-master",
            "16" : "auto-1000MB-full-slave",
            "17" : "none",
            "18" : "auto-1000MB-full-master-preferred",
            "19" : "auto-1000MB-full-slave-oreferred",
            "20" : "10G-full",
            "21" : "auto-detect"
        } 
speed_duplex_mapping1 = {
            "1" : "speed auto duplex auto",
            "2" : "speed 10 duplex half",
            "3" : "speed 10 duplex full",
            "4" : "speed 100 duplex half",
            "5" : "speed 100 duplex full",
            "6" : "speed 1000 duplex half",
            "7" : "speed 1000 duplex full",
            "11" : "speed auto duplex half",
            "12" : "speed auto duplex full",
            "13" : "speed 10 duplex auto",
            "14" : "speed 100 duplex auto",
            "16" : "speed 1000 duplex auto"
        }
status_speed_duplex_mapping = {
                    "1" : "unknown",
                    "2" : "half-10",
                    "3" : "full-10",
                    "4" : "half-100",
                    "5" : "full-100",
                    "6" : "half-1000",
                    "7" : "full-1000"
                }

def snmp_telco_port(equipment_type, equipment_version, equipment_port, host, cpdea , ip):

    ip, timestamp = ip.split(maxsplit=1)
    
    # Variables
    adminstatus = "Null"
    operstatus = "Null"
    status = "Null"
    fin_vlan = "Null"
    fin_port = "Null"
    portavecpoint = "Null"
    portsanspoint = "Null"
    mtu = "Null"
    in_octets = "Null"
    in_discards = "Null"
    in_errors = "Null"
    out_octets = "Null"
    out_discards = "Null"
    out_errors = "Null"
    speed_duplex = "Null"
    mac_97_bas = "Null"
    mac_97_nte = "Null"
    name = "Null"
    default_vlan = "Null"
    mac_vlan = []
    mac_sdp = []
    interface_vlan = "Null"
    mac_data = "Null"
    mac_et_interface = "Null"
    status_speed_duplex = "Null"
    oid = "Null"
    port1 = "Null"
    port2 = "Null"
    port3 = "Null"
    port4 = ""
    type_media = "Null"
    puissance_optique_tx = "Null"
    puissance_optique_rx = "Null"
    puissance_optique_tx_access = "Null"
    puissance_optique_rx_access = "Null"
    equipementier_sfp = "Null"
    type_connecteur_sfp = "Null"
    laser_wave_length = "Null"
    link_length = "Null"
    link_length_access = "Null"
    evpl = "Null"
    port_numerique = "Null"
    snmp_command = "Null"
    port_huawei_switch = "Null"
    port_network2 = None

    port = str(equipment_port).split('/')

    # If port is like 1/1/1
    if re.search(r'[0-9]+/[0-9]+/[0-9]+', equipment_port):
        port1 = re.findall(r'[0-9]+', port[0])[0]
        port2 = int(port[1])
        port3 = int(port[2])
        fin_vlan = str(port3).zfill(2)
        fin_port = port3
        portavecpoint = str(port1) + "." + str(port2) + "." + str(port3)
        portsanspoint = str(port1) + str(port2) + str(port3)
        if port3 > 9:
            portsanspoint = str(port1) + str(port3)
        if port1 == '2' and equipment_type == 'CISCO':
            portsanspoint = "6" + str(port2) + str(port3)
            if port3 > 9:
                portsanspoint = "6" + str(port3)

    # If port is like access/1/1/1/1
    elif re.search(r'access-\d+-\d+-\d+-\d+', equipment_port):
        port1 = int(re.search(r'access-(\d+)-(\d+)-(\d+)-(\d+)', equipment_port).group(1))
        port2 = int(re.search(r'access-(\d+)-(\d+)-(\d+)-(\d+)', equipment_port).group(2))
        port3 = int(re.search(r'access-(\d+)-(\d+)-(\d+)-(\d+)', equipment_port).group(3))
        port4 = int(re.search(r'access-(\d+)-(\d+)-(\d+)-(\d+)', equipment_port).group(4))
        fin_port = port4
        portavecpoint = str(port1) + "." + str(port2) + "." + str(port3) + "." + str(port4)

    # If port is like FastEthernet0/1
    elif re.search(r'FastEthernet\d+/\d+', equipment_port):
        port1 = re.search(r'\d+', port[0]).group()
        port2 = int(port[1])

        portsanspoint = "00" + str(port2)
        if port[1] > 9:
            portsanspoint = "0" + str(port2)

    # If port is like GigabitEthernet0/1
    elif re.search(r'GigabitEthernet[0-9]+/[0-9]+', equipment_port):
        port1 = re.findall(r'[0-9]+', port[0])[0]
        port2 = int(port[1])
        port3 = int(port[2])
        if port[1] > 9:
            portsanspoint = "1", str(port2)
        if port[1] < 10:
            portsanspoint = "10", str(port2)

    tested_swa = test_swa(port1, port2, port3, port4, host)

    # Once port info is extracted, we can send SNMP request
    # snmp commands for T5C type
    if equipment_type == "T5C":
        # Admin status
        result = snmp_request(host, ".1.3.6.1.2.1.2.2.1.7.11" + fin_vlan)
        result = re.search(r'\((\d+)\)', str(result)).group(1)
        if '1' in result:
            adminstatus = "up"
        elif '2' in result:
            adminstatus = "down"
        else:
            adminstatus = "no such instance"

        # Oper status
        result = snmp_request(host, ".1.3.6.1.2.1.2.2.1.8.11" + fin_vlan)
        result = re.search(r'\((\d+)\)', str(result)).group(1)
        if '1' in result:
            operstatus = "up"
        elif '2' in result:
            operstatus = "down"
        else:
            operstatus = "no such instance"

        status = adminstatus + "-" + operstatus

        # In/Out octets, discards, errors
        if tested_swa > 1 and operstatus == "UP":

            in_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.10.1" + str(port2) + str(fin_vlan))
            in_octets = re.search(r': (\d+)', str(in_octets)).group(1)

            in_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.13.1" + str(port2) + str(fin_vlan))
            in_discards = re.search(r': (\d+)', str(in_discards)).group(1)

            in_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.14.1" + str(port2) + str(fin_vlan))
            in_errors = re.search(r': (\d+)', str(in_errors)).group(1)

            out_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.16.1" + str(port2) + str(fin_vlan))
            out_octets = re.search(r': (\d+)', str(out_octets)).group(1)

            out_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.19.1" + str(port2) + str(fin_vlan))
            out_discards = re.search(r': (\d+)', str(out_discards)).group(1)

            out_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.20.1" + str(port2) + str(fin_vlan))
            out_errors = re.search(r': (\d+)', str(out_errors)).group(1)

            # MAC address and VLAN interface
            if port != ['1', '1', '1'] and tested_swa > 1:
                result = snmp_request(host, "1.3.6.1.2.1.17.7.1.2.2.1.2" + str(tested_swa))
                for line in result.splitlines():
                    interface_vlan = int(re.search(r': (\d+)?', str(line)).group(1))
                    if interface_vlan == 1:
                        interface_vlan = "1/1/1"
                    elif interface_vlan == 3:
                        interface_vlan = "1/1/3"
                    elif interface_vlan == port3:
                        interface_vlan = str(equipment_port)

                    mac_data = re.search(r'(\d+.){5}(\d+ )', str(line)).group()
                    mac_data = mac_data.replace(" ", "")
                    mac_data = mac_data.split(".")
                    for i in range(0, 6):
                        mac_data[i] = hex(int(mac_data[i]))
                        mac_data[i] = mac_data[i].replace("0x", "")
                        # list to string
                        mac_data[i] = str(mac_data[i])

                    mac_data = ":".join(mac_data)
                    mac_et_interface = mac_data + "_" + str(interface_vlan)
                    if interface_vlan == str(port1) + "/" + str(port2) + "/" + str(port3):
                        if mac_et_interface not in mac_vlan:
                            mac_vlan.append(mac_et_interface)

            result = ""

        # Speed Duplex
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.2.2.2.1.7." + portavecpoint)
        result = re.search(r': (\d+)', str(result)).group(1)
        speed_duplex  = speed_duplex_mapping1.get(result, "type non trouvee")

        # Status speed duplex
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.3.1.1.1.7." + portavecpoint)
        result = re.search(r': (\d+)', str(result)).group(1)
        status_speed_duplex = status_speed_duplex_mapping.get(result,"non trouver")

        # Name
        name = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.2.2.2.1.4." + portavecpoint)
        if re.search(r': \"(.*)\"', str(name)):
            name = re.search(r': \"(.*)\"', str(name)).group(1)
        else:
            name = "not found"

        # TX optical power
        puissance_optique_tx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.3." + portavecpoint + ".1")
        if re.search(r': (\D?\d+)', str(puissance_optique_tx)):
            puissance_optique_tx = re.search(r': (\D?\d+)', str(puissance_optique_tx)).group(1)
        else:
            puissance_optique_tx = "not found"

        # RX optical power
        puissance_optique_rx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.4." + portavecpoint + ".1")
        if re.search(r': (\D?\d+)', str(puissance_optique_rx)):
            puissance_optique_rx = re.search(r': (\D?\d+)', str(puissance_optique_rx)).group(1)
        else:
            puissance_optique_rx = "not found"

    # snmp commands for T380 type
    elif equipment_type == "T380":
        port3 = port3 + 2
        # Admin status
        result = snmp_request(host, ".1.3.6.1.2.1.2.2.1.7.12" + fin_vlan)
        result = re.search(r'\((\d+)\)', str(result)).group(1)
        if '1' in result:
            adminstatus = "up"
        elif '2' in result:
               adminstatus = "down"
        else:
            adminstatus = "not found"
        result = ""

        # Oper status
        result = snmp_request(host, ".1.3.6.1.2.1.2.2.1.8.12" + fin_vlan)
        result = re.search(r'\((\d+)\)', str(result)).group(1)
        if '1' in result:
            operstatus = "up"
        elif '2' in result:
            operstatus = "down"
        else:
            operstatus = "not found"
        result = ""

        status = adminstatus + "-" + operstatus

        # In/Out octets, discards, errors
        if tested_swa > 1 and operstatus == "UP":

            in_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.10.1" + port2 + fin_vlan)
            in_octets = re.search(r': (\d+)', str(in_octets)).group(1)

            in_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.13.1" + port2 + fin_vlan)
            in_discards = re.search(r': (\d+)', str(in_discards)).group(1)

            in_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.14.1" + port2 + fin_vlan)
            in_errors = re.search(r': (\d+)', str(in_errors)).group(1)

            out_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.16.1" + port2 + fin_vlan)
            out_octets = re.search(r': (\d+)', str(out_octets)).group(1)

            out_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.19.1" + port2 + fin_vlan)
            out_discards = re.search(r': (\d+)', str(out_discards)).group(1)

            out_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.20.1" + port2 + fin_vlan)
            out_errors = re.search(r': (\d+)', str(out_errors)).group(1)

            # MAC address and VLAN interface
            if port != ['1', '1', '1'] and tested_swa > 1:
                result = snmp_request(host, "1.3.6.1.2.1.17.4.3.1.2")
                for line in result.splitlines():
                    interface_vlan = int(re.search(r'INTEGER: (\d+)', str(line)).group(1))
                    if interface_vlan == port3:
                        interface_vlan = str(equipment_port)

                    mac_data = re.search(r'(\d+.){5}(\d+ )', str(line)).group()
                    mac_data = mac_data.replace(" ", "")
                    mac_data = mac_data.split(".")
                    for i in range(0, 6):
                        mac_data[i] = hex(int(mac_data[i]))
                        mac_data[i] = mac_data[i].replace("0x", "")
                        # list to string
                        mac_data[i] = str(mac_data[i])

                    mac_data = ":".join(mac_data)
                    mac_et_interface = mac_data + "_" + str(interface_vlan)
                    if interface_vlan == str(port1) + "/" + str(port2) + "/" + str(port3):
                        if mac_et_interface not in mac_vlan:
                            mac_vlan.append(mac_et_interface)

            result = ""

        # Speed duplex
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.2.2.2.1.7." + portavecpoint)
        result = re.search(r': (\d+)', str(result)).group(1)
        speed_duplex  = speed_duplex_mapping1.get(result, "type non trouvee")


        # Status speed duplex
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.3.1.1.1.7." + portavecpoint)
        result = re.search(r': (\d+)', str(result)).group(1)
        status_speed_duplex = status_speed_duplex_mapping.get(result,"non trouver")
        # Name
        name = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.2.2.2.1.4." + portavecpoint)
        if re.search(r'STRING: "(.*)"', str(name)):
            name = re.search(r'STRING: "(.*)"', str(name)).group(1).replace("\\", "").replace('"', "")
        else:
            name = "not found"

        # TX optical power
        puissance_optique_tx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.3." + portavecpoint + ".1")
        if "No Such Instance" in str(puissance_optique_tx):
            puissance_optique_tx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.3." + portavecpoint)
            if re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_tx)):
                puissance_optique_tx = re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_tx)).group(1)
            else:
                puissance_optique_tx = "noSuchInstance"
        elif re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_tx)):
            puissance_optique_tx = re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_tx)).group(1)


        # RX optical power
        puissance_optique_rx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.4." + portavecpoint + ".1")
        if "No Such Instance" in str(puissance_optique_rx):
            puissance_optique_rx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.4." + portavecpoint)
            if re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_rx)):
                puissance_optique_rx = re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_rx)).group(1)
            else:
                puissance_optique_rx = "noSuchInstance"
        elif re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_rx)):
            puissance_optique_rx = re.search(r'INTEGER: (\D?\d+)', str(puissance_optique_rx)).group(1)

        # Equipment supplier
        equipementier_sfp = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.5.1.2." + portavecpoint + ".1")
        if re.search(r': \"(.*)\"', str(equipementier_sfp)):
            equipementier_sfp = re.search(r': \"(.*)\"', str(equipementier_sfp)).group(1)
        else:
            equipementier_sfp = "No equipment supplier found"


        # Link Length
        link_length = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.5.1.5." + portavecpoint + ".1")
        if "0x0428" in str(link_length):
            link_length = "4"
        elif "0x0f96" in str(link_length):
            link_length = "15"
        elif "0x14c8" in str(link_length):
            link_length = "20"
        elif "0x1eff" in str(link_length):
            link_length = "30"
        elif "0x28ff" in str(link_length):
            link_length = "40"
        elif re.search(r'd', str(link_length)):
            link_length = "10"
        else:
            link_length = "No link length found"

    # snmp commands for T280 type
    elif equipment_type == "T280":
        # admin status
        result = snmp_request(host, ".1.3.6.1.2.1.2.2.1.7.1" + str(port2) + fin_vlan)
        result = re.search(r'\((\d+)\)', str(result)).group(1)
        if '1' in result:
            adminstatus = "up"
        elif '2' in result:
               adminstatus = "down"
        else:
            adminstatus = "not found"

        # oper status
        result = snmp_request(host, ".1.3.6.1.2.1.2.2.1.8.1" + str(port2) + fin_vlan)
        result = re.search(r'\((\d+)\)', str(result)).group(1)
        if '1' in result:
            operstatus = "up"
        elif '2' in result:
            operstatus = "down"
        else:
            operstatus = "not found"

        status = adminstatus + "_" + operstatus

        # mtu
        mtu = snmp_request(host, ".1.3.6.1.2.1.2.2.1.4.1" + str(port2) + fin_vlan)
        if re.search(r': (\d+)', str(mtu)):
            mtu = re.search(r': (\d+)', str(mtu)).group(1)
        else:
            mtu = "not found"

        # In/Out octets, in/out errors, in/out discards
        if operstatus == "UP":
            in_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.10.1" + str(port2) + fin_vlan)
            in_octets = re.search(r': (\d+)', str(in_octets)).group(1)

            in_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.13.1" + str(port2) + fin_vlan)
            in_discards = re.search(r': (\d+)', str(in_discards)).group(1)

            in_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.14.1" + str(port2) + fin_vlan)
            in_errors = re.search(r': (\d+)', str(in_errors)).group(1)

            out_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.16.1" + str(port2) + fin_vlan)
            out_octets = re.search(r': (\d+)', str(out_octets)).group(1)

            out_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.19.1" + str(port2) + fin_vlan)
            out_discards = re.search(r': (\d+)', str(out_discards)).group(1)

            out_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.20.1" + str(port2) + fin_vlan)
            out_errors = re.search(r': (\d+)', str(out_errors)).group(1)

        # Speed duplex
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.2.2.2.1.7." + portavecpoint)
        result = re.search(r': (\d+)', str(result)).group(1)
        speed_duplex  = speed_duplex_mapping1.get(result, "type non trouvee")

        # Status Speed duplex
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.3.1.1.1.7." + portavecpoint)
        result = re.search(r': (\d+)', str(result)).group(1)
        status_speed_duplex = status_speed_duplex_mapping.get(result,"non trouver")
        # Mac 97 bas
        if port == ['1', '1', '1']:
            result = snmp_request(host, "1.3.6.1.2.1.17.7.1.2.2.1.2.97")
            for line in result.splitlines():
                mac_97_bas = re.search(r'(\d+)\.(144)\.(\d+)\.(\d+)\.(\d+)\.(\d+)\s+=\s+INTEGER:\s+\d+',
                                       str(line)).group()
                mac_97_bas = mac_97_bas.replace(" ", "")
                mac_97_bas = mac_97_bas.split(".")
                for i in range(0, 6):
                    mac_97_bas[i] = hex(int(mac_97_bas[i]))
                    mac_97_bas[i] = mac_97_bas[i].replace("0x", "")
                    # list to string
                    mac_97_bas[i] = str(mac_97_bas[i])
                mac_97_bas = ":".join(mac_97_bas)

        # Name
        name = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.2.2.2.1.4." + portavecpoint)
        if re.search(r'STRING: "(.*)"', str(name)):
            name = re.search(r'STRING: "(.*)"', str(name)).group(1).replace("\\", "").replace('"', "")
        else:
            name = "not found"

        # Default vlan
        default_vlan = snmp_request(host, ".1.3.6.1.4.1.738.1.5.100.2.2.2.1.11." + portavecpoint)
        if re.search(r': (\d+)', str(default_vlan)):
            default_vlan = re.search(r': (\d+)', str(default_vlan)).group(1)
        else:
            default_vlan = "not found"

        # MAC address and vlan interface
        if port != ['1', '1', '1'] and re.search(r'\d{4}', str(default_vlan)) and operstatus == "UP":
            result = snmp_request(host, "1.3.6.1.2.1.17.7.1.2.2.1.2" + default_vlan)
            i = "0"
            for line in result.splitlines():
                if re.search(r'(\d+.){5}(\d+ )\D+(\d+)\)?', str(line)):
                    interface_vlan = int(re.search(r'(\d+.){5}(\d+ )\D+(\d+)\)?', str(line)).group(3))
                    if interface_vlan == 1:
                        interface_vlan = "1/1/1"
                    elif interface_vlan == 2:
                        interface_vlan = "1/2/1"
                    elif interface_vlan == 3:
                        interface_vlan = "1/2/2"
                    elif interface_vlan == 4:
                        interface_vlan = "1/3/1"
                    mac_data = re.search(r'(\d+.){5}(\d+ )', str(line)).group()
                    mac_data = mac_data.replace(" ", "")
                    mac_data = mac_data.split(".")
                    for i in range(0, 6):
                        mac_data[i] = hex(int(mac_data[i]))
                        mac_data[i] = mac_data[i].replace("0x", "")
                    # list to string
                    mac_data[i] = str(mac_data[i])

                    mac_data = ":".join(mac_data)
                    mac_et_interface = mac_data + "_" + str(interface_vlan)
                    if interface_vlan == str(port1) + "/" + str(port2) + "/" + str(port3):
                        if mac_et_interface not in mac_vlan:
                            mac_vlan.append(mac_et_interface)

            result = ""

        # TX optical power
        puissance_optique_tx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.3.1.1.1.1")
        if re.search(r': (\D?\d+)', str(puissance_optique_tx)):
            puissance_optique_tx = re.search(r': (\D?\d+)', str(puissance_optique_tx)).group(1)
        else:
            puissance_optique_tx = "not found"

        # RX optical power
        puissance_optique_rx = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.4.1.1.1.1")
        if re.search(r': (\D?\d+)', str(puissance_optique_rx)):
            puissance_optique_rx = re.search(r': (\D?\d+)', str(puissance_optique_rx)).group(1)
        else:
            puissance_optique_rx = "not found"

        # TX optical power access
        puissance_optique_tx_access = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.3." + portavecpoint + ".1")
        if re.search(r': (\D?\d+)', str(puissance_optique_tx_access)):
            puissance_optique_tx_access = re.search(r': (\D?\d+)', str(puissance_optique_tx_access)).group(1)
        else:
            puissance_optique_tx_access = "not found"

        # RX optical power access
        puissance_optique_rx_access = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.4.1.4." + portavecpoint + ".1")
        if re.search(r': (\D?\d+)', str(puissance_optique_rx_access)):
            puissance_optique_rx_access = re.search(r': (\D?\d+)', str(puissance_optique_rx_access)).group(1)
        else:
            puissance_optique_rx_access = "not found"

        # Equipment supplier
        equipementier_sfp = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.5.1.2.1.1.1.1")
        if re.search(r': (\D+)', str(equipementier_sfp)):
            equipementier_sfp = re.search(r': (\D+)', str(equipementier_sfp)).group(1).replace('"', '').replace("\\", "")
        else:
            equipementier_sfp = "not found"

        # Link Length
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.5.1.5.1.1.1.1")
        if "0x0428" in str(result):
            link_length = "4"
        elif "0x0f96" in str(result):
            link_length = "15"
        elif "0x14c8" in str(result):
            link_length = "20"
        elif "0x1eff" in str(result):
            link_length = "30"
        elif "0x28ff" in str(result):
            link_length = "40"
        elif re.search(r'd', str(result)):
            link_length = "10"
        else:
            link_length = "not found"

        # Link Length access
        result = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.5.1.5." + portavecpoint + ".1")
        if "0x0428" in str(result):
            link_length_access = "4"
        elif "0x0f96" in str(result):
            link_length_access = "15"
        elif "0x14c8" in str(result):
            link_length_access = "20"
        elif "0x1eff" in str(result):
            link_length_access = "30"
        elif "0x28ff" in str(result):
            link_length_access = "40"
        elif re.search(r'd', str(result)):
            link_length_access = "10"
        if not re.search(r': (\d+)', str(result)):
            result_new = snmp_request(host, ".1.3.6.1.4.1.738.1.111.3.1.2.5.1.3." + portavecpoint + ".1")
            if re.search(r'SFP-GIG-LX\+-SO', str(result_new)):
                link_length_access = "10"

    # snmp commands for ADVA type
    elif equipment_type == "ADVA":

        # evpl
        evpl = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.66." + portavecpoint)
        evpl = evpl.decode() if isinstance(evpl, bytes) else str(evpl)
        match = re.search(r'INTEGER:\s*(\d+)\s*$', evpl)
        evpl = match.group(1) if match else "not found"

        # type media
        type_media = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.8." + portavecpoint)
        type_media = type_media.decode() if isinstance(type_media, bytes) else str(type_media)
        match = re.search(r'INTEGER:\s*(\d+)\s*$', type_media)
        if match:
            valeur = match.group(1)
            if valeur == "1":
                type_media = "copper"
            elif valeur == "2":
                type_media = "fiber"
            else:
                type_media = valeur
        else:
            type_media = "not found"

        # Admin status
        adminstatus = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.4." + portavecpoint)
        adminstatus = adminstatus.decode() if isinstance(adminstatus, bytes) else str(adminstatus)
        match = re.search(r'INTEGER:\s*(\d+)\s*$', adminstatus)
        if match:
            valeur = match.group(1)
            adminstatus = "up" if valeur == "1" else "down" if valeur == "2" else valeur
        else:
            adminstatus = "not found"

        # Oper status
        operstatus = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.5." + portavecpoint)
        operstatus = operstatus.decode() if isinstance(operstatus, bytes) else str(operstatus)
        match = re.search(r'INTEGER:\s*(\d+)\s*$', operstatus)
        if match:
            valeur = match.group(1)
            operstatus = "up" if valeur == "1" else "down" if valeur == "2" else valeur
        else:
            operstatus = "not found"

        status = adminstatus + "_" + operstatus

        # mtu
        mtu = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.7." + portavecpoint)
        mtu = mtu.decode() if isinstance(mtu, bytes) else str(mtu)
        match = re.search(r'INTEGER:\s*(\d+)\s*$', mtu)
        mtu = match.group(1) if match else "not found"

        # name
        if evpl == "1":
            oid = ".1.3.6.1.4.1.2544.1.12.4.1.4.1.2." + portavecpoint + ".1"
        elif evpl == "2":
            if re.search(r'-PLUS', str(tested_swa)):
                oid = ".1.3.6.1.4.1.2544.1.12.4.1.4.1.2." + portavecpoint + ".2"
            else:
                oid = ".1.3.6.1.4.1.2544.1.12.4.1.4.1.2." + portavecpoint + ".1"
        name = snmp_request(host, oid)
        try:
            name = name.decode() if isinstance(name, bytes) else str(name)
            name = re.search(r'STRING: \"(.*)\"', name).group(1).replace("\\", "").replace('"', "")
        except:
            name = "No name found"

        # Default VLAN
        default_vlan = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.4.1.31." + portavecpoint + ".1")
        default_vlan = default_vlan.decode() if isinstance(default_vlan, bytes) else str(default_vlan)
        match = re.search(r': (\d+)', default_vlan)
        default_vlan = match.group(1) if match else "not found"

        # Speed duplex
        speed_duplex = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.9." + portavecpoint)
        speed_duplex = speed_duplex.decode() if isinstance(speed_duplex, bytes) else str(speed_duplex)
        match = re.search(r': (\d+)', speed_duplex)
        result = match.group(1) if match else None
        speed_duplex = speed_duplex_mapping2.get(result, "type non trouvee")

        # Status speed duplex
        result = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.10." + portavecpoint)
        result = result.decode() if isinstance(result, bytes) else str(result)
        result = re.search(r': (\d+)', result)
        result = result.group(1) if result else None
        status_speed_duplex = speed_duplex_mapping2.get(result, "type non trouvee")

        # In/out octets, discards, errors
        if operstatus.lower() == "up":
            def get_counter(oid):
                val = snmp_request(host, oid)
                val = val.decode() if isinstance(val, bytes) else str(val)
                match = re.search(r': (\d+)', val)
                return match.group(1) if match else "not found"

            in_octets = get_counter(".1.3.6.1.2.1.2.2.1.10." + str(port4))
            in_discards = get_counter(".1.3.6.1.2.1.2.2.1.13." + str(port4))
            in_errors = get_counter(".1.3.6.1.4.1.2544.1.12.5.1.1.1.9." + portavecpoint + ".3")
            out_octets = get_counter(".1.3.6.1.2.1.2.2.1.16." + str(port4))
            out_discards = get_counter(".1.3.6.1.2.1.2.2.1.19." + str(port4))

        # TX optical power
        def get_power(oid):
            val = snmp_request(host, oid)
            val = val.decode() if isinstance(val, bytes) else str(val)
            match = re.search(r': (\D?\d+)', val)
            return match.group(1) if match else "not found"

        puissance_optique_tx = get_power(".1.3.6.1.4.1.2544.1.12.5.1.5.1.33.1.1.1.1.1")
        puissance_optique_rx = get_power(".1.3.6.1.4.1.2544.1.12.5.1.5.1.34.1.1.1.1.1")
        puissance_optique_tx_access = get_power(".1.3.6.1.4.1.2544.1.12.5.1.1.1.33." + portavecpoint + ".1")
        puissance_optique_rx_access = get_power(".1.3.6.1.4.1.2544.1.12.5.1.1.1.34." + portavecpoint + ".1")

        # equipment supplier
        equipementier_sfp = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.7.1.13.1.1.1.1")
        equipementier_sfp = equipementier_sfp.decode() if isinstance(equipementier_sfp, bytes) else str(equipementier_sfp)
        match = re.search(r': \"(.*)\"', equipementier_sfp)
        equipementier_sfp = match.group(1) if match else "No equipment supplier found"

        # Laser Wavelength
        laser_wave_length = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.7.1.70.1.1.1.1")
        laser_wave_length = laser_wave_length.decode() if isinstance(laser_wave_length, bytes) else str(laser_wave_length)
        match = re.search(r': (\d+)', laser_wave_length)
        laser_wave_length = match.group(1) if match else "not found"

        # Link Length
        link_length = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.7.1.69.1.1.1.1")
        link_length = link_length.decode() if isinstance(link_length, bytes) else str(link_length)
        match = re.search(r': (\d+)', link_length)
        link_length = int(match.group(1)) / 1000 if match else "not found"

        # Link Length access
        link_length_access = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.1.1.71." + portavecpoint)
        link_length_access = link_length_access.decode() if isinstance(link_length_access, bytes) else str(link_length_access)
        match = re.search(r': (\d+)', link_length_access)
        link_length_access = int(match.group(1)) / 1000 if match else "not found"

        # SFP connector type
        type_connecteur_sfp = snmp_request(host, ".1.3.6.1.4.1.2544.1.12.4.1.7.1.17.1.1.1.1")
        type_connecteur_sfp = type_connecteur_sfp.decode() if isinstance(type_connecteur_sfp, bytes) else str(type_connecteur_sfp)
        match = re.search(r': (\d+)', type_connecteur_sfp)
        type_code = match.group(1) if match else "not found"
        type_connecteur_sfp_mapping = {
            "0": "Not applicable", "1": "Unknown", "2": "sc", "3": "fcs1cu", "4": "fcs2cu",
            "5": "bnc-tnc", "6": "fccoaxhdr", "7": "fjack", "8": "lc", "9": "mt-rj",
            "10": "mu", "11": "sg", "12": "optpigtail", "13": "hssdc", "14": "cupigtail",
            "15": "vendorspecific", "16": "rj45"
        }
        type_connecteur_sfp = type_connecteur_sfp_mapping.get(type_code, "not found")
        # snmp commands for NE05 type
    elif equipment_type == "NE05":
        result = snmp_request(host, "1.3.6.1.2.1.2.2.1.2")
        result = result.splitlines()
        for line in result:
            match = re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (GigabitEthernet(\d)/(\d)/(\d))', str(line))
            if match:
                if str(match.group(2)) == str(port[0] + "/" + port[1] + "/" + port[2]):
                    fin_port = match.group(1)
                    break


        oid = f".1.3.6.1.2.1.2.2.1.7.{fin_port}"
        if "1" in net_snmp(ip, oid):
            adminstatus = "up" 
        else:
            adminstatus = "down"

        oid = f".1.3.6.1.2.1.2.2.1.8.{fin_port}"
        if "1" in net_snmp(ip,oid):
            operstatus = "up"
        else :
            operstatus = "down"

        oid = f".1.3.6.1.2.1.31.1.1.1.18.{fin_port}"
        nameresponse = net_snmp(ip, oid)
        match = re.search(r'STRING:\s*(-?\d+)', nameresponse )
        if match:
            name =  match.group(1)  # Retourne uniquement le nombre sous forme de chaîne

        if(operstatus == "up"):
            oid = f".1.3.6.1.2.1.2.2.1.10.{fin_port}"
            in_octets = net_snmp(ip,oid)
            in_octets = extract_counter32(in_octets)

            oid = f".1.3.6.1.2.1.2.2.1.13.{fin_port}"
            in_discards = net_snmp(ip,oid)
            in_discards = extract_counter32(in_discards)

            oid = f".1.3.6.1.2.1.2.2.1.14.{fin_port}"
            in_errors = net_snmp(ip,oid)
            in_errors = extract_counter32(in_errors)
            
            oid = f".1.3.6.1.2.1.2.2.1.16.{fin_port}"
            out_octets = net_snmp(ip,oid)
            out_octets = extract_counter32(out_octets)

            oid = f".1.3.6.1.2.1.2.2.1.19.{fin_port}"
            out_discards = net_snmp(ip,oid)
            out_discards = extract_counter32(out_discards)

            oid = f".1.3.6.1.2.1.2.2.1.20.{fin_port}"
            out_errors = net_snmp(ip,oid)
            out_errors = extract_counter32(out_errors)


        oid = f".1.3.6.1.2.1.2.2.1.5.{fin_port}"
        speed_duplex = net_snmp(ip,oid)
        match = re.search(r'Gauge32:\s*(-?\d+)', speed_duplex)
        if match:
            speed_duplex = match.group(1)
        if speed_duplex == "100000000":
            speed_duplex = "100"
        elif speed_duplex == "1000000000":
            speed_duplex = "1000"

        oid = f".1.3.6.1.2.1.2.2.1.4.{fin_port}"
        mtu = net_snmp(ip,oid)
        match = re.search(r'INTEGER:\s*(\d+)', mtu )
        if match:
            mtu = match.group(1)

        commande = f"snmpwalk -c cpdea -v2c {ip} 1.3.6.1.2.1.31.1.1.1.18 | grep 0/2/5:fibre"

        result = subprocess.getoutput(commande)


        if "iso." in result:
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.9.16912646"
            puissance_optique_tx = net_snmp(ip,oid)
            if puissance_optique_tx is not None:
                puissance_optique_tx = extract_integer(puissance_optique_tx)
                if puissance_optique_tx is not None:
                    puissance_optique_tx = float(puissance_optique_tx) / 100

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.8.16912646"
            puissance_optique_rx = net_snmp(ip,oid)
            if puissance_optique_rx is not None:
                puissance_optique_rx = extract_integer(puissance_optique_rx)
                if puissance_optique_rx is not None:
                    puissance_optique_rx = float(puissance_optique_rx) / 100

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.24.16912646"
            equipementier_sfp = net_snmp(ip, oid)
            match = re.search(r'STRING:\s*"(.*?)"', equipementier_sfp)
            if match:
                equipementier_sfp = match.group(1)

                    
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.2.16912646"
            laser_wave_length = net_snmp(ip,oid)
            laser_wave_length = extract_integer(laser_wave_length)
            if laser_wave_length == 0:
                laser_wave_length = "unknown"

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.3.16912646"
            link_length = net_snmp(ip, oid)
            link_length = extract_integer(link_length)
            if link_length is not None:
                link_length = float(link_length) / 1000
            else:
                link_length = "unknown"

        commande = f"snmpwalk -c cpdea -v2c {ip} 1.3.6.1.2.1.31.1.1.1.18 | grep 0/2/4:fibre"

        result1 = subprocess.getoutput(commande)

        if "iso." in result1:
            port_network2 = "GigabitEthernet 0/2/4" 
            
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.9.16912645"
            puissance_optique_tx_2 = net_snmp(ip,oid)
            if puissance_optique_tx_2 is not None:
                puissance_optique_tx_2 = extract_integer(puissance_optique_tx_2)
                if puissance_optique_tx_2 is not None:
                    puissance_optique_tx_2 = float(puissance_optique_tx_2) / 100

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.8.16912645"
            puissance_optique_rx_2 = net_snmp(ip,oid)
            if puissance_optique_rx_2 is not None:
                puissance_optique_rx_2 = extract_integer(puissance_optique_rx_2)
                if puissance_optique_rx_2 is not None:
                    puissance_optique_rx_2 = float(puissance_optique_rx_2) / 100

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.24.16912645"
            equipementier_sfp_2 = net_snmp(ip, oid)
            match = re.search(r'STRING:\s*"(.*?)"', equipementier_sfp_2)
            if match:
                equipementier_sfp_2 = match.group(1)

                    
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.2.16912645"
            laser_wave_length_2 = net_snmp(ip,oid)
            laser_wave_length_2 = extract_integer(laser_wave_length_2)
            if laser_wave_length_2 == 0:
                laser_wave_length_2 = "unknown"

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.3.16912645"
            link_length_2 = net_snmp(ip, oid)
            link_length_2 = extract_integer(link_length_2)
            if link_length_2 is not None:
                link_length_2 = float(link_length_2) / 1000
            else:
                link_length_2 = "unknown"


    # snmp commands for CISCO type
    elif equipment_type == "CISCO":

        # Admin status
        adminstatus = snmp_request(host, ".1.3.6.1.2.1.2.2.1.7.10" + str(portsanspoint))
        adminstatus = re.search(r'\d+$', adminstatus).group(0)
        if "1" in adminstatus:
            adminstatus = "up"
        elif "2" in adminstatus:
               adminstatus = "down"

        # Oper status
        operstatus = snmp_request(host, ".1.3.6.1.2.1.2.2.1.8.10" + str(portsanspoint))
        operstatus = re.search(r'\d+$', operstatus).group(0)
        if "1" in operstatus:
            operstatus = "up"
        elif "2" in operstatus:
            operstatus = "down"

        status = adminstatus + "_" + operstatus

        # name
        name = snmp_request(host, ".1.3.6.1.2.1.31.1.1.1.18.10" + str(portsanspoint))
        name = re.search(r'\"(.*)\"', name).group(1)

    # snmp commands for CIENA type
    elif equipment_type == "CIENA":

        # Admin status
        adminstatus = snmp_request_public(host, ".1.3.6.1.2.1.2.2.1.7.10001")
        adminstatus = re.search(r'\d+$', adminstatus).group(0)
        if "1" in adminstatus:
            adminstatus = "up"
        elif "2" in adminstatus:
               adminstatus = "down"

        # Oper status
        operstatus = snmp_request_public(host, ".1.3.6.1.2.1.2.2.1.8.10001")
        operstatus = re.search(r'\d+$', operstatus).group(0)
        if "1" in operstatus:
            operstatus = "up"
        elif "2" in operstatus:
            operstatus = "down"

        status = adminstatus + "_" + operstatus

        # name
        name = "Ciena 3902 10/100/G"

    # snmp commands for HUAWEI type
    elif equipment_type == "HUAWEI":
        result = snmp_request(host, "1.3.6.1.2.1.2.2.1.2")
        result = result.splitlines()
        for line in result:
            if re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d)/(\d)/(\d))$', str(line)):
                if re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d)/(\d)/(\d))$', str(line)).group(2) == equipment_port:
                    port_numerique = re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d)/(\d)/(\d))$',
                                               str(line)).group(1)
                    break

        # Admin status
        adminstatus = snmp_request(host, ".1.3.6.1.2.1.2.2.1.7." + str(port_numerique))
        adminstatus = re.search(r'\d+\)+$', adminstatus).group(0)
        if "1" in adminstatus:
            adminstatus = "up"
        elif "2" in adminstatus:
               adminstatus = "down"

        # Oper status
        operstatus = snmp_request(host, ".1.3.6.1.2.1.2.2.1.8." + str(port_numerique))
        operstatus = re.search(r'\d+\)+$', operstatus).group(0)
        if "1" in operstatus:
            operstatus = "up"
        elif "2" in operstatus:
            operstatus = "down"

        status = adminstatus + "_" + operstatus

        # name
        name = snmp_request(host, ".1.3.6.1.2.1.31.1.1.1.18." + str(port_numerique))
        #name = re.search(r'\"(.*)\"', name).group(1)

        # In/Out octets, in/out errors, in/out discards
        if operstatus == "UP":
            in_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.10." + str(port_numerique))
            in_octets = re.search(r'\d+$', in_octets).group(0)

            in_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.13." + str(port_numerique))
            in_discards = re.search(r'\d+$', in_discards).group(0)

            in_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.14." + str(port_numerique))
            in_errors = re.search(r'\d+$', in_errors).group(0)

            out_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.16." + str(port_numerique))
            out_octets = re.search(r'\d+$', out_octets).group(0)

            out_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.19." + str(port_numerique))
            out_discards = re.search(r'\d+$', out_discards).group(0)

            out_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.20." + str(port_numerique))
            out_errors = re.search(r'\d+$', out_errors).group(0)

        # speed duplex
        speed_duplex = snmp_request(host, ".1.3.6.1.2.1.2.2.1.5." + str(port_numerique))
        speed_duplex = re.search(r'\d+$', speed_duplex).group(0)
        if speed_duplex == "1000000000":
            speed_duplex = "1000"
        elif speed_duplex == "100000000":
            speed_duplex = "100"

        # mtu
        mtu = snmp_request(host, ".1.3.6.1.2.1.2.2.1.4." + str(port_numerique))
        mtu = re.search(r'\d+$', mtu).group(0)

    # snmp commands for HUAWEI_SWITCH type
    elif equipment_type == "HUAWEI_SWITCH":
        if cpdea == True:
            result = snmp_request_cpdeacpdea(host, "1.3.6.1.2.1.2.2.1.2")
            result = result.splitlines()
            for line in result:
                if re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d+)/(\d+)/(\d+))', str(line)):
                    if re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d+)/(\d+)/(\d+))', str(line)).group(2) == str(
                            equipment_port):
                        port_numerique = re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d+)/(\d+)/(\d+))',
                                                   str(line)).group(1)
                        break

            if port_numerique != "Null":
                # adminstatus
                adminstatus = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.7." + str(port_numerique))
                adminstatus = re.search(r'\((\d+)\)', str(adminstatus)).group(1)
                if "1" in adminstatus:
                    adminstatus = "up"
                elif "2" in adminstatus:
                       adminstatus = "down"
                else:
                    adminstatus = "not found"

                # operstatus
                operstatus = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.8." + str(port_numerique))
                operstatus = re.search(r'\((\d+)\)', str(operstatus)).group(1)
                if "1" in operstatus:
                    operstatus = "up"
                elif "2" in operstatus:
                    operstatus = "down"
                else:
                    operstatus = "not found"

                status = adminstatus + "_" + operstatus

                # name
                name = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.31.1.1.1.18." + str(port_numerique))
                if re.search(r'\"(.*)\"', str(name)):
                    name = re.search(r'\"(.*)\"', str(name)).group(1)
                else:
                    name = "not found"

                # in/out octets, in/out errors, in/out discards
                if operstatus == "UP":
                    in_octets = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.10." + str(port_numerique))
                    in_octets = re.search(r': (\d+)', str(in_octets)).group(1)

                    in_discards = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.13." + str(port_numerique))
                    in_discards = re.search(r': (\d+)', str(in_discards)).group(1)

                    in_errors = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.14." + str(port_numerique))
                    in_errors = re.search(r': (\d+)', str(in_errors)).group(1)

                    out_octets = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.16." + str(port_numerique))
                    out_octets = re.search(r': (\d+)', str(out_octets)).group(1)

                    out_discards = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.19." + str(port_numerique))
                    out_discards = re.search(r': (\d+)', str(out_discards)).group(1)

                    out_errors = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.20." + str(port_numerique))
                    out_errors = re.search(r': (\d+)', str(out_errors)).group(1)

                # speed duplex
                speed_duplex = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.5." + str(port_numerique))
                speed_duplex = re.search(r': (\d+)', str(speed_duplex)).group(1)
                if "100000000" in str(speed_duplex):
                    speed = "100"
                elif "1000000000" in str(speed_duplex):
                    speed = "1000"

                # mtu
                mtu = snmp_request_cpdeacpdea(host, ".1.3.6.1.2.1.2.2.1.4." + str(port_numerique))
                if re.search(r': (\d+)', str(mtu)):
                    mtu = re.search(r': (\d+)', str(mtu)).group(1)
                else:
                    mtu = "not found"
            else:
                return "Can't reach host or port not found"

        elif not cpdea:
            result = snmp_request(host, "1.3.6.1.2.1.2.2.1.2")
            result = result.splitlines()
            for line in result:
                if re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d+)/(\d+)/(\d+))', str(line)):
                    if re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d+)/(\d+)/(\d+))', str(line)).group(2) == str(equipment_port):
                        port_numerique = re.search(r'1.3.6.1.2.1.2.2.1.2.(\d+) = STRING: (\w+(\d+)/(\d+)/(\d+))',
                                                   str(line)).group(1)
                        break

            if port_numerique != "Null":
                # adminstatus
                adminstatus = snmp_request(host, ".1.3.6.1.2.1.2.2.1.7." + str(port_numerique))
                adminstatus = re.search(r'\((\d+)\)', str(adminstatus)).group(1)
                if "1" in adminstatus:
                    adminstatus = "up"
                elif "2" in adminstatus:
                       adminstatus = "down"
                else:
                    adminstatus = "not found"

                # operstatus
                operstatus = snmp_request(host, ".1.3.6.1.2.1.2.2.1.8." + str(port_numerique))
                operstatus = re.search(r'\((\d+)\)', str(operstatus)).group(1)
                if "1" in operstatus:
                    operstatus = "up"
                elif "2" in operstatus:
                    operstatus = "down"
                else:
                    operstatus = "not found"

                # name
                name = snmp_request(host, ".1.3.6.1.2.1.31.1.1.1.18." + str(port_numerique))
                if re.search(r'\"(.*)\"', str(name)):
                    name = re.search(r'\"(.*)\"', str(name)).group(1)
                else:
                    name = "not found"

                # in/out octets, in/out errors, in/out discards
                if operstatus == "UP":
                    in_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.10." + str(port_numerique))
                    in_octets = re.search(r': (\d+)', str(in_octets)).group(1)

                    in_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.13." + str(port_numerique))
                    in_discards = re.search(r': (\d+)', str(in_discards)).group(1)

                    in_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.14." + str(port_numerique))
                    in_errors = re.search(r': (\d+)', str(in_errors)).group(1)

                    out_octets = snmp_request(host, ".1.3.6.1.2.1.2.2.1.16." + str(port_numerique))
                    out_octets = re.search(r': (\d+)', str(out_octets)).group(1)

                    out_discards = snmp_request(host, ".1.3.6.1.2.1.2.2.1.19." + str(port_numerique))
                    out_discards = re.search(r': (\d+)', str(out_discards)).group(1)

                    out_errors = snmp_request(host, ".1.3.6.1.2.1.2.2.1.20." + str(port_numerique))
                    out_errors = re.search(r': (\d+)', str(out_errors)).group(1)

                # speed duplex
                speed_duplex = snmp_request(host, ".1.3.6.1.2.1.2.2.1.5." + str(port_numerique))
                speed_duplex = re.search(r': (\d+)', str(speed_duplex)).group(1)
                if "100000000" in str(speed_duplex):
                    speed = "100"
                elif "1000000000" in str(speed_duplex):
                    speed = "1000"

                # mtu
                mtu = snmp_request(host, ".1.3.6.1.2.1.2.2.1.4." + str(port_numerique))
                if re .search(r': (\d+)', str(mtu)):
                    mtu = re.search(r': (\d+)', str(mtu)).group(1)
                else:
                    mtu = "not found"
            else:
                return "Can't reach host or port not found"

    if "NE8000" in equipment_type:

        commande = ["snmpwalk", "-c", "cpdea", "-v2c", ip, "1.3.6.1.2.1.2.2.1.2"]
        try:
            result = subprocess.check_output(commande, text=True)
            match = re.search(rf"1.3.6.1.2.1.2.2.1.2\.(\d+) = STRING: GigabitEthernet1\\n", result)
            if match:
                fin_port = match.group(1)
        except subprocess.CalledProcessError:
            return "Erreur lors de la récupération du port"

        # Statuts administratifs et opérationnels
        oid = f".1.3.6.1.2.1.2.2.1.7.{fin_port}"
        if "1" in net_snmp(ip, oid):
            adminstatus = "up" 
        else:
            adminstatus = "down"

        oid = f".1.3.6.1.2.1.2.2.1.8.{fin_port}"
        if "1" in net_snmp(ip, oid):
            operstatus = "up" 
        else:
            operstatus = "down"

        status = f"{adminstatus}-{operstatus}"

        # Nom de l'interface
        oid = f".1.3.6.1.2.1.31.1.1.1.18.{fin_port}"
        nameresponse = net_snmp(ip, oid)
        match = re.search(r'STRING:\s*(-?\d+)', nameresponse )
        if match:
            name =  match.group(1)  # Retourne uniquement le nombre sous forme de chaîne


        # Si l'interface est active, récupérer les statistiques
        if operstatus == "up":
            inoctets = net_snmp(ip, f".1.3.6.1.2.1.2.2.1.10.{fin_port}")
            indiscards = net_snmp(ip, f".1.3.6.1.2.1.2.2.1.13.{fin_port}")
            inerrors = net_snmp(ip, f".1.3.6.1.2.1.2.2.1.14.{fin_port}")
            outoctets = net_snmp(ip, f".1.3.6.1.2.1.2.2.1.16.{fin_port}")
            outdiscards = net_snmp(ip, f".1.3.6.1.2.1.2.2.1.19.{fin_port}")
            outerrors = net_snmp(ip, f".1.3.6.1.2.1.2.2.1.20.{fin_port}")

        # Vitesse et duplex
        oid = f".1.3.6.1.2.1.2.2.1.5.{fin_port}"
        speed_duplex = net_snmp(ip, oid)
        match = re.search(r'Gauge32:\s*(-?\d+)', speed_duplex)
        if match:
            speed_duplex = match.group(1)
        if speed_duplex == "100000000":
            speed_duplex = "100"
        elif speed_duplex == "1000000000":
            speed_duplex = "1000"

        # MTU
        oid = f".1.3.6.1.2.1.2.2.1.4.{fin_port}"
        mtu = net_snmp(ip, oid)
        match = re.search(r'INTEGER:\s*(\d+)', mtu )
        if match:
            mtu = match.group(1)

        commande = f"snmpwalk -c cpdea -v2c {ip} 1.3.6.1.2.1.31.1.1.1.18 | grep 0/2/0:fibre"

        result = subprocess.getoutput(commande)


        if "iso." in result:
    
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.9.16912641"
            puissance_optique_tx = net_snmp(ip, oid)
            if puissance_optique_tx is not None:
                puissance_optique_tx = extract_integer(puissance_optique_tx)
                if puissance_optique_tx is not None:
                    puissance_optique_tx = float(puissance_optique_tx) / 100

            # Puissance optique RX
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.8.16912641"
            puissance_optique_rx = net_snmp(ip, oid)
            if puissance_optique_rx is not None:
                puissance_optique_rx = extract_integer(puissance_optique_rx)
                if puissance_optique_rx is not None:
                    puissance_optique_rx = float(puissance_optique_rx) / 100

            # Équipementier SFP
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.24.16912641"
            result = net_snmp(ip, oid)
            match = re.search(r'STRING:\s*"(.*?)"', result)
            if match:
                equipementier_sfp = match.group(1)


            # Longueur d'onde du laser
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.2.16912641"
            laser_wave_length = net_snmp(ip, oid)
            laser_wave_length = extract_integer(laser_wave_length)
            if laser_wave_length == 0:
                laser_wave_length = "unknown"

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.3.16912641"
            link_length = net_snmp(ip, oid)
            link_length = extract_integer(link_length)
            if link_length is not None :
               link_length = float(link_length) / 1000
            else:
                link_length = "unknown"

        commande = f"snmpwalk -c cpdea -v2c {ip} 1.3.6.1.2.1.31.1.1.1.18 | grep 0/2/1:fibre"

        result = subprocess.getoutput(commande)

       
        if "iso." in result:
            port_network2 = "GigabitEthernet 0/2/1" 

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.9.16912642"
            puissance_optique_tx_2 = net_snmp(ip, oid)
            if puissance_optique_tx_2 is not None:
                puissance_optique_tx_2 = extract_integer(puissance_optique_tx_2)
                if puissance_optique_tx_2 is not None:
                    puissance_optique_tx_2 = float(puissance_optique_tx_2) / 100

            # Puissance optique RX
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.8.16912642"
            puissance_optique_rx_2 = net_snmp(ip, oid)
            if puissance_optique_rx_2 is not None:
                puissance_optique_rx_2 = extract_integer(puissance_optique_rx_2)
                if puissance_optique_rx_2 is not None:
                    puissance_optique_rx_2 = float(puissance_optique_rx_2) / 100

            # Équipementier SFP
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.24.16912642"
            result = net_snmp(ip, oid)
            match = re.search(r'STRING:\s*"(.*?)"', result)
            if match:
                equipementier_sfp_2 = match.group(1)

            # Longueur d'onde du laser
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.2.16912642"
            laser_wave_length_2 = net_snmp(ip, oid)
            laser_wave_length_2 = extract_integer(laser_wave_length_2)
            if laser_wave_length_2 == 0:
                laser_wave_length_2 = "unknown"

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.3.16912642"
            link_length_2 = net_snmp(ip, oid)
            link_length_2 = extract_integer(link_length_2)
            if link_length_2 is not None :
               link_length_2 = float(link_length_2) / 1000
            else:
                link_length_2 = "unknown"


        if "0/2/5" in equipment_port:
            # Longueur de lien
            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.3.16912646"
            link_length = net_snmp(ip, oid)
            link_length = extract_integer(link_length)
            if link_length is not None :
               link_length = float(link_length) / 1000
            else:
                link_length = "unknown"

        else :

            oid = ".1.3.6.1.4.1.2011.5.25.31.1.1.3.1.3.16912641"
            link_length = net_snmp(ip, oid)
            link_length = extract_integer(link_length)
            if link_length is not None :
               link_length = float(link_length) / 1000
            else:
                link_length = "unknown"


    snmpinfo = {
        'ip': ip,
        'port':equipment_port,
        'type equipement': equipment_type,
        'admin status': adminstatus,
        'oper status': operstatus,
        'mtu': mtu,
        'in_octets': in_octets,
        'in_discards': in_discards,
        'in_errors': in_errors,
        'out_octets': out_octets,
        'out_discards': out_discards,
        'out_errors': out_errors,
        'speed duplex': speed_duplex,
        'mac 97 bas': mac_97_bas,
        'mac 97 nte': mac_97_nte,
        'name': name,
        'equipment version': equipment_version,
        'default VLAN': default_vlan,
        'status speed duplex': status_speed_duplex,
        'type media': type_media,
        'Link Length Access': link_length_access,
        'puissance optique TX access': puissance_optique_tx_access,
        'puissance optique RX access': puissance_optique_rx_access,
        'MAC/VLAN': mac_vlan,
        'evpl': evpl,
        'fin port':fin_port
    }

    snmpinfonetwork = {
        'type equipement': equipment_type,
        'puissance optique TX': puissance_optique_tx,
        'puissance optique RX': puissance_optique_rx,
        'equipementier SFP': equipementier_sfp,
        'type connecteur SFP': type_connecteur_sfp,
        'Laser Wave Length': laser_wave_length,
        'Link Length': link_length,
    }

    
    if  port_network2 is not None:
        snmp_infonetwork2 = {
            'puissance optique TX 2':puissance_optique_tx_2,
            'puissance optique RX 2':puissance_optique_rx_2,
            'equipementier SFP 2':equipementier_sfp_2,
            'laser wave length 2':laser_wave_length_2,
            'link length 2':link_length_2

        }
        tableaux = [snmpinfo, snmpinfonetwork,port_network2,snmp_infonetwork2]
    else:
        tableaux = [snmpinfo, snmpinfonetwork]

    return tableaux