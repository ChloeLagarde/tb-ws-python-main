import subprocess


# Create the SNMP request (cpdea) to simplify the code
def snmp_request(host, oid):
    command = ['snmpwalk', '-c', 'cpdea', '-v', '2c', host, oid]
    response = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = response.communicate()[0]
    return output


# Create the SNMP request (public) to simplify the code
def snmp_request_public(host, oid):
    command = ['snmpwalk', '-c', 'public', '-v', '2c', host, oid]
    response = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = response.communicate()[0]
    return output


# Create the SNMP request (Cpdeacpdea) to simplify the code
def snmp_request_cpdeacpdea(host, oid):
    command = ['snmpwalk', '-c', 'Cpdeacpdea', '-v', '2c', host, oid]
    response = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = response.communicate()[0]
    return output