#!/usr/bin/python -tt


import sys
import MySQLdb # driver database

import datetime
import jc_error
import jc_util  # fonctions jc

###############################################################################
# functions handling MySQL bdd and trees of hashes
#
# JC Aout 2016
###############################################################################


def connect_db():
    try:
        db = MySQLdb.connect(host="localhost",    
                     unix_socket="/var/run/mysqld/mysqld.sock", # adresse socket bdd xampp
                     user="root",         #  username
                     passwd="mysqlroot2017",  # password
                     db="proof")        # nom de la base
    except:
        sys.exit(jc_error.ERROR_DB_CONNEXION)
    return db

def get_submitted_tx():
    try:
        db = connect_db()
        cur = db.cursor() 
        # select requests with status "3" 
        cur.execute("""SELECT DISTINCT txid FROM tbrequest WHERE status='3';""")
        # storage of the results in a python list
        list_tx = []
        for row in cur.fetchall():
            list_tx.append(row[0])
    except:
        sys.exit(jc_error.ERROR_GET_SUBMITTED)
    return list_tx

# -------------------------------------------------------------------------------
# Update requests in bdd with :
#         - status 3 ("submitted") 
#         - "tree part" of the proof
#         - id of the submitted OP_RETURN transaction 
# ------------------------------------------------------------------------------
def update_step1(list_requests, tx, net="testnet"):
    db = connect_db()
    k = 0     # index on original requests 
    while (k < len(list_requests)):
        print "Requete %d : %s" % (k, list_requests[k])
        cur = db.cursor()  
        cur.execute("""
           UPDATE tbrequest
           SET status=%s, tree=%s, txid=%s
           WHERE id=%s;
        """, ("3", list_requests[k][2], tx, list_requests[k][0]))
        k += 1
    db.commit()
    db.close()

# -------------------------------------------------------------------------------
# Update requests in bdd with :
#         - status 4 ("ready") 
#         - timestamp of th block
# ------------------------------------------------------------------------------
def update_step2(tx, time, net="testnet"):
    date_string = datetime.datetime.utcfromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S')
    db = connect_db()
    cur = db.cursor() 
    cur.execute("""
           UPDATE tbrequest
           SET status=%s, info=%s
           WHERE txid=%s;
        """, ("4", date_string, tx))
    db.commit()
    db.close()



# -------------------------------------------------------------------------------
# Creation of a list containing each request with its hash and the tree part
# of its proof. This is done by building a Merkle-like tree 
# -------------------------------------------------------------------------------
def tree():
    
    db = connect_db()
    cur = db.cursor() # new cursor for request management 

    # select requests with status "2" 
    cur.execute("""SELECT * FROM tbrequest WHERE status='2';""")

    # storage of the results in a python list
    # 0:id, 3:hash, 4:tree
    tree_hashes = []
    for row in cur.fetchall():
        tree_hashes.append([row[0],row[3],row[4]])

    # add dummy rows until number of rows reaches 2**n
    NB_DEM = len(tree_hashes)
    if NB_DEM == 0:
        sys.exit(jc_error.ERROR_NO_REQUESTS)
    (tree_hashes, NB_TIERS) = jc_util.allongement(tree_hashes)

    # now we build the tree by appending "tiers" of rows 
    # each tier size is half of preceding tier size
    # tier zero consists of the augmented list of requests

    N = 1<<(NB_TIERS)

    # building tree : loop on the tree tiers 
    base = 0
    nextbase = (1<<NB_TIERS)
    i=0 # tier number
    
    while (i < NB_TIERS):
        # building the next tier looping on its leaves 
        k=0 # leaf number within next tier
        while (nextbase + 2 * k) < (2 * N):
            # append leaf number k of next tier, computing its hash from leaves (2k) and (2k+1) of current tier
            tree_hashes.append([i, jc_util.jchash(tree_hashes [base+2*k][1], tree_hashes[base+2*k+1][1]), ''])
            k += 1
        base = nextbase
        nextbase = nextbase + k 
        i += 1
    ROOT=tree_hashes[base][1]

    # now that all the hashes are written in the tree, it remains to write the proof for each orginal request
    # we do this by appending to the proof string one line for each tier
    k = 0                                                          # index on original requests 
    while (k < NB_DEM):
        tree_hashes[k][2]=jc_util.proof_start(tree_hashes[k][1])    # starting line of the proof string for request number k
        index_tier=0                                               # initialize index on tiers
        base_of_current_tier = 0                                   # base line number of tier index_tier (starting with 0)
        offset_in_current_tier = k                                 # offset matching k in tier index_tier (starting with k) 
        size_of_current_tier = N                                   # number of lines in tier index_tier (starting with N)

        while (index_tier < (NB_TIERS)):
            # add one line to the proof string 
            tree_hashes[k][2] += jc_util.proof_part(index_tier, base_of_current_tier, offset_in_current_tier, tree_hashes)
            # prepare next tier
            index_tier += 1        
            base_of_current_tier += size_of_current_tier
            offset_in_current_tier = offset_in_current_tier >> 1
            size_of_current_tier = size_of_current_tier >> 1
        tree_hashes[k][2] += jc_util.proof_end(ROOT, NB_TIERS)
        k += 1;

    # it's done and we only need to keep the first NB_DEM items of the list
    del tree_hashes[NB_DEM:]
    return (tree_hashes, ROOT)

