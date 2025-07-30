import re
import subprocess
from scripts.ClassConversion import convert

def get_card_names(adresse_ip, oid):
    try:
        card_names = []
        command = f"snmpwalk -v2c -c cpdea {adresse_ip} {oid}"
        output_bytes = subprocess.check_output(command, shell=True)
        output_text = output_bytes.decode('utf-8').strip()
        name = re.findall(r'STRING: "(.*?)\s*"', output_text)
        
        card_names.extend(name)
        return card_names
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande SNMP : {e}")
        print(f"Sortie de la commande : {e.output.decode('utf-8').strip()}")
        return None
    
def get_slot(adresse_ip, oid):
    # Le slot représente le dernier digit de l'OID
    try:
        card_slots = []
        command = f"snmpwalk -v2c -c cpdea {adresse_ip} {oid}"
        output_bytes = subprocess.check_output(command, shell=True)
        output_text = output_bytes.decode('utf-8').strip()
        # Expression régulière pour supprimer tout ce qui se trouve après le "="
        slots_cartesV1 = re.findall(r'^(.*?)=', output_text, re.MULTILINE)
        for slot in slots_cartesV1:
            # Coupe et garde ce qu'il y a après le dernier point
            slot_number = re.search(r'\.(\d+)\s*$', slot, re.MULTILINE)
            if slot_number:
                card_slots.append(slot_number.group(1).strip())
        if card_slots:
            return card_slots
        else:
            print("Aucun numéro de slot trouvé")
            return None

    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande SNMP : {e}")
        print(f"Sortie de la commande : {e.output.decode('utf-8').strip()}")
        return None
    
def get_shelf(adresse_ip, oid):
    # Le shelf est l'avant dernier digit de l'OID
    try:
        card_shelf = []
        command = f"snmpwalk -v2c -c cpdea {adresse_ip} {oid}"
        output_bytes = subprocess.check_output(command, shell=True)
        output_text = output_bytes.decode('utf-8').strip()
        # Expression régulière pour capturer tout avant le dernier point
        expr_reg = re.compile(r'^(.*\.\d+)\.', re.MULTILINE)
        shelf_cartesV1 = [match.group(1) for match in expr_reg.finditer(output_text)]
        # Expression régulière pour capturer le chiffre après le dernier point
        expr_reg_digit = re.compile(r'\.(\d+)\s*$', re.MULTILINE)
        for shelf in shelf_cartesV1:
            digit_match = expr_reg_digit.search(shelf)
            if digit_match:
                card_shelf.append(int(digit_match.group(1)))
        if card_shelf:
            return card_shelf
        else:
            print("Aucun numéro de shelf trouvé")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande SNMP : {e}")
        print(f"Sortie de la commande : {e.output.decode('utf-8').strip()}")
        return None
    
def get_index(adresse_ip, oid):
    # Retour de l'index qui est le dernier digit des OIDs 
    try:
        card_index = []
        command_index = f"snmpwalk -v2c -c cpdea {adresse_ip} {oid}"
        output_bytes = subprocess.check_output(command_index, shell=True)
        output_text = output_bytes.decode('utf-8').strip()
        # Expression régulière pour capturer tout avant le dernier point 
        expr_reg = re.findall(r'\.([^.]+)\s*=\s*.*$', output_text, re.MULTILINE)
        for index in expr_reg:
            card_index.append(index)
        if card_index:
            return card_index
        else:
            print("Aucun numéro d'index trouvé")
            return None

    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande SNMP : {e}")
        print(f"Sortie de la commande : {e.output.decode('utf-8').strip()}")
        return None

def get_tab_index(adresse_ip, oid):
    # Retour de la liste des index
    try:
        command_list_index = f"snmpwalk -v2c -c cpdea {adresse_ip} {oid}"
        output_bytes = subprocess.check_output(command_list_index, shell=True)
        output_text = output_bytes.decode('utf-8').strip()
        expr_reg = re.findall(r'\.([^.]+)\s*=\s*.*$', output_text, re.MULTILINE)
        return expr_reg

    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande SNMP : {e}")
        print(f"Sortie de la commande : {e.output.decode('utf-8').strip()}")
        return None
    
def get_list_port_name(adresse_ip, oid, i):
    # Retour de la liste du nom des ports
    try:
        port_name = []
        command_port_name = f"snmpwalk -v2c -c cpdea {adresse_ip} {oid}"
        output_bytes = subprocess.check_output(command_port_name, shell=True)
        output_text = output_bytes.decode('utf-8').strip().splitlines()
        for output in output_text:
            res=output.split("STRING: ", 1)[1]
            port_name.append(res)
        return port_name[i]

    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande SNMP : {e}")
        print(f"Sortie de la commande : {e.output.decode('utf-8').strip()}")
        return None
    
def get_index_name(index, adresse_ip, oid):
    # Récupère la position de l'index récupéré 
    list_index = get_tab_index(adresse_ip, oid)
    for lIndex in list_index:
        IntIndex = int(lIndex)
        if IntIndex == index :
            position = list_index.index(lIndex)
    res = get_list_port_name(adresse_ip, oid, position)
    return res

