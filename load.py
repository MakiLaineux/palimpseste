#!/usr/bin/env python
import sys
import datetime
import time
from binascii import hexlify, unhexlify
import requests # to handle communication with remote server
import json # to handle communication with remote server

# NET : "btc-testnet" or "btc-mainnet"
NET = "btc-testnet"
start_time = time.time()
# Loop and create dummy requests
k=100
request_string = ""
while k < 200 :
    try:
        request_string = ("http://technoprimates.com/request_proof.php?idrequest='%s'&instance='toto'&hash='texteduhash'" % str(k))
        print(request_string)
        r = requests.get(request_string)
        data = json.loads(r.text)
        print("%s , id=%d", (request_string, long(data[0]['id'])))
        k += 1
    except:
        print("Remote query failed, request : %s" % request_string)
        k += 1

print("--- total time : %s seconds" % (time.time() - start_time))


