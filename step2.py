#!/usr/bin/env python
import sys
import datetime
import time
from binascii import hexlify, unhexlify

import jc_ops
import jc_tree
import jc_util # for debug prints


# NET : "btc-testnet" or "btc-mainnet"
NET = "btc-testnet"
DEBUG = False
print("%s Step 2 started, net: %s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), NET))

start_time = time.time()

# search in bdd for transactions "submitted" 
list_tx = jc_tree.get_submitted_tx()

# check if the transaction are confirmed
# if yes, update bdd with date of mining
for tx in list_tx:
    (is_found, timest, confirm) = jc_ops.txinfo(tx, NET)
    if is_found:
        if confirm >= 3:
            print("--- confirmed tx : %s, confirmations : %s, timestamp = %s" % (tx, confirm, timest))
            jc_tree.local_update_step2(tx, timest, NET)
        else:
            print("--- pending tx : %s, confirmations : %s, timestamp = %s" % (tx, confirm, timest))
    else:
        print("*** tx id not found in the blockchain : %s" % tx)
    
# update remote db for all ready  records 
nb_requests = jc_tree.remote_update_step2(NET)
print("%s Step 2 completed, nb requests completed : %s, duration :%s seconds " % 
      (time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), nb_requests, round(time.time() - start_time, 3)))