def get_version(host):
    command = f"snmpget -v2c -c cpdea {host} 1.3.6.1.2.1.1.1.0"
    output_bytes = subprocess.check_output(command, shell=True)
    output_text = output_bytes.decode('utf-8').strip()
    if "No Such Instance" in output_text:
        return None
    else:
        match = re.search(r'v\d+\.\d+', output_text)
        if match:
            version = match.group(0)
            return version
    return None

def opticalTransponders(shelf, slot, adresse_ip):
    detailOpticalTransponders = []

    oidIndex = "1.3.6.1.2.1.31.1.1.1.1"
    oidReceivePower = f"1.3.6.1.4.1.7483.2.2.4.3.5.71.1.1"
    oidTransmitPower = f"1.3.6.1.4.1.7483.2.2.4.3.5.71.1.2"
    oidQMargin = f"1.3.6.1.4.1.7483.2.4.1.2.3.96.1.4"
    oidTrafficTx = f"1.3.6.1.4.1.7483.2.4.1.2.3.8.1.22"
    oidTrafficRx = f"1.3.6.1.4.1.7483.2.4.1.2.3.8.1.6"
    oidTxCrc = f"1.3.6.1.4.1.7483.2.4.1.2.3.8.1.17"
    oidRxCrc = f"1.3.6.1.4.1.7483.2.4.1.2.3.8.1.33"
    oidTemp = f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    oidMeasuredCurrent = f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.39.{shelf}.{slot}"
    oidMeasuredPower = f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.38.{shelf}.{slot}"

    commandReceivePower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidReceivePower}"
    commandTransmitPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTransmitPower}"
    commandQMargin = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidQMargin}"
    commandTrafficTx = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTrafficTx}"
    commandTrafficRx = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTrafficRx}"
    commandTxCrc = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTxCrc}"
    commandRxCrc = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidRxCrc}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    commandMeasuredCurrent = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredCurrent}"
    commandMeasuredPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredPower}"

    # output_receive = "test"
    # output_transmit = "test"
    # output_qmargin = "test"
    # output_traffic_tx = "test"
    # output_traffic_rx = "test"
    # output_tx_crc = "test"
    # output_rx_crc = "test"
    # output_temp = "test"
    # output_measured_current = "test"
    # output_measured_power = "test"
    tab_receive = []
    output_bytes_receive = subprocess.check_output(commandReceivePower, shell=True)
    output_receive = output_bytes_receive.decode('utf-8').strip()
    if "INTEGER: " in output_receive:
        output_receive = re.findall(r'INTEGER: (.+)', output_receive, re.MULTILINE)
        res_receive_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_receive, res_receive_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_receive = f"{name_index} : {int(res) /100} dBm"
            tab_receive.append(output_receive)
    
    tab_transmit = []
    output_bytes_transmit = subprocess.check_output(commandTransmitPower, shell=True)
    output_transmit = output_bytes_transmit.decode('utf-8').strip()
    if "INTEGER: " in output_transmit:
        output_transmit = re.findall(r'INTEGER: (.+)', output_transmit, re.MULTILINE)
        res_transmit_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_transmit, res_transmit_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_transmit = f"{name_index} : {int(res) /100} dBm"
            tab_transmit.append(output_transmit)

    tab_traffic_tx = []
    output_bytes_traffic_tx = subprocess.check_output(commandTrafficTx, shell=True)
    output_traffic_tx = output_bytes_traffic_tx.decode('utf-8').strip()
    if "Counter64: " in output_traffic_tx:
        output_traffic_tx = re.findall(r'Counter64: (.+)', output_traffic_tx, re.MULTILINE)
        res_traffic_tx_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_traffic_tx, res_traffic_tx_index):
            res = int(res)
            convertTool= convert(res)
            res=convertTool.converterOctalToBits()
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_traffic_tx = f"{name_index} : {res} "
            tab_traffic_tx.append(output_traffic_tx)
    
    tab_traffic_rx = []
    output_bytes_traffic_rx = subprocess.check_output(commandTrafficRx, shell=True)
    output_traffic_rx = output_bytes_traffic_rx.decode('utf-8').strip()
    if "Counter64: " in output_traffic_rx:
        output_traffic_rx = re.findall(r'Counter64: (.+)', output_traffic_rx, re.MULTILINE)
        res_traffic_rx_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_traffic_rx, res_traffic_rx_index):
            res = int(res)
            convertTool= convert(res)
            res=convertTool.converterOctalToBits()
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_traffic_rx = f"{name_index} : {res} "
            tab_traffic_rx.append(output_traffic_rx)
    
    tab_tx_crc = [] 
    output_bytes_tx_crc = subprocess.check_output(commandTxCrc, shell=True)
    output_tx_crc = output_bytes_tx_crc.decode('utf-8').strip()
    if "Counter64: " in output_tx_crc:
        output_tx_crc = re.findall(r'Counter64: (.+)', output_tx_crc, re.MULTILINE)
        res_tx_crc_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_tx_crc, res_tx_crc_index):
            res = int(res)
            convertTool= convert(res)
            res=convertTool.converterOctalToBits()
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_tx_crc = f"{name_index} : {res} "
            tab_tx_crc.append(output_tx_crc)
    
    tab_rx_crc = [] 
    output_bytes_rx_crc = subprocess.check_output(commandRxCrc, shell=True)
    output_rx_crc = output_bytes_rx_crc.decode('utf-8').strip()
    if "Counter64: " in output_rx_crc:
        output_rx_crc = re.findall(r'Counter64: (.+)', output_rx_crc, re.MULTILINE)
        res_rx_crc_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_rx_crc, res_rx_crc_index):
            res = int(res)
            convertTool= convert(res)
            res=convertTool.converterOctalToBits()
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_rx_crc = f"{name_index} : {res} "
            tab_rx_crc.append(output_rx_crc)
    
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
    
    output_bytes_measured_current = subprocess.check_output(commandMeasuredCurrent, shell=True)
    output_measured_current = output_bytes_measured_current.decode('utf-8').strip()
    if "Gauge32: " in output_measured_current:
        output_measured_current=output_measured_current.split("Gauge32: ", 1)[1]
    
    output_bytes_measured_power = subprocess.check_output(commandMeasuredPower, shell=True)
    output_measured_power = output_bytes_measured_power.decode('utf-8').strip()
    if "INTEGER: " in output_measured_power:
        output_measured_power=output_measured_power.split("INTEGER: ", 1)[1]
    
    detailOpticalTransponders.append(tab_receive)
    detailOpticalTransponders.append(tab_transmit)
    detailOpticalTransponders.append(tab_traffic_tx)
    detailOpticalTransponders.append(tab_traffic_rx)
    detailOpticalTransponders.append(tab_tx_crc)
    detailOpticalTransponders.append(tab_rx_crc)
    detailOpticalTransponders.append(output_temp)
    detailOpticalTransponders.append(output_measured_current)
    detailOpticalTransponders.append(output_measured_power)
    
    return detailOpticalTransponders

