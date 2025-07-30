import subprocess
import re
import platform


def ping(host):
    # Parameters depending on the OS
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    # Ping
    command = ['ping', param, '1', host]
    try :
        response = subprocess.check_output(command)
    # Get IP address
        ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', str(response))
    # Get response time
        response_time = re.findall(r'time=[0-9]+(?:\.[0-9]+)?', str(response))
        return ip[0] + " " + response_time[0]
    except subprocess.CalledProcessError:
        return "No response from host"
