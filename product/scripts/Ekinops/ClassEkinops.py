import math

import subprocess
from scripts.ClassConversion import convert
from scripts.SSH import *


# def get_type_chassis(adresse_ip, oidChassis):
#     oidC = f"{oidChassis}"
#     command = f"snmpget -v2c -c cpdea {adresse_ip} {oidC}"
#     output_bytes = subprocess.check_output(command, shell=True)
#     output_text = output_bytes.decode('utf-8').strip()
#     if "," in output_text:
#         chassis=output_text.split(',', 1)[1].split(',', 1)[0].strip()
#     else:
#         chassis=output_text
#     return chassis   

def get_card_types(adresse_ip, oidType):
    card_types = []
    i=0
    verif = True
    while verif:
        oidT = f"{oidType}.{i}"
        command = f"snmpget -v2c -c cpdea {adresse_ip} {oidT}"
        try:
            output_bytes = subprocess.check_output(command, shell=True)
            output_text = output_bytes.decode('utf-8').strip()
            if "No Such Instance" in output_text:
                verif = False
            else:
                if "STRING: " in output_text:
                    output_text=output_text.split("STRING: ", 1)[1]
                    output_text = output_text.strip('""')
                card_types.append(output_text)
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return card_types if card_types else None

def get_card_slot(adresse_ip, oidSlot):
    card_slots = []
    i=0
    verif = True
    while verif:
        oidS = f"{oidSlot}.{i}"
        command = f"snmpget -v2c -c cpdea {adresse_ip} {oidS}"
        try:
            output_bytes = subprocess.check_output(command, shell=True)
            output_text = output_bytes.decode('utf-8').strip()
            if "No Such Instance" in output_text:
                verif = False
            else:
                if "INTEGER: " in output_text:
                    output_text=output_text.split("INTEGER: ", 1)[1]
                card_slots.append(output_text)
                i += 1
                
        except subprocess.CalledProcessError:
            verif = False
    return card_slots if card_slots else None

def get_version(host):
    command = f"snmpget -v2c -c cpdea {host} 1.3.6.1.2.1.1.1.0"
    output_bytes = subprocess.check_output(command, shell=True)
    output_text = output_bytes.decode('utf-8').strip()
    if "No Such Instance" in output_text:
        verif = False
    else:
        if "Release" in output_text:
            output_text=output_text.split("Release", 1)[1]   
    return output_text
    
def emuxClient(communaute, adresse_ip):
    tabPorts={}
    verif=True
    i=0
    while verif:
        oidTemp=f"1.3.6.1.4.1.20044.107.3.2.16.1.2.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.107.3.2.112.1.2.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.107.3.2.80.1.2.{i}"
        oidTrafficIn =f"1.3.6.1.4.1.20044.107.11.2.4.16.1.2.{i}"
        oidTrafficOut =f"1.3.6.1.4.1.20044.107.11.2.4.400.1.2.{i}"
        oidInputCrc =f"1.3.6.1.4.1.20044.107.11.2.4.48.1.2.{i}"
        oidOutputCrc =f"1.3.6.1.4.1.20044.107.11.2.4.432.1.2.{i}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        commandTrafficIn = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficIn}"
        commandTrafficOut = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficOut}"
        commandInputCRC = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidInputCrc}"
        commandOutputCRC = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidOutputCrc}"
        numPort=i+1
        if numPort not in tabPorts:
            tabPorts[numPort] = []
        port_list = tabPorts[numPort]
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_Temp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such Instance" in output_Temp:
                verif = False
            else:
                if "INTEGER: " in output_Temp:
                    output_Temp=output_Temp.split("INTEGER: ", 1)[1]
                    output_Temp=float(output_Temp) / 256
                    output_Temp=round(output_Temp, 2)
                    port_list.append(f"{output_Temp} °C")
                output_bytes_RXP = subprocess.check_output(commandRXPower, shell=True)
                output_RXP = output_bytes_RXP.decode('utf-8').strip()
                if "INTEGER" in output_RXP:
                    output_RXP=output_RXP.split("INTEGER: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0 
                    port_list.append(f"{output_RXP} dBm")
                output_bytes_TXP = subprocess.check_output(commandTXPower, shell=True)
                output_TXP = output_bytes_TXP.decode('utf-8').strip()
                if "INTEGER" in output_TXP:
                    output_TXP=output_TXP.split("INTEGER: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                    port_list.append(f"{output_TXP} dBm")
                output_bytes_TIN = subprocess.check_output(commandTrafficIn, shell=True)
                output_TIN = output_bytes_TIN.decode('utf-8').strip()
                if "Counter64" in output_TIN:
                    output_TIN=output_TIN.split("Counter64: ", 1)[1]
                    output_TIN=int(output_TIN)
                    convertTool= convert(output_TIN)
                    output_TIN=convertTool.converterOctalToBits()
                    port_list.append(output_TIN)
                output_bytes_TOUT = subprocess.check_output(commandTrafficOut, shell=True)
                output_TOUT = output_bytes_TOUT.decode('utf-8').strip()
                if "Counter64" in output_TOUT:
                    output_TOUT=output_TOUT.split("Counter64: ", 1)[1]
                    output_TOUT=int(output_TOUT)
                    convertTool= convert(output_TOUT)
                    output_TOUT=convertTool.converterOctalToBits()
                    port_list.append(output_TOUT)
                output_bytes_input_crc = subprocess.check_output(commandInputCRC, shell=True)
                output_input_crc = output_bytes_input_crc.decode('utf-8').strip()
                if "Counter64" in output_input_crc:
                    output_input_crc=output_input_crc.split("Counter64: ", 1)[1]
                    port_list.append(output_input_crc)
                output_bytes_output_crc = subprocess.check_output(commandOutputCRC, shell=True)
                output_output_crc = output_bytes_output_crc.decode('utf-8').strip()
                if "Counter64" in output_output_crc:
                    output_output_crc=output_output_crc.split("Counter64: ", 1)[1]
                    port_list.append(output_output_crc)
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPorts
                
def emuxLine(communaute, adresse_ip):
    detailEmuxLine=[]
    oidLineTemp = "1.3.6.1.4.1.20044.107.3.3.12"
    oidLineErrors = "1.3.6.1.4.1.20044.107.4.3.192.1.2"
    oidLineRxAvg = "1.3.6.1.4.1.20044.107.3.3.192.1.2"
    oidLineTxAvg = "1.3.6.1.4.1.20044.107.3.3.160.1.2"
    commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
    commandLineErrors = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineErrors}"
    commandLineRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxAvg}"
    commandLineTxAvg = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxAvg}"
    output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
    output_line_temp = output_bytes_LineTemp.decode('utf-8').strip()
    if "Gauge32: " in output_line_temp:
        output_line_temp=output_line_temp.split("Gauge32: ", 1)[1]
        output_line_temp=float(output_line_temp) / 256
        output_line_temp = round(output_line_temp, 2)
        detailEmuxLine.append(f"{output_line_temp}°C")
    output_bytes_errors = subprocess.check_output(commandLineErrors, shell=True)
    output_errors = output_bytes_errors.decode('utf-8').strip()
    if "Counter64" in output_errors:
        output_errors=output_errors.split("Counter64: ", 1)[1]
        detailEmuxLine.append(f"{output_errors}")
    output_bytes_RXPower = subprocess.check_output(commandLineRxPower, shell=True)
    output_RXPower = output_bytes_RXPower.decode('utf-8').strip()
    if "INTEGER" in output_RXPower:
        output_RXPower=output_RXPower.split("INTEGER: ", 1)[1]
        output_RXPower = float(output_RXPower)
        if output_RXPower > 0:
            output_RXPower=round((10 * math.log10(output_RXPower)-40))
        detailEmuxLine.append(f"{output_RXPower} dBm")
    output_bytes_TXAVG = subprocess.check_output(commandLineTxAvg, shell=True)
    output_TXAVG = output_bytes_TXAVG.decode('utf-8').strip()
    if "INTEGER" in output_TXAVG:
        output_TXAVG=output_TXAVG.split("INTEGER: ", 1)[1]
        output_TXAVG = float(output_TXAVG)
        if output_TXAVG > 0:
            output_TXAVG=round((10 * math.log10(output_TXAVG)-40))
        detailEmuxLine.append(f"{output_TXAVG} dBm")
    return detailEmuxLine