def opticalAmplifiers(shelf, slot, adresse_ip):
    detailOpticalAmplifiers = {}
    verif = True
    i = 0
    
    while verif:
        oidIndex = "1.3.6.1.2.1.31.1.1.1.1"
        oidTotalInputPower = f"1.3.6.1.4.1.7483.2.2.4.3.5.72.1.1"
        oidTotalOutputPower = f"1.3.6.1.4.1.7483.2.2.4.3.5.72.1.2"
        oidCurrentGain = f"1.3.6.1.4.1.7483.2.2.3.7.4.2.1.1"
        oidTemp = f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
        oidMeasuredCurrent = f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.39.{shelf}.{slot}"
        oidMeasuredPower = f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.38.{shelf}.{slot}"
        oidChannelPower = f"1.3.6.1.4.1.7483.2.2.3.2.2.1.11.1.7"

        commandTotalInputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalInputPower}"
        commandTotalOutputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOutputPower}"
        commandCurrentGain = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidCurrentGain}"
        commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
        commandMeasuredCurrent = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredCurrent}"
        commandMeasuredPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredPower}"
        commandChannelPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidChannelPower}"
        
        numPort = i + 1
        if numPort not in detailOpticalAmplifiers:
            detailOpticalAmplifiers[numPort] = []
        port_list = detailOpticalAmplifiers[numPort]
        
        try:
            output_bytes_total_input = subprocess.check_output(commandTotalInputPower, shell=True)
            output_total_input = output_bytes_total_input.decode('utf-8').strip()
            if "No Such" in output_total_input:
                verif = False
            else:
                if "INTEGER: " in output_total_input:
                    res_total_input = re.findall(r'INTEGER: (.+)', output_total_input, re.MULTILINE)
                    res_total_input_index = get_index(adresse_ip, oidIndex)
                    for (res, res_index) in zip(res_total_input, res_total_input_index):
                        res_index = int(res_index)
                        name_index = get_index_name(res_index, adresse_ip, oidIndex)
                        output_total_input = f"{name_index} : {int(res) / 100} dBm"
                port_list.append(output_total_input)
                
                output_bytes_total_output = subprocess.check_output(commandTotalOutputPower, shell=True)
                output_total_output = output_bytes_total_output.decode('utf-8').strip()
                if "INTEGER: " in output_total_output:
                    res_power_out = re.findall(r'INTEGER: (.+)', output_total_output, re.MULTILINE)
                    res_power_out_index = get_index(adresse_ip, oidIndex)
                    for (res, res_index) in zip(res_power_out, res_power_out_index):
                        res_index = int(res_index)
                        name_index = get_index_name(res_index, adresse_ip, oidIndex)
                        output_total_output = f"{name_index} : {int(res) / 100} dBm"
                port_list.append(output_total_output)
                
                output_bytes_current_gain = subprocess.check_output(commandCurrentGain, shell=True)
                output_current_gain = output_bytes_current_gain.decode('utf-8').strip()
                if "Gauge32: " in output_current_gain:
                    res_current_gain = re.findall(r'Gauge32: (.+)', output_current_gain, re.MULTILINE)
                    res_current_gain_index = get_index(adresse_ip, oidIndex)
                    for (res, res_index) in zip(res_current_gain, res_current_gain_index):
                        res_index = int(res_index)
                        name_index = get_index_name(res_index, adresse_ip, oidIndex)
                        output_current_gain = f"{name_index} : {int(res) / 100} dB"
                port_list.append(output_current_gain)
                
                output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
                output_temp = output_bytes_temp.decode('utf-8').strip()
                if "INTEGER: " in output_temp:
                    output_temp = output_temp.split("INTEGER: ", 1)[1]
                port_list.append(f"{output_temp} °C")
                
                output_bytes_measured_current = subprocess.check_output(commandMeasuredCurrent, shell=True)
                output_measured_current = output_bytes_measured_current.decode('utf-8').strip()
                if "Gauge32: " in output_measured_current:
                    output_measured_current = output_measured_current.split("Gauge32: ", 1)[1]
                    output_measured_current = int(output_measured_current) / 1000
                    port_list.append(f"{output_measured_current} Amp")
                else:
                    port_list.append("Carte pas concerné")
                
                output_bytes_measured_power = subprocess.check_output(commandMeasuredPower, shell=True)
                output_measured_power = output_bytes_measured_power.decode('utf-8').strip()
                if "INTEGER: " in output_measured_power:
                    output_measured_power = output_measured_power.split("INTEGER: ", 1)[1]
                    output_measured_power = int(output_measured_power) / 1000
                    port_list.append(f"{output_measured_power} Watt")
                else:
                    port_list.append("Carte pas concerné")
                
                output_bytes_channel_power_in = subprocess.check_output(commandChannelPower, shell=True)
                output_power = output_bytes_channel_power_in.decode('utf-8').strip()
                
                if "INTEGER: " in output_power:
                    tabPowerIn = []
                    tabPowerOut = []
                    res_power = re.findall(r'INTEGER: (.+)', output_power, re.MULTILINE)
                    les_shelf = get_shelf(adresse_ip, oidIndex)
                    for shelf, res in zip(les_shelf, res_power):
                        res = int(res) / 100
                        if int(shelf) == 2:
                            tabPowerIn.append(f"{res} dBm")
                        else:
                            tabPowerOut.append(f"{res} dBm")
                    port_list.append(tabPowerIn)
                    port_list.append(tabPowerOut)
                
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    
    return detailOpticalAmplifiers

