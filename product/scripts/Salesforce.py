# -*- coding: utf-8 -*-

# 
# @file	    Salesforce.py
#

# LIBRAIRIES
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

# METHODES

# Check d'une requête Salesforce
def QuerySF(query):
    try:
        sf = Salesforce(
            username='production@axione.fr',
            password='Ame@Pyrite',
            security_token='',
            domain='login',
            instance_url='https://axione-sso.my.salesforce.com'
        )
    except SalesforceAuthenticationFailed as e:
        raise Exception(f"Impossible de se connecter à SF: {e}")
    #

    records = []
    try:
        result = sf.query_all(query)
        records.extend(result['records'])

        while not result['done']:
            result = sf.query_more(result['nextRecordsUrl'], True)
            records.extend(result['records'])
        #
    except Exception as e:
        raise Exception(f"Echec de la requête: {e}")
    #

    return {key: record[key] for record in records for key in record}
#