def ClientFRS02(communaute, adresse_ip):
    tabPortsFRS02={}
    verif=True 
    i=0
    while verif:
        oidAvgRxPower = f"1.3.6.1.4.1.20044.90.3.2.288.1.2.{i}"
        oidAvgTxPower = f"1.3.6.1.4.1.20044.90.3.2.256.1.2.{i}"
        oidTrafficIn = f"1.3.6.1.4.1.20044.90.11.2.4.16.1.2.{i}"
        oidtrafficOut = f"1.3.6.1.4.1.20044.90.11.2.4.400.1.2.{i}"
        oidInputCRC = f"1.3.6.1.4.1.20044.90.11.2.4.48.1.2.{i}"
        oidOutputCRC = f"1.3.6.1.4.1.20044.90.11.2.4.432.1.2.{i}"
        
        commandAvgRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidAvgRxPower}"
        commandAvgTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidAvgTxPower}"
        commandTrafficIn = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficIn}"
        commandTrafficOut = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidtrafficOut}"
        commandInputCrc = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidInputCRC}"
        commandOutputCrc = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidOutputCRC}"
        numPort=i+1
        if numPort not in tabPortsFRS02:
            tabPortsFRS02[numPort] = []
        port_list = tabPortsFRS02[numPort]
        output_bytes_AVGRX = subprocess.check_output(commandAvgRXPower, shell=True)
        output_AVGRX = output_bytes_AVGRX.decode('utf-8').strip()
        try:
            if "No Such" in output_AVGRX:
                verif = False
            else:
                if "INTEGER: " in output_AVGRX:
                    output_AVGRX=output_AVGRX.split("INTEGER: ", 1)[1]
                    output_AVGRX=float(output_AVGRX)
                    if output_AVGRX > 0:
                        output_AVGRX=round((10 * math.log10(output_AVGRX)-40))
                port_list.append(f"{output_AVGRX} dBm")
                output_bytes_AVGTX = subprocess.check_output(commandAvgTXPower, shell=True)
                output_AVGTX = output_bytes_AVGTX.decode('utf-8').strip()
                if "INTEGER" in output_AVGTX:
                    output_AVGTX=output_AVGTX.split("INTEGER: ", 1)[1]
                    output_AVGTX=float(output_AVGTX)
                    if output_AVGTX > 0:
                        output_AVGTX=round((10 * math.log10(output_AVGTX)-40))
                port_list.append(f"{output_AVGTX} dBm")
                output_bytes_Input = subprocess.check_output(commandInputCrc, shell=True)
                output_Input = output_bytes_Input.decode('utf-8').strip()
                if "Counter64" in output_Input: 
                    output_Input=output_Input.split("Counter64: ", 1)[1]
                    
                port_list.append(output_Input)
                output_bytes_Output = subprocess.check_output(commandOutputCrc, shell=True)
                output_Output = output_bytes_Output.decode('utf-8').strip()
                if "Counter64" in output_Output:
                    output_Output=output_Output.split("Counter64: ", 1)[1]
                port_list.append(output_Output)
                output_bytes_traffic_in = subprocess.check_output(commandTrafficIn, shell=True)
                output_traffic_in = output_bytes_traffic_in.decode('utf-8').strip()
                if "Counter64" in output_traffic_in: 
                    output_traffic_in=output_traffic_in.split("Counter64: ", 1)[1]
                    output_traffic_in=int(output_traffic_in)
                    convertTool= convert(output_traffic_in)
                    output_traffic_in=convertTool.converterOctalToBits()
                port_list.append(output_traffic_in)
                output_bytes_traffic_out = subprocess.check_output(commandTrafficOut, shell=True)
                output_traffic_out = output_bytes_traffic_out.decode('utf-8').strip()
                if "Counter64" in output_traffic_out: 
                    output_traffic_out=output_traffic_out.split("Counter64: ", 1)[1]
                    output_traffic_out=int(output_traffic_out)
                    convertTool= convert(output_traffic_out)
                    output_traffic_out=convertTool.converterOctalToBits()
                port_list.append(output_traffic_out)
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    
    return tabPortsFRS02

def LineFRS02 (communaute, adresse_ip):
    detailFRS02Line=[]
    oidLineTemp = "1.3.6.1.4.1.20044.90.3.3.12"
    oidLineErrors = "1.3.6.1.4.1.20044.90.4.3.192.1.2"
    oidLineRxPower = "1.3.6.1.4.1.20044.90.3.3.156.1.2"
    oidLineTxPower = "1.3.6.1.4.1.20044.90.3.3.144.1.2"
    oidTemp1 = f"1.3.6.1.4.1.20044.90.3.1.252"
    oidTemp2 = f"1.3.6.1.4.1.20044.90.3.1.253"
    commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
    commandLineErrors = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineErrors}"
    commandRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxPower}"
    commandTxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxPower}"
    commandTemp1 = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp1}"
    commandTemp2 = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp2}"
    output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
    output_LineTemp = output_bytes_LineTemp.decode('utf-8').strip()
    if "Gauge32: " in output_LineTemp:
        output_LineTemp=output_LineTemp.split("Gauge32: ", 1)[1]
        output_LineTemp=float(output_LineTemp) / 256 
        output_LineTemp=round(output_LineTemp,2)
        detailFRS02Line.append(f"{output_LineTemp} °C")
    output_bytes_errors = subprocess.check_output(commandLineErrors, shell=True)
    output_errors = output_bytes_errors.decode('utf-8').strip()
    if "Counter64" in output_errors:
        output_errors=output_errors.split("Counter64: ", 1)[1]
        detailFRS02Line.append(f"{output_errors}")
    output_bytes_RXPower = subprocess.check_output(commandRxPower, shell=True)
    output_RXPower = output_bytes_RXPower.decode('utf-8').strip()
    if "INTEGER" in output_RXPower:
        output_RXPower=output_RXPower.split("INTEGER: ", 1)[1]
        output_RXPower = float(output_RXPower)
        if output_RXPower < 32768 :
            output_RXPower = output_RXPower / 100
        else:
            output_RXPower = (output_RXPower-65536)/100
    detailFRS02Line.append(f"{output_RXPower} dBm")
    output_bytes_TXPower = subprocess.check_output(commandTxPower, shell=True)
    output_TXPower = output_bytes_TXPower.decode('utf-8').strip()
    if "INTEGER" in output_TXPower:
        output_TXPower=output_TXPower.split("INTEGER: ", 1)[1]
        output_TXPower = float(output_TXPower)
        if output_TXPower < 32768 :
            output_TXPower = output_TXPower / 100
        else:
            output_TXPower = (output_TXPower-65536)/100
    detailFRS02Line.append(f"{output_TXPower} dBm")
    output_bytes_tempPort1 = subprocess.check_output(commandTemp1, shell=True)
    output_temp1 = output_bytes_tempPort1.decode('utf-8').strip()
    if "Gauge32: " in output_temp1:
        output_temp1=output_temp1.split("Gauge32: ", 1)[1]
        output_temp1=float(output_temp1) / 256 
        output_temp1=round(output_temp1,2)
    detailFRS02Line.append(f"{output_temp1} °C")
    output_bytes_tempPort2 = subprocess.check_output(commandTemp2, shell=True)
    output_temp2 = output_bytes_tempPort2.decode('utf-8').strip()
    if "Gauge32: " in output_temp2:
        output_temp2=output_temp2.split("Gauge32: ", 1)[1]
        output_temp2=float(output_temp2) / 256 
        output_temp2=round(output_temp2,2)
    detailFRS02Line.append(f"{output_temp2} °C")
    return detailFRS02Line
    