def opticalAmplifiersGeneral(shelf, slot, adresse_ip):
    detailOpticalAmplifiers= []
    oidIndex = "1.3.6.1.2.1.31.1.1.1.1"
    oidTotalInputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.72.1.1"
    oidTotalOutputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.72.1.2"
    oidCurrentGain=f"1.3.6.1.4.1.7483.2.2.3.7.4.2.1.1"
    oidTemp=f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    oidMeasuredCurrent =f".1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.39.{shelf}.{slot}"
    oidMeasuredPower =f".1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.38.{shelf}.{slot}"
    
    commandTotalInputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalInputPower}"
    commandTotalOutputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOutputPower}"
    commandCurrentGain = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidCurrentGain}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    commandMeasuredCurrent = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredCurrent}"
    commandMeasuredPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredPower}"
    
    output_bytes_total_input = subprocess.check_output(commandTotalInputPower, shell=True)
    output_total_input = output_bytes_total_input.decode('utf-8').strip()
    tab_total_input = []
    if "INTEGER: " in output_total_input:
        output_total_input = re.findall(r'INTEGER: (.+)', output_total_input, re.MULTILINE)
        res_total_input_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_total_input, res_total_input_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_total_input = f"{name_index} : {int(res) /100}0101010 dBm"
            tab_total_input.append(output_total_input)
            
    output_bytes_total_output = subprocess.check_output(commandTotalOutputPower, shell=True)
    output_total_output = output_bytes_total_output.decode('utf-8').strip()
    tab_total_output = []
    if "INTEGER: " in output_total_output:
        output_total_output = re.findall(r'INTEGER: (.+)', output_total_output, re.MULTILINE)
        res_power_out_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_total_output, res_power_out_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_total_output = f"{name_index} : {int(res) /100} dBm"
            tab_total_output.append(output_total_output)
    
    output_bytes_current_gain = subprocess.check_output(commandCurrentGain, shell=True)
    output_current_gain = output_bytes_current_gain.decode('utf-8').strip()
    tab_current_gain = []
    if "Gauge32: " in output_current_gain:
        output_current_gain = re.findall(r'Gauge32: (.+)', output_current_gain, re.MULTILINE)
        res_current_gain_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_current_gain, res_current_gain_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_current_gain = f"{name_index} : {int(res) /100} dB"
            tab_current_gain.append(output_current_gain)
    
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
        output_temp = f"{output_temp}°C"
    else:
        output_temp = "Carte pas concerné"
    
    output_bytes_measured_current = subprocess.check_output(commandMeasuredCurrent, shell=True)
    output_measured_current = output_bytes_measured_current.decode('utf-8').strip()
    if "Gauge32: " in output_measured_current:
        output_measured_current=output_measured_current.split("Gauge32: ", 1)[1]
        output_measured_current = int(output_measured_current)/1000
        output_measured_current = f"{output_measured_current} Amp"
    else:
        output_measured_current = "Carte pas concerné"
    
    output_bytes_measured_power = subprocess.check_output(commandMeasuredPower, shell=True)
    output_measured_power = output_bytes_measured_power.decode('utf-8').strip()
    if "INTEGER: " in output_measured_power:
        output_measured_power=output_measured_power.split("INTEGER: ", 1)[1]
        output_measured_power = int(output_measured_power)/1000
        output_measured_power = f"{output_measured_power} Watt"
    else:
        output_measured_power = "Carte pas concerné"

    detailOpticalAmplifiers.append(tab_total_input)
    detailOpticalAmplifiers.append(tab_total_output)
    detailOpticalAmplifiers.append(tab_current_gain)
    detailOpticalAmplifiers.append(output_temp)
    detailOpticalAmplifiers.append(output_measured_current)
    detailOpticalAmplifiers.append(output_measured_power)
    return detailOpticalAmplifiers

