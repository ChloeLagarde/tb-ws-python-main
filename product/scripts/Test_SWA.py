from scripts.SnmpRequests import *
import re


def test_swa(port1, port2, port3, port4, host):
    if port4 == "":
        portavecpoint = str(port1) + "." + str(port2) + "." + str(port3)
    else:
        portavecpoint = str(port1) + "." + str(port2) + "." + str(port3) + "." + str(port4)
    result = snmp_request(host, '1.3.6.1.4.1.738.1.5.100.2.2.2.1.11')
    # the command returns several lines, we only want the one that matches the port
    for line in result.splitlines():
        test = re.search(r'11.(\d+.\d+.\d+)', str(line))
        if test:
            test = test.group(1)
        if portavecpoint == test:
            # get the digits at the end of the line
            result = re.search(r'(: (\d+))', str(line))
            if result:
                result = result.group(2)
            return int(result)