def clientOABP_HCS(communaute, adresse_ip):
    tabPortsOABP={}
    verif=True 
    i=0
    while verif:
        oidTemp = f"1.3.6.1.4.1.20044.61.3.1.80.{i}"
        oidBoosterRx = f"1.3.6.1.4.1.20044.61.3.3.50.{i}"
        oidBoosterTx = f"1.3.6.1.4.1.20044.61.3.3.49.{i}"
        oidBoosterGain = f"1.3.6.1.4.1.20044.61.3.3.54.{i}"
        oidPumpLaser = f"1.3.6.1.4.1.20044.61.3.3.48.{i}"
        oidPreAmpRx = f"1.3.6.1.4.1.20044.61.3.2.34.{i}"
        oidPreAmpTx = f"1.3.6.1.4.1.20044.61.3.2.33.{i}"
        oidPreAmpGain = f"1.3.6.1.4.1.20044.61.3.2.38.{i}"
        oidPreAmpPump = f"1.3.6.1.4.1.20044.61.3.2.32.{i}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandBRX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterRx}"
        commandBTX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterTx}"
        commandBoosterGain = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterGain}"
        commandPumpLaser = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPumpLaser}"
        commandPARX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpRx}"
        commandPATX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpTx}"
        commandPreAmpGain = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpGain}"
        commandPreAmpPump = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpPump}"
        numPort=i+1
        if numPort not in tabPortsOABP:
            tabPortsOABP[numPort] = []
        port_list = tabPortsOABP[numPort]
        
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_temp_oabp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such" in output_temp_oabp:
                verif = False
            else:
                if "INTEGER" in output_temp_oabp:
                    output_temp_oabp=output_temp_oabp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_temp_oabp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                port_list.append(f"{temperature} °C")
                output_bytes_BRX = subprocess.check_output(commandBRX, shell=True)
                output_BRX = output_bytes_BRX.decode('utf-8').strip()
                if "INTEGER" in output_BRX:
                    output_BRX=output_BRX.split("INTEGER: ", 1)[1]
                    output_BRX=round(((float(output_BRX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_BRX} dBm")
                output_bytes_BTX = subprocess.check_output(commandBTX, shell=True)
                output_BTX = output_bytes_BTX.decode('utf-8').strip()
                if "INTEGER" in output_BTX:
                    output_BTX=output_BTX.split("INTEGER: ", 1)[1]
                    output_BTX=round(((float(output_BTX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_BTX} dBm")
                output_bytes_gain = subprocess.check_output(commandBoosterGain, shell=True)
                output_gain = output_bytes_gain.decode('utf-8').strip()
                if "INTEGER" in output_gain:
                    output_gain=output_gain.split("INTEGER: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_gain:
                    output_gain=output_gain.split("Gauge32: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                elif "Counter64" in output_gain:
                    output_gain=output_gain.split("Counter64: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                port_list.append(f"{output_gain} dB")
                output_bytes_pump_laser = subprocess.check_output(commandPumpLaser, shell=True)
                output_pump_laser = output_bytes_pump_laser.decode('utf-8').strip()
                if "INTEGER" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("INTEGER: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                elif "Gauge32" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("Gauge32: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                elif "Counter64" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("Counter64: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                port_list.append(f"{output_pump_laser} mA")
                output_bytes_PARX = subprocess.check_output(commandPARX, shell=True)
                output_PARX = output_bytes_PARX.decode('utf-8').strip()
                if "INTEGER" in output_PARX:
                    output_PARX=output_PARX.split("INTEGER: ", 1)[1]
                    output_PARX=round(((float(output_PARX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_PARX} dBm")
                output_bytes_PATX = subprocess.check_output(commandPATX, shell=True)
                output_PATX = output_bytes_PATX.decode('utf-8').strip()
                if "INTEGER" in output_PATX:
                    output_PATX=output_PATX.split("INTEGER: ", 1)[1]
                    output_PATX=round(((float(output_PATX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_PATX} dBm")
                output_bytes_preamp_gain = subprocess.check_output(commandPreAmpGain, shell=True)
                output_preamp_gain = output_bytes_preamp_gain.decode('utf-8').strip()
                if "INTEGER" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("INTEGER: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("Gauge32: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                elif "Counter64" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("Counter64: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                port_list.append(f"{output_preamp_gain} dB")
                
                output_bytes_preamp_pump_laser = subprocess.check_output(commandPreAmpPump, shell=True)
                output_pump_preamp_laser = output_bytes_preamp_pump_laser.decode('utf-8').strip()
                if "INTEGER" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("INTEGER: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                elif "Gauge32" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("Gauge32: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                elif "Counter64" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("Counter64: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                port_list.append(f"{output_pump_preamp_laser} mA")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPortsOABP

def OPM8(communaute, adresse_ip):
    tabPortsOpm8 = []
    i = 0
    while i < 8:
        oidPowerInput= f"1.3.6.1.4.1.20044.66.3.2.784.1.2.{i}"
        commandPowerInput = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPowerInput}"
        
        
        output_bytes_power_input = subprocess.check_output(commandPowerInput, shell=True)
        output_power_input = output_bytes_power_input.decode('utf-8').strip()
        
        if "INTEGER: " in output_power_input:
            output_power_input = output_power_input.split("INTEGER: ", 1)[1]
            output_power_input=float(output_power_input)
            if output_power_input < 32768:
                output_power_input = float(output_power_input) / 256
            else:
                output_power_input = (output_power_input / 256) - 256
            output_power_input = round(output_power_input, 2)
        tabPortsOpm8.append(f"{output_power_input} dBm")
        i += 1
    return tabPortsOpm8

def OPM8ChannelPower(communaute, adresse_ip):
    tabPortsOpm8 = {}
    i = 0
    while i < 9:
        iPower = 16
        oidTemp = "1.3.6.1.4.1.20044.66.3.1.808"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_temp = output_bytes_temp.decode('utf-8').strip()
            
        if "Gauge32: " in output_temp:
            output_temp = output_temp.split("Gauge32: ", 1)[1]
            temperature = float(output_temp) / 256
            temperature = round(temperature, 2)
            
        while iPower < 777:
            oidChannelPower = f"1.3.6.1.4.1.20044.66.3.2.{iPower}.1.2.{i}"
            commandChannelPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidChannelPower}"
            output_bytes_chan_power = subprocess.check_output(commandChannelPower, shell=True)
            output_chan_power = output_bytes_chan_power.decode('utf-8').strip()
            numPort = iPower
            if numPort not in tabPortsOpm8:
                tabPortsOpm8[numPort] = []
            port_list = tabPortsOpm8[numPort] 
            
            port_list.append(f"{temperature} °C")
            
            output_bytes_chan_power = subprocess.check_output(commandChannelPower, shell=True)
            output_chan_power = output_bytes_chan_power.decode('utf-8').strip()
            
            if "No Such" in output_chan_power:
                output_chan_power = "Pas ici"
            else:
                output_chan_power = output_chan_power.split("INTEGER: ", 1)[1]
                output_chan_power = float(output_chan_power)
                
                if output_chan_power < 32768:
                    output_chan_power = output_chan_power / 256
                else:
                    output_chan_power = (output_chan_power / 256) - 256
                output_chan_power = round(output_chan_power, 2)
            
            port_list.append(f"{output_chan_power} dBm")
            iPower += 1
        i += 1
    return tabPortsOpm8

def OTDR(communaute, adresse_ip):
    tabPortsOtdr={}
    verif=True 
    i=0 
    while verif:
        oidTemp=f"1.3.6.1.4.1.20044.95.3.3.28.1.2.{i}"
        oidRxPower=f"1.3.6.1.4.1.20044.95.3.3.36.1.2.{i}"
        oidTxPower=f"1.3.6.1.4.1.20044.95.3.3.32.1.2.{i}"
        oidFaultDistance=f"1.3.6.1.4.1.20044.95.3.3.20.1.2.{i}"
        commandTempOtdr = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandRX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"  
        commandFaultDistance = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidFaultDistance}"    
        numPort=i+1
        if numPort not in tabPortsOtdr:
            tabPortsOtdr[numPort] = []
        port_list = tabPortsOtdr[numPort]
        output_bytes_tempOtdr = subprocess.check_output(commandTempOtdr, shell=True)
        output_tempOtdr = output_bytes_tempOtdr.decode('utf-8').strip()
        try:
            if "No Such" in output_tempOtdr:
                verif = False
            else:
                if "INTEGER: " in output_tempOtdr:
                    output_tempOtdr = output_tempOtdr.split("INTEGER: ", 1)[1]
                    output_tempOtdr=float(output_tempOtdr) / 256
                    port_list.append(f"{round(output_tempOtdr, 2)} °C")           
                output_bytes_RX = subprocess.check_output(commandRX, shell=True)
                output_RX = output_bytes_RX.decode('utf-8').strip()
                if "INTEGER" in output_RX:
                    output_RX=output_RX.split("INTEGER: ", 1)[1]
                    output_RX = float(output_RX)
                    if output_RX > 0:
                        output_RX=round((10 * math.log10(output_RX)-40), 2)
                    port_list.append(f"{output_RX} dBm")
                output_bytes_TX = subprocess.check_output(commandTX, shell=True)
                output_TX = output_bytes_TX.decode('utf-8').strip()
                if "INTEGER" in output_TX:
                    output_TX=output_TX.split("INTEGER: ", 1)[1]
                    output_TX = float(output_TX)
                    if output_TX > 0:
                        output_TX=round((10 * math.log10(output_TX)-40), 2)
                    port_list.append(f"{output_TX} dBm")
                output_bytes_fault = subprocess.check_output(commandFaultDistance, shell=True)
                output_fault = output_bytes_fault.decode('utf-8').strip()
                if "INTEGER" in output_fault:
                    output_fault=output_fault.split("INTEGER: ", 1)[1]
                    output_fault = float(output_fault)
                    if output_fault > 0:
                        output_fault=round(output_fault*2, 2)
                    port_list.append(f"{output_fault} m")
                    i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPortsOtdr

def c1008mplhClient(communaute, adresse_ip):
    tabPorts={}
    verif=True
    i=0
    while verif:
        oidTemp=f"1.3.6.1.4.1.20044.47.3.2.16.1.2.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.47.3.2.48.1.2.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.47.3.2.40.1.2.{i}"
        oidTrafficIn =f"1.3.6.1.4.1.20044.47.11.2.4.16.1.2.{i}"
        oidInputError =f"1.3.6.1.4.1.20044.47.4.2.32.1.2.{i}"
        oidOutputError =f"1.3.6.1.4.1.20044.47.4.2.64.1.2.{i}"
        oidLineTemp = f"1.3.6.1.4.1.20044.47.3.3.208.1.2.{i}"
        oidLineErrors = f"1.3.6.1.4.1.20044.47.4.3.152.1.2.{i}"
        oidLineRxPower = f"1.3.6.1.4.1.20044.47.3.3.212.1.2.{i}"
        oidLineTxPower = f"1.3.6.1.4.1.20044.47.3.3.211.1.2.{i}"
        commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
        commandLineErrors = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineErrors}"
        commandLineRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxPower}"
        commandLineTxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxPower}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        commandTrafficIn = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficIn}"
        commandInputError = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidInputError}"
        commandOutputError = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidOutputError}"
        numPort=i+1
        if numPort not in tabPorts:
            tabPorts[numPort] = []
        port_list = tabPorts[numPort]
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_Temp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such" in output_Temp:
                verif = False
            else:
                if "INTEGER: " in output_Temp:
                    output_Temp=output_Temp.split("INTEGER: ", 1)[1]
                    output_Temp=float(output_Temp) / 256
                    output_Temp=round(output_Temp, 2)
                port_list.append(f"{output_Temp} °C")
                output_bytes_RXP = subprocess.check_output(commandRXPower, shell=True)
                output_RXP = output_bytes_RXP.decode('utf-8').strip()
                if "INTEGER" in output_RXP:
                    output_RXP=output_RXP.split("INTEGER: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0 
                port_list.append(f"{output_RXP} dBm")
                output_bytes_TXP = subprocess.check_output(commandTXPower, shell=True)
                output_TXP = output_bytes_TXP.decode('utf-8').strip()
                if "INTEGER" in output_TXP:
                    output_TXP=output_TXP.split("INTEGER: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                port_list.append(f"{output_TXP} dBm")
                output_bytes_TIN = subprocess.check_output(commandTrafficIn, shell=True)
                output_TIN = output_bytes_TIN.decode('utf-8').strip()
                if "Counter64" in output_TIN:
                    output_TIN=output_TIN.split("Counter64: ", 1)[1]
                    output_TIN=int(output_TIN)
                    convertTool= convert(output_TIN)
                    output_TIN=convertTool.converterOctalToBits()
                port_list.append(output_TIN)
                output_bytes_InError = subprocess.check_output(commandInputError, shell=True)
                output_InError = output_bytes_InError.decode('utf-8').strip()
                if "Gauge32" in output_InError:
                    output_InError=output_InError.split("Gauge32: ", 1)[1]
                port_list.append(output_InError)
                output_bytes_OutError = subprocess.check_output(commandOutputError, shell=True)
                output_OutError = output_bytes_OutError.decode('utf-8').strip()
                if "Gauge32" in output_OutError:
                    output_OutError=output_OutError.split("Gauge32: ", 1)[1]
                port_list.append(output_OutError)
                output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
                output_line_temp = output_bytes_LineTemp.decode('utf-8').strip()
                if "No Such Instance" in output_line_temp:
                        output_line_temp = "Pas sur ce port"
                elif "INTEGER: " in output_line_temp:
                    output_line_temp=output_line_temp.split("INTEGER: ", 1)[1]
                    output_line_temp=float(output_line_temp) / 256
                    output_line_temp = round(output_line_temp, 2)
                port_list.append(f"{output_line_temp}°C")
                output_bytes_errors = subprocess.check_output(commandLineErrors, shell=True)
                output_errors = output_bytes_errors.decode('utf-8').strip()
                if "No Such Instance" in output_errors:
                        output_errors = "Pas sur ce port"
                elif "Gauge32" in output_errors:
                    output_errors=output_errors.split("Gauge32: ", 1)[1]
                port_list.append(f"{output_errors}")
                output_bytes_RXAVG = subprocess.check_output(commandLineRxPower, shell=True)
                output_RXAVG = output_bytes_RXAVG.decode('utf-8').strip()
                if "No Such Instance" in output_RXAVG:
                        output_RXAVG = "Pas sur ce port"
                elif "INTEGER" in output_RXAVG:
                    output_RXAVG=output_RXAVG.split("INTEGER: ", 1)[1]
                    output_RXAVG = float(output_RXAVG)
                    if output_RXAVG > 0:
                        output_RXAVG=round((10 * math.log10(output_RXAVG)-40))
                port_list.append(f"{output_RXAVG} dBm")
                output_bytes_TXPower = subprocess.check_output(commandLineTxPower, shell=True)
                output_TXPower = output_bytes_TXPower.decode('utf-8').strip()
                if "No Such Instance" in output_TXPower:
                        output_TXPower = "Pas sur ce port"
                if "INTEGER" in output_TXPower:
                    output_TXPower=output_TXPower.split("INTEGER: ", 1)[1]
                    output_TXPower = float(output_TXPower)
                    if output_TXPower > 0:
                        output_TXPower=round((10 * math.log10(output_TXPower)-40))
                port_list.append(f"{output_TXPower} dBm")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPorts
    
def c1008GEClient(communaute, adresse_ip):
    tabPorts={}
    verif=True
    i=0
    while verif:
        oidTemp=f"1.3.6.1.4.1.20044.27.3.2.16.1.2.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.27.3.2.48.1.2.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.27.3.2.40.1.2.{i}"
        oidTrafficIn =f"1.3.6.1.4.1.20044.27.11.2.4.16.1.2.{i}"
        oidInputError =f"1.3.6.1.4.1.20044.27.4.2.32.1.2.{i}"
        oidOutputError =f"1.3.6.1.4.1.20044.27.4.2.64.1.2.{i}"
        oidInputCRCError =f"1.3.6.1.4.1.20044.27.11.2.4.24.1.2.{i}"
        oidLineTemp = f"1.3.6.1.4.1.20044.27.3.3.208.1.2.{i}"
        oidLineErrors = f"1.3.6.1.4.1.20044.27.4.3.152.1.2.{i}"
        oidLineRxPower = f"	1.3.6.1.4.1.20044.27.3.3.212.1.2.{i}"
        oidLineTxPower = f"1.3.6.1.4.1.20044.27.3.3.211.1.2.{i}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        commandTrafficIn = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficIn}"
        commandInputError = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidInputError}"
        commandOutputError = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidOutputError}"
        commandInputCRCError = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidInputCRCError}"
        commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
        commandLineErrors = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineErrors}"
        commandLineRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxPower}"
        commandLineTxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxPower}"
        numPort=i+1
        if numPort not in tabPorts:
            tabPorts[numPort] = []
        port_list = tabPorts[numPort]
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_Temp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such" in output_Temp:
                verif = False
            else:
                if "INTEGER: " in output_Temp:
                    output_Temp=output_Temp.split("INTEGER: ", 1)[1]
                    output_Temp=float(output_Temp) / 256
                    output_Temp=round(output_Temp, 2)
                elif "Gauge32: " in output_Temp:
                    output_Temp=output_Temp.split("Gauge32: ", 1)[1]
                    output_Temp=float(output_Temp) / 256
                    output_Temp=round(output_Temp, 2)
                elif "Counter64: " in output_Temp:
                    output_Temp=output_Temp.split("Counter64: ", 1)[1]
                    output_Temp=float(output_Temp) / 256
                    output_Temp=round(output_Temp, 2)
                port_list.append(f"{output_Temp} °C")
                output_bytes_RXP = subprocess.check_output(commandRXPower, shell=True)
                output_RXP = output_bytes_RXP.decode('utf-8').strip()
                if "INTEGER" in output_RXP:
                    output_RXP=output_RXP.split("INTEGER: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0
                elif "Gauge32" in output_RXP:
                    output_RXP=output_RXP.split("Gauge32: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0
                elif "Counter64" in output_RXP:
                    output_RXP=output_RXP.split("Counter64: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0
                port_list.append(f"{output_RXP} dBm")
                output_bytes_TXP = subprocess.check_output(commandTXPower, shell=True)
                output_TXP = output_bytes_TXP.decode('utf-8').strip()
                if "INTEGER" in output_TXP:
                    output_TXP=output_TXP.split("INTEGER: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                elif "Gauge32" in output_TXP:
                    output_TXP=output_TXP.split("Gauge32: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                elif "Counter64" in output_TXP:
                    output_TXP=output_TXP.split("Counter64: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                port_list.append(f"{output_TXP} dBm")
                output_bytes_TIN = subprocess.check_output(commandTrafficIn, shell=True)
                output_TIN = output_bytes_TIN.decode('utf-8').strip()
                if "Counter64" in output_TIN:
                    output_TIN=output_TIN.split("Counter64: ", 1)[1]
                elif "Gauge32" in output_TIN:
                    output_TIN=output_TIN.split("Gauge32: ", 1)[1]
                elif "INTEGER" in output_TIN:
                    output_TIN=output_TIN.split("INTEGER: ", 1)[1]
                output_TIN=int(output_TIN)
                convertTool= convert(output_TIN)
                output_TIN=convertTool.converterOctalToBits()
                port_list.append(output_TIN)
                output_bytes_input_error = subprocess.check_output(commandInputError, shell=True)
                output_input_error = output_bytes_input_error.decode('utf-8').strip()
                if "Counter64" in output_input_error:
                    output_input_error=output_input_error.split("Counter64: ", 1)[1]
                elif "Gauge32" in output_input_error:
                    output_input_error=output_input_error.split("Gauge32: ", 1)[1]
                elif "INTEGER" in output_input_error:
                    output_input_error=output_input_error.split("INTEGER: ", 1)[1]
                port_list.append(output_input_error)
                output_bytes_output_error = subprocess.check_output(commandOutputError, shell=True)
                output_output_error = output_bytes_output_error.decode('utf-8').strip()
                if "Counter64" in output_output_error:
                    output_output_error=output_output_error.split("Counter64: ", 1)[1]
                elif "Gauge32" in output_output_error:
                    output_output_error=output_output_error.split("Gauge32: ", 1)[1]
                elif "INTEGER" in output_output_error:
                    output_output_error=output_output_error.split("INTEGER: ", 1)[1]
                port_list.append(output_output_error)
                output_bytes_input_crc_error = subprocess.check_output(commandInputCRCError, shell=True)
                output_input_crc_error = output_bytes_input_crc_error.decode('utf-8').strip()
                if "Counter64" in output_input_crc_error:
                    output_input_crc_error=output_input_crc_error.split("Counter64: ", 1)[1]
                elif "Gauge32" in output_input_crc_error:
                    output_input_crc_error=output_input_crc_error.split("Gauge32: ", 1)[1]
                elif "INTEGER" in output_input_crc_error:
                    output_input_crc_error=output_input_crc_error.split("INTEGER: ", 1)[1]
                port_list.append(output_input_crc_error)
                output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
                output_line_temp = output_bytes_LineTemp.decode('utf-8').strip()
                if "No Such" in output_line_temp:
                        output_line_temp = "Pas sur ce port"
                elif "Gauge32: " in output_line_temp:
                    output_line_temp=output_line_temp.split("Gauge32: ", 1)[1]
                    output_line_temp=float(output_line_temp) / 256
                    output_line_temp = round(output_line_temp, 2)
                elif "INTEGER: " in output_line_temp:
                    output_line_temp=output_line_temp.split("INTEGER: ", 1)[1]
                    output_line_temp=float(output_line_temp) / 256
                    output_line_temp = round(output_line_temp, 2)
                elif "Counter64: " in output_line_temp:
                    output_line_temp=output_line_temp.split("Counter64: ", 1)[1]
                    output_line_temp=float(output_line_temp) / 256
                    output_line_temp = round(output_line_temp, 2)
                port_list.append(f"{output_line_temp}°C")
                output_bytes_errors = subprocess.check_output(commandLineErrors, shell=True)
                output_errors = output_bytes_errors.decode('utf-8').strip()
                if "No Such" in output_errors:
                        output_errors = "Pas sur ce port"
                elif "Counter64" in output_errors:
                    output_errors=output_errors.split("Counter64: ", 1)[1]
                elif "Gauge32" in output_errors:
                    output_errors=output_errors.split("Gauge32: ", 1)[1]
                elif "INTEGER" in output_errors:
                    output_errors=output_errors.split("INTEGER: ", 1)[1]
                port_list.append(f"{output_errors}")
                output_bytes_line_RXAVG = subprocess.check_output(commandLineRxPower, shell=True)
                output_line_RXPower = output_bytes_line_RXAVG.decode('utf-8').strip()
                if "No Such" in output_line_RXPower:
                        output_line_RXPower = "Pas sur ce port"
                elif "INTEGER" in output_line_RXPower:
                    output_line_RXPower=output_line_RXPower.split("INTEGER: ", 1)[1]
                    output_line_RXPower = float(output_line_RXPower)
                    if output_line_RXPower > 0:
                        output_line_RXPower=round((10 * math.log10(output_line_RXPower)-40))
                elif "Gauge32" in output_line_RXPower:
                    output_line_RXPower=output_line_RXPower.split("Gauge32: ", 1)[1]
                    output_line_RXPower = float(output_line_RXPower)
                    if output_line_RXPower > 0:
                        output_line_RXPower=round((10 * math.log10(output_line_RXPower)-40))
                elif "Counter64" in output_line_RXPower:
                    output_line_RXPower=output_line_RXPower.split("Counter64: ", 1)[1]
                    output_line_RXPower = float(output_line_RXPower)
                    if output_line_RXPower > 0:
                        output_line_RXPower=round((10 * math.log10(output_line_RXPower)-40))
                port_list.append(f"{output_line_RXPower} dBm")
                output_bytes_line_TXPower = subprocess.check_output(commandLineTxPower, shell=True)
                output_line_TXPower = output_bytes_line_TXPower.decode('utf-8').strip()
                if "No Such" in output_line_TXPower:
                        output_line_TXPower = "Pas sur ce port"
                elif "INTEGER" in output_line_TXPower:
                    output_line_TXPower=output_line_TXPower.split("INTEGER: ", 1)[1]
                    output_line_TXPower = float(output_line_TXPower)
                    if output_line_TXPower > 0:
                        output_line_TXPower=round((10 * math.log10(output_line_TXPower)-40))
                elif "Gauge32" in output_line_TXPower:
                    output_line_TXPower=output_line_TXPower.split("Gauge32: ", 1)[1]
                    output_line_TXPower = float(output_line_TXPower)
                    if output_line_TXPower > 0:
                        output_line_TXPower=round((10 * math.log10(output_line_TXPower)-40))
                elif "Counter64" in output_line_TXPower:
                    output_line_TXPower=output_line_TXPower.split("Counter64: ", 1)[1]
                    output_line_TXPower = float(output_line_TXPower)
                    if output_line_TXPower > 0:
                        output_line_TXPower=round((10 * math.log10(output_line_TXPower)-40))
                port_list.append(f"{output_line_TXPower} dBm")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPorts

def pm06006Client(communaute, adresse_ip):
    tabPorts={}
    verif=True
    i=0
    while verif:
        oidTemp=f"1.3.6.1.4.1.20044.70.3.2.16.1.2.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.70.3.2.64.1.2.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.70.3.2.48.1.2.{i}"
        oidTrafficIn =f"1.3.6.1.4.1.20044.70.11.2.4.16.1.2.{i}"
        oidInputError =f"1.3.6.1.4.1.20044.70.11.2.4.32.1.2.{i}"
        oidOutputError =f"1.3.6.1.4.1.20044.70.11.2.4.224.1.2.{i}"
        oidLineTemp = f"1.3.6.1.4.1.20044.70.3.3.96.1.2.{i}"
        oidLineErrors = f"1.3.6.1.4.1.20044.70.4.3.192.1.2.{i}"
        oidLineRxPower = f"1.3.6.1.4.1.20044.70.3.3.128.1.2.{i}"
        oidLineTxPower = f"1.3.6.1.4.1.20044.70.3.3.80.1.2.{i}"
        commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
        commandLineErrors = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineErrors}"
        commandLineRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxPower}"
        commandLineTxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxPower}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        commandTrafficIn = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficIn}"
        commandInputError = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidInputError}"
        commandOutputError = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidOutputError}"
        numPort=i+1
        if numPort not in tabPorts:
            tabPorts[numPort] = []
        port_list = tabPorts[numPort]
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_Temp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such Instance" in output_Temp:
                verif = False
            else:
                if "INTEGER: " in output_Temp:
                    output_Temp=output_Temp.split("INTEGER: ", 1)[1]
                    output_Temp=float(output_Temp) / 256
                    output_Temp=round(output_Temp, 2)
                port_list.append(f"{output_Temp} °C")
                output_bytes_RXP = subprocess.check_output(commandRXPower, shell=True)
                output_RXP = output_bytes_RXP.decode('utf-8').strip()
                if "INTEGER" in output_RXP:
                    output_RXP=output_RXP.split("INTEGER: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0 
                port_list.append(f"{output_RXP} dBm")
                output_bytes_TXP = subprocess.check_output(commandTXPower, shell=True)
                output_TXP = output_bytes_TXP.decode('utf-8').strip()
                if "INTEGER" in output_TXP:
                    output_TXP=output_TXP.split("INTEGER: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                port_list.append(f"{output_TXP} dBm")
                output_bytes_TIN = subprocess.check_output(commandTrafficIn, shell=True)
                output_TIN = output_bytes_TIN.decode('utf-8').strip()
                if "Counter64" in output_TIN:
                    output_TIN=output_TIN.split("Counter64: ", 1)[1]
                    output_TIN=int(output_TIN)
                    convertTool= convert(output_TIN)
                    output_TIN=convertTool.converterOctalToBits()
                port_list.append(output_TIN)
                
                output_bytes_input_error = subprocess.check_output(commandInputError, shell=True)
                output_input_error = output_bytes_input_error.decode('utf-8').strip()
                if "Counter64" in output_input_error:
                    output_input_error=output_input_error.split("Counter64: ", 1)[1]
                port_list.append(output_input_error)
                
                output_bytes_output_error = subprocess.check_output(commandOutputError, shell=True)
                output_output_error = output_bytes_output_error.decode('utf-8').strip()
                if "Counter64" in output_output_error:
                    output_output_error=output_output_error.split("Counter64: ", 1)[1]
                port_list.append(output_output_error)
                output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
                output_line_temp = output_bytes_LineTemp.decode('utf-8').strip()
                if "INTEGER: " in output_line_temp:
                    output_line_temp=output_line_temp.split("INTEGER: ", 1)[1]
                    output_line_temp=float(output_line_temp) / 256
                    output_line_temp = round(output_line_temp, 2)
                port_list.append(f"{output_line_temp}°C")
                output_bytes_errors = subprocess.check_output(commandLineErrors, shell=True)
                output_errors = output_bytes_errors.decode('utf-8').strip()
                if "Gauge32" in output_errors:
                    output_errors=output_errors.split("Gauge32: ", 1)[1]
                port_list.append(f"{output_errors}")
                output_bytes_RXAVG = subprocess.check_output(commandLineRxPower, shell=True)
                output_RXAVG = output_bytes_RXAVG.decode('utf-8').strip()
                if "INTEGER" in output_RXAVG:
                    output_RXAVG=output_RXAVG.split("INTEGER: ", 1)[1]
                    output_RXAVG = float(output_RXAVG)
                    if output_RXAVG > 0:
                        output_RXAVG=round((10 * math.log10(output_RXAVG)-40))
                port_list.append(f"{output_RXAVG} dBm")
                output_bytes_TXPower = subprocess.check_output(commandLineTxPower, shell=True)
                output_TXPower = output_bytes_TXPower.decode('utf-8').strip()
                if "INTEGER" in output_TXPower:
                    output_TXPower=output_TXPower.split("INTEGER: ", 1)[1]
                    output_TXPower = float(output_TXPower)
                    if output_TXPower > 0:
                        output_TXPower=round((10 * math.log10(output_TXPower)-40))
                port_list.append(f"{output_TXPower} dBm")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPorts

def c1001hcClient(communaute, adresse_ip):
    tabPorts={}
    verif=True
    i=0
    while verif:
        oidTemp=f"1.3.6.1.4.1.20044.10.3.2.16.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.10.3.2.48.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.10.3.2.40.{i}"
        oidTrafficIn =f"1.3.6.1.4.1.20044.10.12.4.1.16.1.2.{i}"
        oidTrafficOut =f"1.3.6.1.4.1.20044.10.12.4.1.112.1.2.{i}"
        oidInputCRC =f"1.3.6.1.4.1.20044.10.4.2.32.1.2.{i}"
        oidOutputCRC =f"1.3.6.1.4.1.20044.10.4.2.64.1.2.{i}"
        oidLineTemp = f"1.3.6.1.4.1.20044.10.3.3.208.{i}"
        oidLineErrors = f"1.3.6.1.4.1.20044.10.4.3.152.1.2.{i}"
        oidLineRxAvg = f"1.3.6.1.4.1.20044.10.3.3.212.{i}"
        oidLineTxAvg = f"1.3.6.1.4.1.20044.10.3.3.211.{i}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        commandTrafficIn = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficIn}"
        commandTrafficOut = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTrafficOut}"
        commandInputCRC = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidInputCRC}"
        commandOutputCRC = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidOutputCRC}"
        commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
        commandLineErrors = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineErrors}"
        commandLineRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxAvg}"
        commandLineTxAvg = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxAvg}"
        numPort=i+1
        if numPort not in tabPorts:
            tabPorts[numPort] = []
        port_list = tabPorts[numPort]
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_Temp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such" in output_Temp:
                verif = False
            else:
                if "Gauge32: " in output_Temp:
                    output_Temp=output_Temp.split("Gauge32: ", 1)[1]
                    output_Temp=float(output_Temp) / 256
                    output_Temp=round(output_Temp, 2)
                port_list.append(f"{output_Temp} °C")
                output_bytes_RXP = subprocess.check_output(commandRXPower, shell=True)
                output_RXP = output_bytes_RXP.decode('utf-8').strip()
                if "Gauge32" in output_RXP:
                    output_RXP=output_RXP.split("Gauge32: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0 
                port_list.append(f"{output_RXP} dBm")
                output_bytes_TXP = subprocess.check_output(commandTXPower, shell=True)
                output_TXP = output_bytes_TXP.decode('utf-8').strip()
                if "Gauge32" in output_TXP:
                    output_TXP=output_TXP.split("Gauge32: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                port_list.append(f"{output_TXP} dBm")
                output_bytes_TIN = subprocess.check_output(commandTrafficIn, shell=True)
                output_TIN = output_bytes_TIN.decode('utf-8').strip()
                if "Counter64" in output_TIN:
                    output_TIN=output_TIN.split("Counter64: ", 1)[1]
                    output_TIN=int(output_TIN)
                    convertTool= convert(output_TIN)
                    output_TIN=convertTool.converterOctalToBits()
                port_list.append(output_TIN)
                output_bytes_TOUT = subprocess.check_output(commandTrafficOut, shell=True)
                output_TOUT = output_bytes_TOUT.decode('utf-8').strip()
                if "Gauge32" in output_TOUT:
                    output_TOUT=output_TOUT.split("Gauge32: ", 1)[1]
                    output_TOUT=int(output_TOUT)
                    convertTool= convert(output_TOUT)
                    output_TOUT=convertTool.converterOctalToBits()
                port_list.append(output_TOUT)
                output_bytes_input_error = subprocess.check_output(commandInputCRC, shell=True)
                output_output_error = output_bytes_input_error.decode('utf-8').strip()
                if "Counter64" in output_output_error:
                    output_output_error=output_output_error.split("Counter64: ", 1)[1]
                port_list.append(output_output_error)
                output_bytes_output_error = subprocess.check_output(commandOutputCRC, shell=True)
                output_output_error = output_bytes_output_error.decode('utf-8').strip()
                if "Counter64" in output_output_error:
                    output_output_error=output_output_error.split("Counter64: ", 1)[1]
                port_list.append(output_output_error)
                output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
                output_line_temp = output_bytes_LineTemp.decode('utf-8').strip()
                if "Gauge32: " in output_line_temp:
                    output_line_temp=output_line_temp.split("Gauge32: ", 1)[1]
                    output_line_temp=float(output_line_temp) / 256
                    output_line_temp = round(output_line_temp, 2)
                port_list.append(f"{output_line_temp}°C")
                output_bytes_errors = subprocess.check_output(commandLineErrors, shell=True)
                output_line_errors = output_bytes_errors.decode('utf-8').strip()
                if "Gauge32" in output_line_errors:
                    output_line_errors=output_line_errors.split("Gauge32: ", 1)[1]
                port_list.append(f"{output_line_errors}")
                output_bytes_RXPower = subprocess.check_output(commandLineRxPower, shell=True)
                output_line_RXPower = output_bytes_RXPower.decode('utf-8').strip()
                if "Gauge32" in output_line_RXPower:
                    output_line_RXPower=output_line_RXPower.split("Gauge32: ", 1)[1]
                    output_line_RXPower = float(output_line_RXPower)
                    if output_line_RXPower > 0:
                        output_line_RXPower=round((10 * math.log10(output_line_RXPower)-40))
                port_list.append(f"{output_line_RXPower} dBm")
                output_bytes_line_TXAVG = subprocess.check_output(commandLineTxAvg, shell=True)
                output_line_TXAVG = output_bytes_line_TXAVG.decode('utf-8').strip()
                if "Gauge32" in output_line_TXAVG:
                    output_line_TXAVG=output_line_TXAVG.split("Gauge32: ", 1)[1]
                    output_line_TXAVG = float(output_line_TXAVG)
                    if output_line_TXAVG > 0:
                        output_line_TXAVG=round((10 * math.log10(output_line_TXAVG)-40))
                port_list.append(f"{output_line_TXAVG} dBm")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPorts

def pm404Client(communaute, adresse_ip):
    tabPorts={}
    verif=True
    i=0
    while verif:
        oidTemp=f"1.3.6.1.4.1.20044.25.3.2.16.1.2.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.25.3.2.48.1.2.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.25.3.2.40.1.2.{i}"
        oidLineTemp = f"1.3.6.1.4.1.20044.25.3.3.20.1.2.{i}"
        oidLineRxPower = f"1.3.6.1.4.1.20044.25.3.3.52.1.2.{i}"
        oidLineTxPower = f"1.3.6.1.4.1.20044.25.3.3.44.1.2.{i}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
        commandLineRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxPower}"
        commandLineTxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxPower}"
        numPort=i+1
        if numPort not in tabPorts:
            tabPorts[numPort] = []
        port_list = tabPorts[numPort]
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_Temp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such" in output_Temp:
                verif = False
            else:
                if "INTEGER" in output_Temp:
                    output_Temp=output_Temp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_Temp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                elif "Gauge32: " in output_Temp:
                    output_Temp=output_Temp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_Temp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                elif "Counter64: " in output_Temp:
                    output_Temp=output_Temp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_Temp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                port_list.append(f"{temperature} °C")
                output_bytes_RXP = subprocess.check_output(commandRXPower, shell=True)
                output_RXP = output_bytes_RXP.decode('utf-8').strip()
                if "INTEGER" in output_RXP:
                    output_RXP=output_RXP.split("INTEGER: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0 
                elif "Gauge32" in output_RXP:
                    output_RXP=output_RXP.split("Gauge32: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0
                elif "Counter64" in output_RXP:
                    output_RXP=output_RXP.split("Counter64: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0
                port_list.append(f"{output_RXP} dBm")
                output_bytes_TXP = subprocess.check_output(commandTXPower, shell=True)
                output_TXP = output_bytes_TXP.decode('utf-8').strip()
                if "INTEGER" in output_TXP:
                    output_TXP=output_TXP.split("INTEGER: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0
                elif "Gauge32" in output_TXP:
                    output_TXP=output_TXP.split("Gauge32: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                elif "Counter64" in output_TXP:
                    output_TXP=output_TXP.split("Counter64: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0  
                port_list.append(f"{output_TXP} dBm")
                output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
                output_line_temp = output_bytes_LineTemp.decode('utf-8').strip()
                if "No Such" in output_line_temp:
                        output_line_temp = "Pas sur ce port"
                elif "Gauge32: " in output_line_temp:
                    output_line_temp=output_line_temp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_line_temp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                elif "Counter64: " in output_line_temp:
                    output_line_temp=output_line_temp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_line_temp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                elif "INTEGER: " in output_line_temp:
                    output_line_temp=output_line_temp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_line_temp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                port_list.append(f"{temperature}°C")
                output_bytes_line_RXPower = subprocess.check_output(commandLineRxPower, shell=True)
                output_line_RXPower = output_bytes_line_RXPower.decode('utf-8').strip()
                if "No Such" in output_line_RXPower:
                        output_line_RXPower = "Pas sur ce port"
                elif "INTEGER" in output_line_RXPower:
                    output_line_RXPower=output_line_RXPower.split("INTEGER: ", 1)[1]
                    output_line_RXPower = float(output_line_RXPower)
                    if output_line_RXPower > 0:
                        output_line_RXPower=round((10 * math.log10(output_line_RXPower)-40))
                elif "Gauge32" in output_line_RXPower:
                    output_line_RXPower=output_line_RXPower.split("Gauge32: ", 1)[1]
                    output_line_RXPower = float(output_line_RXPower)
                    if output_line_RXPower > 0:
                        output_line_RXPower=round((10 * math.log10(output_line_RXPower)-40))
                elif "Counter64" in output_line_RXPower:
                    output_line_RXPower=output_line_RXPower.split("Counter64: ", 1)[1]
                    output_line_RXPower = float(output_line_RXPower)
                    if output_line_RXPower > 0:
                        output_line_RXPower=round((10 * math.log10(output_line_RXPower)-40))
                port_list.append(f"{output_line_RXPower} dBm")
                output_bytes_line_TXPower = subprocess.check_output(commandLineTxPower, shell=True)
                output_line_TXPower = output_bytes_line_TXPower.decode('utf-8').strip()
                if "No Such" in output_line_TXPower:
                        output_line_TXPower = "Pas sur ce port"
                elif "INTEGER" in output_line_TXPower:
                    output_line_TXPower=output_line_TXPower.split("INTEGER: ", 1)[1]
                    output_line_TXPower = float(output_line_TXPower)
                    if output_line_TXPower > 0:
                        output_line_TXPower=round((10 * math.log10(output_line_TXPower)-40))
                elif "Gauge32" in output_line_TXPower:
                    output_line_TXPower=output_line_TXPower.split("Gauge32: ", 1)[1]
                    output_line_TXPower = float(output_line_TXPower)
                    if output_line_TXPower > 0:
                        output_line_TXPower=round((10 * math.log10(output_line_TXPower)-40))
                elif "Counter64" in output_line_TXPower:
                    output_line_TXPower=output_line_TXPower.split("Counter64: ", 1)[1]
                    output_line_TXPower = float(output_line_TXPower)
                    if output_line_TXPower > 0:
                        output_line_TXPower=round((10 * math.log10(output_line_TXPower)-40))
                port_list.append(f"{output_line_TXPower} dBm")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPorts

def pm1001RRClient(communaute, adresse_ip):
    tabPorts={}
    verif=True
    i=0
    while verif:
        oidTempClient=f"1.3.6.1.4.1.20044.8.3.2.16.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.8.3.2.20.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.8.3.2.19.{i}"
        oidLineTemp = f"1.3.6.1.4.1.20044.8.3.3.24.{i}"
        oidLineRxPower = f"1.3.6.1.4.1.20044.8.3.3.28.{i}"
        oidLineTxAvg = f"1.3.6.1.4.1.20044.8.3.3.27.{i}"
        commandLineTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTemp}"
        commandLineRxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineRxPower}"
        commandLineTxPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidLineTxAvg}"
        commandTempClient = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTempClient}"
        commandRXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandTXPower = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        numPort=i+1
        if numPort not in tabPorts:
            tabPorts[numPort] = []
        port_list = tabPorts[numPort]
        output_bytes_temp_client = subprocess.check_output(commandTempClient, shell=True)
        output_temp_client = output_bytes_temp_client.decode('utf-8').strip()
        try:
            if "No Such" in output_temp_client:
                verif = False
            else:
                if "Gauge32" in output_temp_client:
                    output_temp_client=output_temp_client.split("Gauge32: ", 1)[1]
                    tempInHex = hex(int(output_temp_client))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                port_list.append(f"{temperature} °C")
                output_bytes_RXP = subprocess.check_output(commandRXPower, shell=True)
                output_RXP = output_bytes_RXP.decode('utf-8').strip()
                if "Gauge32" in output_RXP:
                    output_RXP=output_RXP.split("Gauge32: ", 1)[1]
                    output_RXP = float(output_RXP)
                    if output_RXP > 0:
                        output_RXP=round((10 * math.log10(float(output_RXP))-40))
                    else:
                        output_RXP= 0 
                port_list.append(f"{output_RXP} dBm")
                output_bytes_TXP = subprocess.check_output(commandTXPower, shell=True)
                output_TXP = output_bytes_TXP.decode('utf-8').strip()
                if "Gauge32" in output_TXP:
                    output_TXP=output_TXP.split("Gauge32: ", 1)[1]
                    output_TXP = float(output_TXP)
                    if output_TXP > 0:
                        output_TXP=round((10 * math.log10(float(output_TXP))-40))
                    else:
                        output_TXP= 0 
                port_list.append(f"{output_TXP} dBm")
                output_bytes_LineTemp = subprocess.check_output(commandLineTemp, shell=True)
                output_line_temp = output_bytes_LineTemp.decode('utf-8').strip()
                if "Gauge32" in output_line_temp:
                    output_line_temp=output_line_temp.split("Gauge32: ", 1)[1]
                    tempInHex = hex(int(output_line_temp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                port_list.append(f"{temperature}°C")
                output_bytes_RXPower = subprocess.check_output(commandLineRxPower, shell=True)
                output_RXPower = output_bytes_RXPower.decode('utf-8').strip()
                if "Gauge32" in output_RXPower:
                    output_RXPower=output_RXPower.split("Gauge32: ", 1)[1]
                    output_RXPower = float(output_RXPower)
                    if output_RXPower > 0:
                        output_RXPower=round((10 * math.log10(output_RXPower)-40))
                port_list.append(f"{output_RXPower} dBm")
                output_bytes_TXAVG = subprocess.check_output(commandLineTxPower, shell=True)
                output_TXPower = output_bytes_TXAVG.decode('utf-8').strip()
                if "Gauge32" in output_TXPower:
                    output_TXPower=output_TXPower.split("Gauge32: ", 1)[1]
                    output_TXPower = float(output_TXPower)
                    if output_TXPower > 0:
                        output_TXPower=round((10 * math.log10(output_TXPower)-40))
                port_list.append(f"{output_TXPower} dBm")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPorts

def oabClient(communaute, adresse_ip):
    tabPortsOABE_OABPE={}
    verif=True 
    i=0
    while verif:
        oidTemp = f"1.3.6.1.4.1.20044.9.3.1.72.{i}"
        oidBoosterRx = f"1.3.6.1.4.1.20044.9.3.3.42.{i}"
        oidBoosterTx = f"1.3.6.1.4.1.20044.9.3.3.41.{i}"
        oidBoosterGain = f"1.3.6.1.4.1.20044.9.3.3.43.{i}"
        oidPumpLaser = f"1.3.6.1.4.1.20044.9.3.3.40.{i}"
        oidPreAmpRx = f"1.3.6.1.4.1.20044.9.3.2.34.{i}"
        oidPreAmpTx = f"1.3.6.1.4.1.20044.9.3.2.33.{i}"
        oidPreAmpGain = f"1.3.6.1.4.1.20044.9.3.2.35.{i}"
        oidPreAmpPump = f"1.3.6.1.4.1.20044.9.3.2.32.{i}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandBRX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterRx}"
        commandBoosterGain = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterGain}"
        commandPumpLaser = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPumpLaser}"
        commandBTX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterTx}"
        commandPARX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpRx}"
        commandPATX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpTx}"
        commandPreAmpGain = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpGain}"
        commandPreAmpPump = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpPump}"
        numPort=i+1
        if numPort not in tabPortsOABE_OABPE:
            tabPortsOABE_OABPE[numPort] = []
        port_list = tabPortsOABE_OABPE[numPort]
        
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_temp_oabp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such" in output_temp_oabp:
                verif = False
            else:
                if "INTEGER" in output_temp_oabp:
                    output_temp_oabp=output_temp_oabp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_temp_oabp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                elif "Gauge32" in output_temp_oabp:
                    output_temp_oabp=output_temp_oabp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_temp_oabp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                elif "Counter64" in output_temp_oabp:
                    output_temp_oabp=output_temp_oabp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_temp_oabp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                port_list.append(f"{temperature} °C")
                output_bytes_BRX = subprocess.check_output(commandBRX, shell=True)
                output_BRX = output_bytes_BRX.decode('utf-8').strip()
                if "INTEGER" in output_BRX:
                    output_BRX=output_BRX.split("INTEGER: ", 1)[1]
                    output_BRX=round(((float(output_BRX)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_BRX:
                    output_BRX=output_BRX.split("Gauge32: ", 1)[1]
                    output_BRX=round(((float(output_BRX)-32768)) * 0.005 ,2)
                elif "Counter64" in output_BRX:
                    output_BRX=output_BRX.split("Counter64: ", 1)[1]
                    output_BRX=round(((float(output_BRX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_BRX} dBm")
                output_bytes_BTX = subprocess.check_output(commandBTX, shell=True)
                output_BTX = output_bytes_BTX.decode('utf-8').strip()
                if "INTEGER" in output_BTX:
                    output_BTX=output_BTX.split("INTEGER: ", 1)[1]
                    output_BTX=round(((float(output_BTX)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_BTX:
                    output_BTX=output_BTX.split("Gauge32: ", 1)[1]
                    output_BTX=round(((float(output_BTX)-32768)) * 0.005 ,2)
                elif "Counter64" in output_BTX:
                    output_BTX=output_BTX.split("Counter64: ", 1)[1]
                    output_BTX=round(((float(output_BTX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_BTX} dBm")
                
                output_bytes_gain = subprocess.check_output(commandBoosterGain, shell=True)
                output_gain = output_bytes_gain.decode('utf-8').strip()
                if "INTEGER" in output_gain:
                    output_gain=output_gain.split("INTEGER: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_gain:
                    output_gain=output_gain.split("Gauge32: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                elif "Counter64" in output_gain:
                    output_gain=output_gain.split("Counter64: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                port_list.append(f"{output_gain} dB")
                
                output_bytes_pump_laser = subprocess.check_output(commandPumpLaser, shell=True)
                output_pump_laser = output_bytes_pump_laser.decode('utf-8').strip()
                if "INTEGER" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("INTEGER: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                elif "Gauge32" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("Gauge32: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                elif "Counter64" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("Counter64: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                port_list.append(f"{output_pump_laser} mA")
                output_bytes_PARX = subprocess.check_output(commandPARX, shell=True)
                output_PARX = output_bytes_PARX.decode('utf-8').strip()
                if "INTEGER" in output_PARX:
                    output_PARX=output_PARX.split("INTEGER: ", 1)[1]
                    output_PARX=round(((float(output_PARX)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_PARX:
                    output_PARX=output_PARX.split("Gauge32: ", 1)[1]
                    output_PARX=round(((float(output_PARX)-32768)) * 0.005 ,2)
                elif "Counter64" in output_PARX:
                    output_PARX=output_PARX.split("Counter64: ", 1)[1]
                    output_PARX=round(((float(output_PARX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_PARX} dBm")
                output_bytes_PATX = subprocess.check_output(commandPATX, shell=True)
                output_PATX = output_bytes_PATX.decode('utf-8').strip()
                if "INTEGER" in output_PATX:
                    output_PATX=output_PATX.split("INTEGER: ", 1)[1]
                    output_PATX=round(((float(output_PATX)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_PATX:
                    output_PATX=output_PATX.split("Gauge32: ", 1)[1]
                    output_PATX=round(((float(output_PATX)-32768)) * 0.005 ,2)
                elif "Counter64" in output_PATX:
                    output_PATX=output_PATX.split("Counter64: ", 1)[1]
                    output_PATX=round(((float(output_PATX)-32768)) * 0.005 ,2)
                port_list.append(f"{output_PATX} dBm")
                
                output_bytes_preamp_gain = subprocess.check_output(commandPreAmpGain, shell=True)
                output_preamp_gain = output_bytes_preamp_gain.decode('utf-8').strip()
                if "INTEGER" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("INTEGER: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("Gauge32: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                elif "Counter64" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("Counter64: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                port_list.append(f"{output_preamp_gain} dB")
                
                output_bytes_preamp_pump_laser = subprocess.check_output(commandPreAmpPump, shell=True)
                output_pump_preamp_laser = output_bytes_preamp_pump_laser.decode('utf-8').strip()
                if "INTEGER" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("INTEGER: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                elif "Gauge32" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("Gauge32: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                elif "Counter64" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("Counter64: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                port_list.append(f"{output_pump_preamp_laser} mA")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPortsOABE_OABPE

def roadm(communaute, adresse_ip):
    tabRoadm={}
    i=0
    iPower=65
    while iPower<158:
        oidChannel=f"1.3.6.1.4.1.20044.98.3.3.{iPower}.1.2.0"
        oidPowerIn = f"1.3.6.1.4.1.20044.98.3.3.{iPower}.1.2.0"
        oidPowerOut = f"1.3.6.1.4.1.20044.98.3.3.{iPower}.1.2.1"
        commandPowerOut = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidChannel}"
        commandPowerIn = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPowerIn}"
        commandChannel = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPowerOut}"
        numPort=i+1
        if numPort not in tabRoadm:
            tabRoadm[numPort] = []
        port_list = tabRoadm[numPort]
        output_bytes_pin = subprocess.check_output(commandPowerIn, shell=True)
        output_pin = output_bytes_pin.decode('utf-8').strip()
        try:
            output_bytes_channel = subprocess.check_output(commandChannel, shell=True)
            output_channel = output_bytes_channel.decode('utf-8').strip()
            if "No Such" in output_channel:
                output_channel = "Pas ici"
            else:
                if "INTEGER" in output_channel:
                    output_channel=output_channel.split("INTEGER: ", 1)[1]
                    output_channel=float(output_channel)
                    output_channel = output_channel*0.003125
                    output_channel = round(output_channel, 2)
                port_list.append(f"{output_channel} THz")
            if "No Such" in output_pin:
                output_pin = "Pas ici"
            else:
                if "INTEGER" in output_pin:
                    output_pin=output_pin.split("INTEGER: ", 1)[1]
                    output_pin=float(output_pin)
                    if output_pin < 32768:
                        output_pin = output_pin*0.1
                    else:
                        output_pin =  (output_pin - 65535) * 0.1
                    output_pin = round(output_pin, 2)
                port_list.append(f"{output_pin} dBm")
                output_bytes_pout = subprocess.check_output(commandPowerOut, shell=True)
                output_pout = output_bytes_pout.decode('utf-8').strip()
                if "INTEGER" in output_pout:
                    output_pout=output_pout.split("INTEGER: ", 1)[1]
                    output_pout=float(output_pout)
                    if output_pout < 32768:
                        output_pout = output_pout*0.1
                    else:
                        output_pout =  (output_pout - 65535) * 0.1
                    output_pout = round(output_pout, 2) 
                port_list.append(f"{iPower} {output_pout} dBm")
        except subprocess.CalledProcessError:
            verif = False
        iPower += 1
        i += 1
    return tabRoadm    
                
def oail_hcs(communaute, adresse_ip):
    tabPortsOAIL={}
    verif=True 
    i=0
    while verif:
        oidTemp = f"1.3.6.1.4.1.20044.62.3.1.80.{i}"
        oidBoosterRx = f"1.3.6.1.4.1.20044.62.3.3.50.{i}"
        oidBoosterTx = f"1.3.6.1.4.1.20044.62.3.3.49.{i}"
        oidBoosterGain = f"1.3.6.1.4.1.20044.62.3.3.54.{i}"
        oidPumpLaser = f"1.3.6.1.4.1.20044.62.3.3.48.{i}"
        oidRxPower = f"1.3.6.1.4.1.20044.62.3.2.34.{i}"
        oidTxPower = f"1.3.6.1.4.1.20044.62.3.2.33.{i}"
        oidPreAmpGain = f"1.3.6.1.4.1.20044.62.3.2.38.{i}"
        oidPreAmpPump = f"1.3.6.1.4.1.20044.62.3.2.32.{i}"
        commandTemp = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTemp}"
        commandBRX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterRx}"
        commandBTX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterTx}"
        commandBoosterGain = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidBoosterGain}"
        commandPumpLaser = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPumpLaser}"
        
        commandPreAmpGain = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpGain}"
        commandPreAmpPump = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidPreAmpPump}"
        commandPARX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidRxPower}"
        commandPATX = f"snmpwalk -v2c -c cpdea{communaute} {adresse_ip} {oidTxPower}"
        numPort=i+1
        if numPort not in tabPortsOAIL:
            tabPortsOAIL[numPort] = []
        port_list = tabPortsOAIL[numPort]
        
        output_bytes_temp = subprocess.check_output(commandTemp, shell=True)
        output_temp_oabp = output_bytes_temp.decode('utf-8').strip()
        try:
            if "No Such" in output_temp_oabp:
                verif = False
            else:
                if "INTEGER" in output_temp_oabp:
                    output_temp_oabp=output_temp_oabp.split("INTEGER: ", 1)[1]
                    tempInHex = hex(int(output_temp_oabp))[2:]
                    num_pairs = len(tempInHex) // 2
                    first_pair = tempInHex[:2*num_pairs-2]
                    last_pair = tempInHex[2*num_pairs-2:]
                    first_decimal = int(first_pair, 16)
                    last_decimal = int(last_pair, 16)
                    temperature = last_decimal / 256.0 + first_decimal
                    temperature = round(temperature, 2)
                port_list.append(f"{temperature} °C")
                output_bytes_RXPower = subprocess.check_output(commandBRX, shell=True)
                output_RXPower = output_bytes_RXPower.decode('utf-8').strip()
                if "INTEGER" in output_RXPower:
                    output_RXPower=output_RXPower.split("INTEGER: ", 1)[1]
                    output_RXPower=round(((float(output_RXPower)-32768)) * 0.005 ,2)
                port_list.append(f"{output_RXPower} dBm")
                output_bytes_TXPower = subprocess.check_output(commandBTX, shell=True)
                output_TXPower = output_bytes_TXPower.decode('utf-8').strip()
                if "INTEGER" in output_TXPower:
                    output_TXPower=output_TXPower.split("INTEGER: ", 1)[1]
                    output_TXPower=round(((float(output_TXPower)-32768)) * 0.005 ,2)
                port_list.append(f"{output_TXPower} dBm")     
                output_bytes_gain = subprocess.check_output(commandBoosterGain, shell=True)
                output_gain = output_bytes_gain.decode('utf-8').strip()
                if "INTEGER" in output_gain:
                    output_gain=output_gain.split("INTEGER: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_gain:
                    output_gain=output_gain.split("Gauge32: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                elif "Counter64" in output_gain:
                    output_gain=output_gain.split("Counter64: ", 1)[1]
                    output_gain=round(((float(output_gain)-32768)) * 0.005 ,2)
                port_list.append(f"{output_gain} dB")
                
                output_bytes_pump_laser = subprocess.check_output(commandPumpLaser, shell=True)
                output_pump_laser = output_bytes_pump_laser.decode('utf-8').strip()
                if "INTEGER" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("INTEGER: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                elif "Gauge32" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("Gauge32: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                elif "Counter64" in output_pump_laser:
                    output_pump_laser=output_pump_laser.split("Counter64: ", 1)[1]
                    output_pump_laser=round(float(output_pump_laser)/100)
                port_list.append(f"{output_pump_laser} mA")
                output_bytes_RXIL2 = subprocess.check_output(commandPARX, shell=True)
                output_RXPower2 = output_bytes_RXIL2.decode('utf-8').strip()
                if "INTEGER" in output_RXPower2:
                    output_RXPower2=output_RXPower2.split("INTEGER: ", 1)[1]
                    output_RXPower2=round(((float(output_RXPower2)-32768)) * 0.005 ,2)
                port_list.append(f"{output_RXPower2} dBm")
                output_bytes_TXIL2 = subprocess.check_output(commandPATX, shell=True)
                output_TXPower2 = output_bytes_TXIL2.decode('utf-8').strip()
                if "INTEGER" in output_TXPower2:
                    output_TXPower2=output_TXPower2.split("INTEGER: ", 1)[1]
                    output_TXPower2=round(((float(output_TXPower2)-32768)) * 0.005 ,2)
                port_list.append(f"{output_TXPower2} dBm")
                output_bytes_preamp_gain = subprocess.check_output(commandPreAmpGain, shell=True)
                output_preamp_gain = output_bytes_preamp_gain.decode('utf-8').strip()
                if "INTEGER" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("INTEGER: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                elif "Gauge32" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("Gauge32: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                elif "Counter64" in output_preamp_gain:
                    output_preamp_gain=output_preamp_gain.split("Counter64: ", 1)[1]
                    output_preamp_gain=round(((float(output_preamp_gain)-32768)) * 0.005 ,2)
                port_list.append(f"{output_preamp_gain} dB")
                
                output_bytes_preamp_pump_laser = subprocess.check_output(commandPreAmpPump, shell=True)
                output_pump_preamp_laser = output_bytes_preamp_pump_laser.decode('utf-8').strip()
                if "INTEGER" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("INTEGER: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                elif "Gauge32" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("Gauge32: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                elif "Counter64" in output_pump_preamp_laser:
                    output_pump_preamp_laser=output_pump_preamp_laser.split("Counter64: ", 1)[1]
                    output_pump_preamp_laser=round(float(output_pump_preamp_laser)/100)
                port_list.append(f"{output_pump_preamp_laser} mA")
                i += 1
        except subprocess.CalledProcessError:
            verif = False
    return tabPortsOAIL