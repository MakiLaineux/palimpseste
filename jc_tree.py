#!/usr/bin/python -tt


import sys
import MySQLdb # driver database

import datetime
import jc_error
import jc_util  # jc functions
import json # to handle communication with remote server
import requests # to handle communication with remote server

###############################################################################
# functions handling local MySQL db, remote server communication and trees of hashes
#
# JC november 2018
###############################################################################


def connect_db():
    try:
        db = MySQLdb.connect(host="localhost",    
                     unix_socket="/var/run/mysqld/mysqld.sock", 
                     user="root",         #  username
                     passwd="mysqlroot2017",  # password
                     db="proof")        # local db name
    except:
        sys.exit(jc_error.ERROR_DB_CONNEXION)
    return db

def get_submitted_tx():
    try:
        db = connect_db()
        cur = db.cursor() 
        # select requests with status "3" 
        cur.execute("""SELECT DISTINCT txid FROM tbpalimpsest WHERE status='3';""")
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
def update_step1(list_requests, tx, net="btc-testnet"):
    db = connect_db()
    k = 0     # index on original requests 
    while (k < len(list_requests)):
        #print "Requete %d : %s" % (k, list_requests[k])
        cur = db.cursor()  
        cur.execute("""
           UPDATE tbpalimpsest
           SET status=%s, tree=%s, txid=%s
           WHERE id=%s;
        """, ("3", list_requests[k][2], tx, list_requests[k][0]))
        k += 1
    db.commit()
    db.close()

# -------------------------------------------------------------------------------
# Update requests in local bdd with :
#         - status 4 ("ready") 
#         - chain ("btc-testnet" or "btc-mainnet" for now) 
#         - timestamp of the block
# ------------------------------------------------------------------------------
def local_update_step2(tx, time, net="btc-testnet"):
    date_string = datetime.datetime.utcfromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S')
    db = connect_db()
    cur = db.cursor() 
    cur.execute("""
           UPDATE tbpalimpsest 
           SET status=%s, chain=%s, info=%s 
           WHERE txid=%s;
        """, ("4", net, date_string, tx))
    db.commit()
    db.close()
    

# -------------------------------------------------------------------------------
# For all records with status 4 (ready), update remote db records with :
#         - chain : the chain that was used
#         - txid : the id of the blockchain transaction
#         - tree : the merkle tree for this record
#         - info : the block timestamp
#         - status : 4 ("ready") 
# If successful, update local status to 5 (finished)
# ------------------------------------------------------------------------------
def remote_update_step2(net="btc-testnet"):
    # number of requests processed
    nb_requests_processed = 0
    # get all the records in local db with status 4
    db = connect_db()
    cur = db.cursor() 
    list_record = []
    try:
        request_string = ("""SELECT DISTINCT id, chain, tree, info, txid, status FROM tbpalimpsest WHERE status='4';""")
        cur.execute(request_string)
        for row in cur.fetchall():
            #print(row)
            list_record.append([row[0], row[1], row[2], row[3], row[4], row[5]])
        k=0
        while (k < len(list_record)):
            #print("id type : %s" % type(list_record[k][0]))
            #print("Record id: %s, chain:%s, tree:%s, info: %s, txid: %s, status: %s" % (list_record[k][0], list_record[k][1], list_record[k][2], list_record[k][3], 
            #    list_record[k][4], list_record[k][5], ))
            k += 1
            
    except db.Error as e:
        print("DB Error %s" % e)
    except:
        sys.exit(jc_error.ERROR_GET_RECORDS)
        
    # Update remote records and, if successfull, local status 
    k = 0
    while (k < len(list_record)):
        try:
            request_string = ("http://technoprimates.com/update_proof.php?"
                "idrequest=%s&chain=%s&tree=%s&info=%s&txid=%s" 
                % (str(list_record[k][0]), list_record[k][1], list_record[k][2], list_record[k][3], list_record[k][4]))
            r = requests.get(request_string)
            data = json.loads(r.text)
            b = (long(data[0]['id']) == list_record[k][0])
            if len(data) != 1:
                sys.exit(jc_error.ERROR_INVALID_JSON_RESPONSE)
            if data[0]['id'] != (str(list_record[k][0]).decode("utf-8")):
                sys.exit(jc_error.ERROR_IDS_DONT_MATCH)
            if data[0]['status'] != '4':
                sys.exit(jc_error.ERROR_INVALID_REMOTE_STATUS)
            # all is ok in remote server, update status to 5 in local db
            txt = ("UPDATE tbpalimpsest SET status='5' WHERE id='%s';" % data[0]['id'])
            cur.execute(txt)
            #print("Record %s updated with status 5" % data[0]['id']) 
            k += 1
            nb_requests_processed +=1
        except db.Error as e:
            #print("DB Error %s" % e)
            k += 1
        except:
            #print("Remote query failed, status code : %s" % r.status_code)
            k += 1
            
    db.commit()
    db.close()
    return (nb_requests_processed)

    
# -------------------------------------------------------------------------------
# Insert requests in local db with :
#         - id from remote db
#         - hash from remote db
#         - status 2 ("downloaded")
# ------------------------------------------------------------------------------
def insert_step1():
    db = connect_db()
    cur = db.cursor() 

    #print("--- Query remote server for requests")
    try:
        r = requests.get('http://technoprimates.com/list_status_2.php')
        data = json.loads(r.text)
        #print("Remote query ok, Synchro date: %s, Number of requests: %s" % (data[0]['DateSynchro'], data[0]['NbEnr']))  

    except:
        #print("Remote query failed")
        return()

    #print("--- Remote requests")
    k = 1 #index on list starting at second element
    while (k < len(data)):
        insertid = data[k]['id']
        inserthash = data[k]['hash']
        request = "INSERT INTO tbpalimpsest (id, hash, tree, chain, txid, info, status) VALUES (%s, %s, %s, %s, %s, %s, %s) ;" 
        val = (data[k]['id'], data[k]['hash'], " ", " ", " ", " ", "2")
        try: 
            cur = db.cursor()  
            cur.execute(request, val)
            print("remote query id=%s INSERT OK, hash: %s" % (data[k]['id'], data[k]['hash']))
        except db.Error as e:
            # error may be 1062 (Duplicate entry) if the request was already processed, report only other Mysql errors 
            if e[0] != 1062:
                print("remote query id=%s DB Error [%d]: %s :" % (data[k]['id'], e[0], e[1]))
        except:
            print("Unknown error occured")
    
        k += 1

    #print("--- End of copy")
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
    cur.execute("""SELECT * FROM tbpalimpsest WHERE status='2';""")

    # storage of the results in a python list
    # 0:id, 1:hash, 2:tree
    tree_hashes = []
    for row in cur.fetchall():
        tree_hashes.append([row[0],row[1],row[2]])

    # add dummy rows until number of rows reaches 2**n
    NB_DEM = len(tree_hashes)
    if NB_DEM == 0:
        raise ValueError("no request to process")
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