def opticalAmplifiersForAs(shelf, slot, adresse_ip):
    detailOpticalAmplifiers= []
    oidIndex = "1.3.6.1.2.1.31.1.1.1.1"
    oidTotalInputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.72.1.1"
    oidTotalOutputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.72.1.2"
    oidCurrentGain=f"1.3.6.1.4.1.7483.2.2.3.7.4.2.1.1"
    oidTemp=f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    oidMeasuredCurrent =f".1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.39.{shelf}.{slot}"
    oidMeasuredPower =f".1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.38.{shelf}.{slot}"
    oidChannelPower=f"1.3.6.1.4.1.7483.2.2.3.2.2.1.11.1.7"
    oidOSCsfpPowerOut=f"1.3.6.1.4.1.7483.2.2.3.7.5.2.1.23"
    oidOSCsfpPowerIn=f"1.3.6.1.4.1.7483.2.2.3.7.5.2.1.24"

    commandTotalInputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalInputPower}"
    commandTotalOutputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOutputPower}"
    commandCurrentGain = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidCurrentGain}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    commandMeasuredCurrent = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredCurrent}"
    commandMeasuredPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredPower}"
    commandChannelPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidChannelPower}"
    commandOSCsfpPowerOut = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidOSCsfpPowerOut}"
    commandOSCsfpPowerIn= f"snmpwalk -v2c -c cpdea {adresse_ip} {oidOSCsfpPowerIn}"

    output_bytes_total_input = subprocess.check_output(commandTotalInputPower, shell=True)
    output_total_input = output_bytes_total_input.decode('utf-8').strip()
    tab_total_input = []
    if "INTEGER: " in output_total_input:
        output_total_input = re.findall(r'INTEGER: (.+)', output_total_input, re.MULTILINE)
        res_total_input_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_total_input, res_total_input_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_total_input = f"{name_index} : {int(res) /100} dBm"
            tab_total_input.append(output_total_input)
    
    output_bytes_total_output = subprocess.check_output(commandTotalOutputPower, shell=True)
    output_total_output = output_bytes_total_output.decode('utf-8').strip()
    tab_total_output = []
    if "INTEGER: " in output_total_output:
        output_total_output = re.findall(r'INTEGER: (.+)', output_total_output, re.MULTILINE)
        res_power_out_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_total_output, res_power_out_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_total_output = f"{name_index} : {int(res) /100} dBm"
            tab_total_output.append(output_total_output)
    
    output_bytes_current_gain = subprocess.check_output(commandCurrentGain, shell=True)
    output_current_gain = output_bytes_current_gain.decode('utf-8').strip()
    tab_current_gain = []
    if "Gauge32: " in output_current_gain:
        output_current_gain = re.findall(r'Gauge32: (.+)', output_current_gain, re.MULTILINE)
        res_current_gain_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_current_gain, res_current_gain_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_current_gain = f"{name_index} : {int(res) /100} dB"
            tab_current_gain.append(output_current_gain)
    
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
        output_temp = f"{output_temp} °C"
    
    output_bytes_measured_current = subprocess.check_output(commandMeasuredCurrent, shell=True)
    output_measured_current = output_bytes_measured_current.decode('utf-8').strip()
    if "Gauge32: " in output_measured_current:
        output_measured_current=output_measured_current.split("Gauge32: ", 1)[1]
        output_measured_current = int(output_measured_current)/1000
        output_measured_current = f"{output_measured_current} Amp"
        
    else :
        output_measured_current= "Carte pas concerné"
    
    output_bytes_measured_power = subprocess.check_output(commandMeasuredPower, shell=True)
    output_measured_power = output_bytes_measured_power.decode('utf-8').strip()
    if "INTEGER: " in output_measured_power:
        output_measured_power=output_measured_power.split("INTEGER: ", 1)[1]
        output_measured_power = int(output_measured_power)/1000
        output_measured_power = f"{output_measured_power} Watt"
    else :
        output_measured_power = "Carte pas concerné"
    
    
    output_bytes_channel_power_in = subprocess.check_output(commandChannelPower, shell=True)
    output_power = output_bytes_channel_power_in.decode('utf-8').strip()
    tabPowerIn = []
    tabPowerOut = []
    if "INTEGER: " in output_power:
        tab_power = re.findall(r'INTEGER: (.+)', output_power, re.MULTILINE)
        shelfStep1 = re.sub(r'=.*$', '', output_power, re.MULTILINE)
        shelfStep2 = re.sub(r'\.\d$', '', shelfStep1, re.MULTILINE)
        les_shelf = re.findall(r'\d$', shelfStep2, re.MULTILINE)
        if len(les_shelf) == len(tab_power):
            for i, (shelf, res) in enumerate(zip(les_shelf, output_power)):
                res = int(res) / 100
                if int(shelf) == 2:
                    tabPowerIn.append(f"{res} dBm")
                else:
                    tabPowerOut.append(f"{res} dBm")
    else:
        tabPowerIn.append("Carte pas concerné")
        tabPowerOut.append("Carte pas concerné")
    
    output_bytes_osc_out = subprocess.check_output(commandOSCsfpPowerOut, shell=True)
    output_osc_out = output_bytes_osc_out.decode('utf-8').strip()
    tab_osc_out = []
    if "INTEGER: " in output_osc_out:
        output_osc_out = re.findall(r'INTEGER: (.+)', output_osc_out, re.MULTILINE)
        res_osc_out_index = get_index(adresse_ip, oidIndex)
        for i, (res, res_index) in enumerate(zip(output_osc_out, res_osc_out_index)):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_osc_out = f"{name_index} : {int(res) /100} dBm"
            tab_osc_out.append(output_osc_out)
    
    output_bytes_osc_in = subprocess.check_output(commandOSCsfpPowerIn, shell=True)
    output_osc_in = output_bytes_osc_in.decode('utf-8').strip()
    tab_osc_in = []
    if "INTEGER: " in output_osc_in:
        output_osc_in = re.findall(r'INTEGER: (.+)', output_osc_in, re.MULTILINE)
        res_osc_in_index = get_index(adresse_ip, oidIndex)
        for i, (res, res_index) in enumerate(zip(output_osc_in, res_osc_in_index)):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_osc_in = f"{name_index} : {int(res) /100} dBm"
            tab_osc_in.append(output_osc_in)
         
    detailOpticalAmplifiers.append(tab_total_input)
    detailOpticalAmplifiers.append(tab_total_output)
    detailOpticalAmplifiers.append(tab_current_gain)   
    detailOpticalAmplifiers.append(output_temp)
    detailOpticalAmplifiers.append(output_measured_current)
    detailOpticalAmplifiers.append(output_measured_power)
    detailOpticalAmplifiers.append(tabPowerIn)
    detailOpticalAmplifiers.append(tabPowerOut)
    detailOpticalAmplifiers.append(tab_osc_out)
    detailOpticalAmplifiers.append(tab_osc_in)
    
    return detailOpticalAmplifiers

