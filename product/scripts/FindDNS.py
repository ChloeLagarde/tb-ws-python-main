import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_dns(equipment, dns):
    host = equipment + dns
    result = subprocess.run(["nslookup", host], capture_output=True, text=True)
    if 'NXDOMAIN' not in result.stdout:
        return host
    return None

def find_dns(equipment):
    dns_list = ['.bcb.axione.fr', '.par.axione.fr', '.adn.axione.fr', '.cha.axione.fr', '.lim.axione.fr',
                '.qui.axione.fr', '.tou.axione.fr', '.loi.axione.fr', '.mel.axione.fr', '.mtr.axione.fr',
                '.nie.axione.fr', '.pau.axione.fr', '.hpy.axione.fr', '.sar.axione.fr', '.gon.axione.fr',
                '.vau.axione.fr', '.fin.axione.fr', '.jur.axione.fr', '.bou.axione.fr', '.gab.axione.fr',
                '.t42.axione.fr', '.t78.axione.fr', '.ais.axione.fr', '.bfo.axione.fr', '.npc.axione.fr',
                '.t72.axione.fr', '.odi.axione.fr', '.y78.axione.fr', '.lna.axione.fr', '.lab.axione.fr',
                '.adf.axione.fr', '.enn.axione.fr', '.eur.axione.fr', '.hsn.axione.fr', '.ctf.axione.fr',
                '.uki.axione.fr', '.lat.axione.fr', '.sqy.axione.fr', '.urw.axione.fr', '.enu.axione.fr']

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(check_dns, equipment, dns) for dns in dns_list]
        for future in as_completed(futures):
            result = future.result()
            if result:
                # Si un DNS est trouvé, on arrête la recherche
                executor.shutdown(wait=False)
                return result

    return None
