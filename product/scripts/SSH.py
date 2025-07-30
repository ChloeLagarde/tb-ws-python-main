# -*- coding: utf-8 -*-
 
#
# @file     SSH.py
#
 
# LIBRAIRIES
import pexpect, re, sys
from scripts.FindDNS import find_dns
from scripts.Version_Alcatel_Telco_One_Access import version_alcatel_telco_one_access

# METHODES

# Création d'un session SSH
# @param: str, str
# @return: dict
def ssh(equipement_name, cmds):
    results = {}
    username = ''
    password = ''
    typing = ''

    equipement = find_dns(equipement_name)
    equipement_type = version_alcatel_telco_one_access(equipement)

    if equipement_type['equipment type'] == '7360' and not re.search(r'enu\.axione\.fr', equipement):
        username, password = 'isadmin', 'p2mal&'
    elif equipement_type['equipment type'] == 'EKINOPS':
        username, password = 'administrator', 'administrator'
    else:
        username, password = 'provauto', 'srv-pia64-l'
    #

    if equipement_type['equipment type'] == '7360':
        typing = r'>\#'
    elif equipement_type['equipment type'] == 'ADVA':
        typing = r'-->'
    else:
        #typing = r'\d+\#'
        typing = r'\d+\#'

    try:
        ssh = pexpect.spawn(f'ssh -F /app/ssh_config -o StrictHostKeyChecking=no {username}@{equipement}', timeout=30, maxread=1000000)
        
        while True:
            ix = ssh.expect([pexpect.TIMEOUT, 'password:', pexpect.EOF, 'Are you sure you want to continue connecting (yes/no/[fingerprint])?', 'Permission denied'], timeout=30)

            if ix == 3:  # 'Are you sure you want to continue connecting (yes/no/[fingerprint])?'
                ssh.sendline('yes')
                ssh.expect('password:', timeout=30)
                ssh.sendline(password)
            elif ix == 1:  # 'password:'
                ssh.sendline(password)
                ssh.expect(typing, timeout=30)
                break
            #
        #

        for cmd in cmds:
            ssh.sendline(cmd)

            output = ""
            while True:
                im = ssh.expect([typing, '--More--', 'Press any key to continue'], timeout=30)
                output += ssh.before.decode('utf-8')

                if im == 0:
                    break
                elif im in [1, 2]:
                    ssh.send(' ')
                #
            #

            command_output = "\n".join(
                line for line in output.split('\n')
                if not line.strip() == '=' * len(line.strip())
                and not re.fullmatch(r'(olt|edg)-[a-z0-9\-]+', line.strip())
                and not re.search(r'\*A:edg-[a-z0-9\-]+', line)
            )
            results[cmd] = command_output if command_output else None
        #

        if equipement_type['equipment type'] == 'MA5800':
            ssh.sendline('quit')
        else:
            ssh.sendline('logout')
        ssh.close()
    except pexpect.EOF:
        return "Connexion SSH KO : EOF."
    except pexpect.TIMEOUT:
        return "Connexion SSH KO : TIMEOUT."
    except pexpect.ExceptionPexpect as e:
        return f"Connexion SSH KO : {e}"
    #

    return results
#