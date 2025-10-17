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

    if equipement_type['equipment type'] == '7360':
        typing = r'>\#'
    elif equipement_type['equipment type'] == 'ADVA':
        typing = r'-->'
    else:
        typing = r'\d+\#'

    try:
        ssh = pexpect.spawn(f'ssh -F /app/ssh_config -o StrictHostKeyChecking=no {username}@{equipement}', timeout=30, maxread=1000000)
        
        while True:
            ix = ssh.expect([pexpect.TIMEOUT, 'password:', pexpect.EOF, 'Are you sure you want to continue connecting (yes/no/[fingerprint])?', 'Permission denied'], timeout=30)

            if ix == 3:
                ssh.sendline('yes')
                ssh.expect('password:', timeout=30)
                ssh.sendline(password)
            elif ix == 1:
                ssh.sendline(password)
                ssh.expect(typing, timeout=30)
                break

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

            command_output = "\n".join(
                line for line in output.split('\n')
                if not line.strip() == '=' * len(line.strip())
                and not re.fullmatch(r'(olt|edg)-[a-z0-9\-]+', line.strip())
                and not re.search(r'\*A:edg-[a-z0-9\-]+', line)
            )
            results[cmd] = command_output if command_output else None

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

    return results


# Connexion SSH CISCO complete
# @param: str, str, str, list
# @return: pexpect session object or None
def ssh_pbb_cisco(final_host, intermediate_host='vma-prddck-104.pau', intermediate_user='cag', commands=None):
    """
    Établit une connexion SSH avec rebond pour les équipements PBB/ABR Cisco.
    
    Args:
        final_host: Hostname de l'équipement final (DNS complet)
        intermediate_host: Hostname de l'hôte intermédiaire (par défaut: vma-prddck-104.pau)
        intermediate_user: Username pour l'hôte intermédiaire (par défaut: cag)
        commands: Liste de commandes à exécuter (optionnel)
    
    Returns:
        dict: {'session': pexpect_session, 'results': {cmd: output}} ou None en cas d'erreur
    """
    intermediate_password = 'SpaciumAevum043?'
    final_user = 'provauto'
    final_password = 'srv-pia64-l'
    
    session = None
    results = {}
    
    try:
        # Connexion à l'hôte intermédiaire
        session = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {intermediate_user}@{intermediate_host}', timeout=30)
        i = session.expect(['password:', pexpect.TIMEOUT], timeout=30)
        if i == 1:
            raise Exception(f"Timeout en attendant le mot de passe pour {intermediate_host}")
        session.sendline(intermediate_password)
        
        prompt_patterns = [r'\$ ', r'# ', pexpect.TIMEOUT]
        if session.expect(prompt_patterns, timeout=30) == 2:
            raise Exception(f"Timeout en attendant le prompt sur {intermediate_host}")

        # Connexion à l'équipement final
        final_host_command = f'ssh -o StrictHostKeyChecking=no {final_user}@{final_host}'
        session.sendline(final_host_command)

        # Attendre la bannière Cisco (ligne d'astérisques)
        session.expect(r'\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*', timeout=60)
        session.send(' ')
        
        i = session.expect([r'Password:', r'password:', pexpect.TIMEOUT], timeout=60)
        if i == 2:
            raise Exception(f"Timeout en attendant le mot de passe pour {final_host}")
        session.sendline(final_password)

        # Attendre le prompt Cisco
        prompt_patterns = [r'RP/0/RP0/CPU0:.*#', r'.*#', pexpect.TIMEOUT]
        if session.expect(prompt_patterns, timeout=30) == 2:
            raise Exception(f"Timeout en attendant le prompt Cisco sur {final_host}")
        
        # Exécuter les commandes si fournies
        if commands:
            for cmd in commands:
                session.sendline(cmd)
                
                prompt_pattern = r'RP/0/RP0/CPU0:.*#'
                output = ""
                
                import time
                start_time = time.time()
                while True:
                    index = session.expect([prompt_pattern, '--More--', 'Press any key to continue', pexpect.TIMEOUT], timeout=10)
                    output += session.before.decode('utf-8', errors='replace')
                    
                    if index == 0:
                        break
                    elif index in [1, 2]:
                        session.send(' ')
                    elif index == 3:
                        break
                    
                    # Protection contre les boucles infinies
                    if time.time() - start_time > 15:
                        break
                
                results[cmd] = output
        
        return {'session': session, 'results': results}
        
    except Exception as e:
        if session:
            try:
                session.close()
            except:
                pass
        raise Exception(f"Erreur connexion SSH PBB/Cisco: {str(e)}")


# Fonction pour fermer proprement une session SSH PBB/Cisco
# @param: pexpect session
# @return: None
def close_ssh_pbb_cisco(session):
    """
    Ferme proprement une session SSH PBB/Cisco.
    
    Args:
        session: Session pexpect à fermer
    """
    if session and session.isalive():
        try:
            session.sendline('exit')
            session.close()
        except Exception:
            pass