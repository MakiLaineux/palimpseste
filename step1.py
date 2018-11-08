#!/usr/bin/env python
#jc janvier 2018
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
start_time = time.time()

print "1: "
print "net: "+NET

# query remote db and insert new "status 2" requests in local db 
jc_tree.insert_step1()

# create a list containing the requests, each with its hash and the tree part of its proof 
(list_requests, root_hash) = jc_tree.tree()
nb_requests = len(list_requests)

# print each node 
# print "root_hash : %s" % root_hash
# jc_util.print_tree(list_requests, "full tree")
# jc_util.print_proof(list_requests)

# create the OP_RETURN transaction with the value of root_hash as the message 
print "2: "
raw_tx = jc_ops.create(unhexlify(root_hash), NET)

# send raw transaction
#print "raw transaction: "+raw_tx
print "3: "
if not DEBUG:
    tx = jc_ops.sendrawtx(raw_tx, NET)
    print "transaction: "+tx

#write proofs in bdd and set status to 3
jc_tree.update_step1(list_requests, tx, NET)

print("--- nb requests : %s " % nb_requests)
print("--- time : %s seconds" % (time.time() - start_time))
