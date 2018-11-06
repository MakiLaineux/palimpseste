#!/usr/bin/env python
import sys
import datetime
import time
from binascii import hexlify, unhexlify

import jc_ops
import jc_tree
import jc_util # for debug prints

# NET : "testnet" or "mainnet"
NET = "mainnet"
DEBUG = False
start_time = time.time()


# search in bdd for transactions "submitted" 
list_tx = jc_tree.get_submitted_tx()

# check if the transaction are confirmed
# if yes, update bdd with date of mining
for tx in list_tx:
    (is_found, timest, confirm) = jc_ops.txinfo(tx, NET)
    print "Transaction : %s" % tx
    if is_found:
        print "---timestamp = %d" % timest
        print "---confirmations = %d" % confirm
        if confirm >= 6:
            print "ok"
            jc_tree.update_step2(tx, timest, NET)
            print("--- time : %s seconds" % (time.time() - start_time))

    else:
        print "*** tx id not found in the blockchain"
    
    

