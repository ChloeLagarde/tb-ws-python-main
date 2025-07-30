import time
import pexpect
import json
from concurrent.futures import ThreadPoolExecutor

class SshConnect:
    def __init__(self):
        self.ip = None
        self.login = None
        self.passwd = None
        self.timeout = None
        self.session = None
        self.logged_in = False
        self.log = []  # Liste pour stocker les logs d'erreurs

    def set_connection(self, ip, login, passwd, timeout):
        self.ip = ip
        self.login = login
        self.passwd = passwd
        self.timeout = timeout

    def login_in(self):
        """Établit une connexion SSH et capture les logs en mémoire."""
        try:
            self.session = pexpect.spawn(
                f'ssh -o StrictHostKeyChecking=no {self.login}@{self.ip}', timeout=self.timeout
            )

            # Capture les sorties dans une chaîne
            read_output = ""

            class CaptureOutput:
                def write(self, data):
                    nonlocal read_output
                    read_output += data.decode('utf-8', errors='replace')

                def flush(self):
                    pass

            self.session.logfile_read = CaptureOutput()

            # Attente du prompt de mot de passe (avec variations possibles)
            self.session.expect([r'password.*:', pexpect.TIMEOUT], timeout=60)
            self.session.sendline(self.passwd)

            # Attente du prompt de ligne de commande ou d'un message d'erreur
            index = self.session.expect([
                pexpect.TIMEOUT,
                pexpect.EOF,
                '>',
                r'\$',
                r'[Ee]rror.*',  # Cas de messages d'erreur explicites
                r'[Pp]ermission [Dd]enied.*',  # Permission refusée
                r'[Nn]o such.*',  # Hôte introuvable
            ], timeout=60)

            self.log.append(f"Console complète :\n{read_output}")

            if index == 0:  # TIMEOUT
                self.log.append("Timeout lors de la tentative de connexion SSH.")
                return False
            elif index == 1:  # EOF (Connexion fermée)
                # Analyse des raisons possibles dans les logs
                if "Received disconnect" in read_output:
                    lines = read_output.splitlines()
                    for line in lines:
                        if "Received disconnect" in line:
                            self.log.append(f"Raison de la déconnexion : {line.strip()}")
                            break
                self.log.append("La connexion SSH a été fermée par le serveur.")
                return False
            elif index == 2 or index == 3:  # Prompt trouvé ('>' ou '$')
                self.logged_in = True
                return True
            elif index == 4:  # Message d'erreur explicite
                self.log.append("Erreur détectée lors de la tentative de connexion SSH.")
                return False
            elif index == 5:  # Permission refusée
                self.log.append("Connexion refusée : Mot de passe ou permissions incorrectes.")
                return False
            elif index == 6:  # Hôte introuvable
                self.log.append("Connexion impossible : Hôte introuvable.")
                return False

        except pexpect.exceptions.TIMEOUT as e:
            self.log.append(f"Timeout : {str(e)}")
        except pexpect.exceptions.EOF as e:
            self.log.append(f"EOF atteint : {str(e)}")
        except pexpect.exceptions.ExceptionPexpect as e:
            self.log.append(f"Erreur Pexpect : {str(e)}")
        except Exception as e:
            self.log.append(f"Erreur générale : {str(e)}")

        return False



    def logout(self):
        """Ferme proprement la session SSH."""
        if self.logged_in and self.session:
            try:
                self.session.sendline('quit')  # Commande pour quitter proprement
                self.session.close()
                self.logged_in = False
            except Exception as e:
                self.log.append(f"Erreur lors de la déconnexion : {str(e)}")

    def execute_command(self, command):
        """Exécute une commande SSH, nettoie les résultats et les divise ligne par ligne."""
        if not self.logged_in:
            return ["PAS CONNECTÉ"]

        self.session.sendline(command)
        output_lines = []

        try:
            while True:
                self.session.expect(['---- More ----', '>', pexpect.TIMEOUT], timeout=self.timeout)
                raw_output = self.session.before.decode('utf-8')
                output_lines.extend(raw_output.replace('\r', '').split('\n'))

                if self.session.match_index == 0:  # Si '----more----' est détecté
                    self.session.send(' ')  # Envoie un espace pour continuer
                elif self.session.match_index == 1:  # Si '>' est détecté (fin de commande)
                    break
                elif self.session.match_index == 2:  # Timeout
                    return [f"Timeout lors de l'exécution de la commande: {command}"]

            # Nettoyage et retour des lignes
            cleaned_output = [line.strip() for line in output_lines if line.strip()]
            time.sleep(0.2)
            return cleaned_output

        except pexpect.exceptions.TIMEOUT:
            return [f"Timeout lors de l'exécution de la commande: {command}"]

    def configure_ethernet(self, port):
        if not self.logged_in:
            self.log.append("Session SSH non connectée.")
            return None

        output = []
        commands = [
            f'configure ethernet line {port}',
            'info detail'
        ]
        try:
            for cmd in commands:
                result = self.execute_command(cmd)
                if result:
                    output.extend(result)
            return output
        except Exception as e:
            self.log.append(f"Erreur dans configure_ethernet : {str(e)}")
            return None