def wavelengthRouter(shelf, slot, adresse_ip):
    detailwavelengthRouter= []
    
    oidIndex = "1.3.6.1.2.1.31.1.1.1.1"
    oidTotalInputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.308.1.1"
    oidTotalOutputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.308.1.2"
    oidCurrentGain=f"1.3.6.1.4.1.7483.2.2.3.7.4.2.1.1"
    oidTemp=f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    oidMeasuredCurrent =f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.39.{shelf}.{slot}"
    oidMeasuredPower =f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.38.{shelf}.{slot}"
    oidChannelPower=f"1.3.6.1.4.1.7483.2.2.3.2.2.1.11.1.7"
    oidTotalOSCOut=f"1.3.6.1.4.1.7483.2.2.3.7.5.2.1.23"
    oidTotalOSCIn=f"1.3.6.1.4.1.7483.2.2.3.7.5.2.1.24"
    
    commandTotalInputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalInputPower}"
    commandTotalOutputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOutputPower}"
    commandCurrentGain = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidCurrentGain}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    commandMeasuredCurrent = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredCurrent}"
    commandMeasuredPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredPower}"
    commandChannelPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidChannelPower}"
    commandTotalOSCOut = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOSCOut}"
    commandTotalOSCIn = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOSCIn}"
    
    output_bytes_total_input = subprocess.check_output(commandTotalInputPower, shell=True)
    output_total_input = output_bytes_total_input.decode('utf-8').strip()
    tab_total_input = []
    if "INTEGER: " in output_total_input:
        output_total_input = re.findall(r'INTEGER: (.+)', output_total_input, re.MULTILINE)
        res_power_in_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_total_input, res_power_in_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_total_input = f"{name_index} : {int(res) /100} dBm"
            tab_total_input.append(output_total_input)
    
    output_bytes_total_output = subprocess.check_output(commandTotalOutputPower, shell=True)
    output_total_output = output_bytes_total_output.decode('utf-8').strip()
    tab_total_output = []
    if "INTEGER: " in output_total_output:
        output_total_output = re.findall(r'INTEGER: (.+)', output_total_output, re.MULTILINE)
        res_power_out_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_total_output, res_power_out_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_total_output = f"{name_index} : {int(res) /100} dBm"
            tab_total_output.append(output_total_output)
    
    output_bytes_current_gain = subprocess.check_output(commandCurrentGain, shell=True)
    output_current_gain = output_bytes_current_gain.decode('utf-8').strip()
    tab_current_gain = []
    if "Gauge32: " in output_current_gain:
        output_current_gain = re.findall(r'Gauge32: (.+)', output_current_gain, re.MULTILINE)
        res_current_gain_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_current_gain, res_current_gain_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_current_gain = f"{name_index} : {int(res) /100} dB"
            tab_current_gain.append(output_current_gain)
    
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
    detailwavelengthRouter.append(f"{output_temp} °C")
    
    output_bytes_measured_current = subprocess.check_output(commandMeasuredCurrent, shell=True)
    output_measured_current = output_bytes_measured_current.decode('utf-8').strip()
    if "Gauge32: " in output_measured_current:
        output_measured_current=output_measured_current.split("Gauge32: ", 1)[1]
        output_measured_current = int(output_measured_current)/1000
    
    output_bytes_measured_power = subprocess.check_output(commandMeasuredPower, shell=True)
    output_measured_power = output_bytes_measured_power.decode('utf-8').strip()
    if "INTEGER: " in output_measured_power:
        output_measured_power=output_measured_power.split("INTEGER: ", 1)[1]
        output_measured_power = int(output_measured_power)/1000
    
    output_bytes_channel_power_in = subprocess.check_output(commandChannelPower, shell=True)
    output_power = output_bytes_channel_power_in.decode('utf-8').strip()
    if "INTEGER: " in output_power:
        tabShelf = []
        tabPowerIn = []
        tabPowerOut = []
        res_power = re.findall(r'INTEGER: (.+)', output_power, re.MULTILINE)
        tabShelf = get_shelf(adresse_ip, oidIndex)
        for i, (shelf,test) in enumerate(zip(tabShelf,res_power)):
            test = int(test)/100
            if int(shelf) == 2:
                tabPowerIn.append(f"{test} dBm")
            else:
                tabPowerOut.append(f"{test} dBm")
                
    output_bytes_osc_out = subprocess.check_output(commandTotalOSCOut, shell=True)
    output_osc_out = output_bytes_osc_out.decode('utf-8').strip()
    tab_osc_out = []
    if "INTEGER: " in output_osc_out:
        output_osc_out = re.findall(r'INTEGER: (.+)', output_osc_out, re.MULTILINE)
        res_osc_out_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_osc_out, res_osc_out_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_osc_out = f"{name_index} : {int(res) /100} dBm"
            tab_osc_out.append(output_osc_out)
    
    output_bytes_osc_in = subprocess.check_output(commandTotalOSCIn, shell=True)
    output_osc_in = output_bytes_osc_in.decode('utf-8').strip()
    tab_osc_in = []
    if "INTEGER: " in output_osc_in:
        output_osc_in = re.findall(r'INTEGER: (.+)', output_osc_in, re.MULTILINE)
        res_osc_in_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(output_osc_in, res_osc_in_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            output_osc_in = f"{name_index} : {int(res) /100} dBm"
            tab_osc_in.append(output_osc_in)

    detailwavelengthRouter.append(tab_total_input)
    detailwavelengthRouter.append(tab_total_output)
    detailwavelengthRouter.append(tab_current_gain)
    detailwavelengthRouter.append(f"{output_temp} °C")
    detailwavelengthRouter.append(f"{output_measured_current} Amp")
    detailwavelengthRouter.append(f"{output_measured_power} Watt")
    detailwavelengthRouter.append(tabPowerIn)
    detailwavelengthRouter.append(tabPowerOut)
    detailwavelengthRouter.append(tab_osc_out)
    detailwavelengthRouter.append(tab_osc_in)
    return detailwavelengthRouter

def RA2P(shelf, slot, adresse_ip):
    detailRA2P= []
    oidIndex = "1.3.6.1.2.1.31.1.1.1.1"
    oidTotalInputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.144.1.1"
    oidTotalOutputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.144.1.2"
    oidCurrentGain=f"1.3.6.1.4.1.7483.2.2.3.7.4.2.1.1"
    oidTemp=f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    oidMeasuredCurrent =f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.39.{shelf}.{slot}"
    oidMeasuredPower =f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.38.{shelf}.{slot}"
    commandTotalInputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalInputPower}"
    commandTotalOutputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOutputPower}"
    commandCurrentGain = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidCurrentGain}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    commandMeasuredCurrent = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredCurrent}"
    commandMeasuredPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredPower}"
    
    output_bytes_total_input = subprocess.check_output(commandTotalInputPower, shell=True)
    output_total_input = output_bytes_total_input.decode('utf-8').strip()
    if "INTEGER: " in output_total_input:
        tabTotalIn =[]
        res_power_in = re.findall(r'INTEGER: (.+)', output_total_input, re.MULTILINE)
        res_power_in_index = get_index(adresse_ip, oidIndex)
        for (res, res_index) in zip(res_power_in, res_power_in_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            final_res_tin = f"{name_index} : {int(res) /100} dBm"
            tabTotalIn.append(final_res_tin)
    detailRA2P.append(tabTotalIn)
    
    output_bytes_total_output = subprocess.check_output(commandTotalOutputPower, shell=True)
    output_total_output = output_bytes_total_output.decode('utf-8').strip()
    if "INTEGER: " in output_total_output:
        tabTotalOut =[]
        res_power_out = re.findall(r'INTEGER: (.+)', output_total_output, re.MULTILINE)
        res_power_out_index = get_index()
        for (res, res_index) in zip(res_power_out, res_power_out_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            final_res_tout = f"{name_index} : {int(res) /100} dBm"
            tabTotalOut.append(final_res_tout)
    detailRA2P.append(tabTotalOut)
    
    output_bytes_current_gain = subprocess.check_output(commandCurrentGain, shell=True)
    output_current_gain = output_bytes_current_gain.decode('utf-8').strip()
    if "Gauge32: " in output_current_gain:
        tabCurrentGain =[]
        res_current_gain = re.findall(r'Gauge32: (.+)', output_current_gain, re.MULTILINE)
        res_current_gain_index = get_index()
        for (res, res_index) in zip(res_current_gain, res_current_gain_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            final_res_cugain = f"{name_index} : {int(res) /100} dB"
            tabCurrentGain.append(final_res_cugain)
        detailRA2P.append(tabCurrentGain)
    
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
    detailRA2P.append(f"{output_temp} °C")
    
    output_bytes_measured_current = subprocess.check_output(commandMeasuredCurrent, shell=True)
    output_measured_current = output_bytes_measured_current.decode('utf-8').strip()
    if "Gauge32: " in output_measured_current:
        output_measured_current=output_measured_current.split("Gauge32: ", 1)[1]
        output_measured_current = int(output_measured_current)/1000
    detailRA2P.append(f"{output_measured_current} Amp")
    
    output_bytes_measured_power = subprocess.check_output(commandMeasuredPower, shell=True)
    output_measured_power = output_bytes_measured_power.decode('utf-8').strip()
    if "INTEGER: " in output_measured_power:
        output_measured_power=output_measured_power.split("INTEGER: ", 1)[1]
        output_measured_power = int(output_measured_power)/1000
    detailRA2P.append(f"{output_measured_power} Watt")
    
    return detailRA2P

def AAR8A(shelf, slot, adresse_ip):
    detailAAR8A= []
    oidIndex = "1.3.6.1.2.1.31.1.1.1.1"
    oidTotalInputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.280.1.1"
    oidTotalOutputPower=f"1.3.6.1.4.1.7483.2.2.4.3.5.280.1.5"
    oidTemp=f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    commandTotalInputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalInputPower}"
    commandTotalOutputPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTotalOutputPower}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    # getNameIndex= WDMManagerNokia(self.adresse_ip, oidIndex)

    output_bytes_total_input = subprocess.check_output(commandTotalInputPower, shell=True)
    output_total_input = output_bytes_total_input.decode('utf-8').strip()
    # getIndex= WDMManagerNokia(self.adresse_ip, oidTotalInputPower)
    if "INTEGER: " in output_total_input:
        tabTotalIn =[]
        res_power_in = re.findall(r'INTEGER: (.+)', output_total_input, re.MULTILINE)
        res_power_in_index = get_index()
        for (res, res_index) in zip(res_power_in, res_power_in_index):
            res_index = int(res_index)
            name_index =get_index_name(res_index, adresse_ip, oidIndex)
            final_res_tin = f"{name_index} : {int(res) /100} dBm"
            tabTotalIn.append(final_res_tin)
    detailAAR8A.append(tabTotalIn)
    output_bytes_total_output = subprocess.check_output(commandTotalOutputPower, shell=True)
    output_total_output = output_bytes_total_output.decode('utf-8').strip()
    # getIndex= WDMManagerNokia(self.adresse_ip, oidTotalOutputPower)
    if "INTEGER: " in output_total_output:
        tabTotalOut = []
        res_power_out = re.findall(r'INTEGER: (.+)', output_total_output, re.MULTILINE)
        res_power_out_index = get_index()
        for (res, res_index) in zip(res_power_out, res_power_out_index):
            res_index = int(res_index)
            name_index = get_index_name(res_index, adresse_ip, oidIndex)
            final_res_tout = f"{name_index} : {int(res) /100} dBm"
            tabTotalOut.append(final_res_tout)
    detailAAR8A.append(tabTotalOut)
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
    detailAAR8A.append(f"{output_temp} °C")
    return detailAAR8A

def ControllerCards(shelf, slot, adresse_ip):
    detailController= []
    oidTemp=f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    oidMeasuredCurrent =f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.39.{shelf}.{slot}"
    oidMeasuredPower =f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.38.{shelf}.{slot}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    commandMeasuredCurrent = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredCurrent}"
    commandMeasuredPower = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidMeasuredPower}"
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
    detailController.append(f"{output_temp} °C")
    output_bytes_measured_current = subprocess.check_output(commandMeasuredCurrent, shell=True)
    output_measured_current = output_bytes_measured_current.decode('utf-8').strip()
    if "Gauge32: " in output_measured_current:
        output_measured_current=output_measured_current.split("Gauge32: ", 1)[1]
        output_measured_current = int(output_measured_current)/1000
    detailController.append(f"{output_measured_current} Amp")
    
    output_bytes_measured_power = subprocess.check_output(commandMeasuredPower, shell=True)
    output_measured_power = output_bytes_measured_power.decode('utf-8').strip()
    if "INTEGER: " in output_measured_power:
        output_measured_power=output_measured_power.split("INTEGER: ", 1)[1]
        output_measured_power = int(output_measured_power)/1000
    detailController.append(f"{output_measured_power} Watt")
    return detailController

def Autre(shelf, slot, adresse_ip):
    detailAutre= []
    oidTemp=f"1.3.6.1.4.1.7483.2.2.3.1.2.1.2.1.13.{shelf}.{slot}"
    commandTemp = f"snmpwalk -v2c -c cpdea {adresse_ip} {oidTemp}"
    output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
    output_temp = output_bytes_temp.decode('utf-8').strip()
    if "INTEGER: " in output_temp:
        output_temp=output_temp.split("INTEGER: ", 1)[1]
    detailAutre.append(f"{output_temp} °C")
    return detailAutre
