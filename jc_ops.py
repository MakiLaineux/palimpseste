import sys
import datetime
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import logging
from decimal import Decimal
from binascii import hexlify, unhexlify

import jc_error

###############################################################################
#             various functions calling Bitcoin commands via RPC 
# 
# JC Aout 2016
# 
###############################################################################


# -------------------------------------------------------------------------------
# connect to bitcoin daemon via rpc user and password (both defined in bitcoin.conf)
# ------------------------------------------------------------------------------
# enable for verbose logs
#logging.basicConfig()
#logging.getLogger("BitcoinRPC").setLevel(logging.DEBUG)

def rpc_connect(net):
    rpc_user = "lorisrpc"
    rpc_password = "QuandLeCielBasEtLourdPeseCommeUnCouvercleSurLEspritGemissantEnProieAuxLongsEnnuis"
    # port 18332 for testnet, 8332 for mainnet
    try:
        if net == "btc-testnet":
            rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:18332/" % (rpc_user, rpc_password))
        elif net == "btc-mainnet":
            rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:8332/" % (rpc_user, rpc_password))
        else:
            sys.exit(jc_error.ERROR_INVALID_NETWORK)
    except:
        sys.exit(jc_error.ERROR_RPC_CONNEXION)
    return rpc

def gettxid(tx_raw, net="btc-testnet"):
    rpc=rpc_connect(net)
    try:
        return(rpc.decoderawtransaction(tx_raw)["txid"])
    except:
        sys.exit(jc_error.ERROR_DECODE_RAW_TX)

# -------------------------------------------------------------------------------
# selection of an utxo to be spent in the OP_RETURN transaction
# ------------------------------------------------------------------------------
def select_utxo(rpc, fee, confirm):
    # search an utxo with enough amount 
    lst_utxos = rpc.listunspent()
    if len(lst_utxos) == 0:
        sys.exit(jc_error.ERROR_NO_UTXO_FOUND)
    
    i=0
    utxo_found = False
    while (i < len(lst_utxos)) and (not utxo_found) :
        if (lst_utxos[i]["amount"]>fee) and (lst_utxos[i]["confirmations"] >= confirm) :
            utxo_found = True 
        i += 1

    if not utxo_found:
        sys.exit(jc_error.ERROR_NO_MATCHING_UTXO)

    return lst_utxos[i-1]

# -------------------------------------------------------------------------------
# checks the blockchain with a transaction id and returns validation info 
# ------------------------------------------------------------------------------
def txinfo(tx_id, net="btc-testnet"):

    # open rpc connexion
    rpc=rpc_connect(net)

    # get transaction details 
    try:
        tx_info = rpc.gettransaction(tx_id)
        confirmations = tx_info["confirmations"]
        if confirmations <= 0:
            return (True, "", confirmations)
        else:
            return (True, tx_info["blocktime"], confirmations)

    except:
        return (False, "", "")

# -------------------------------------------------------------------------------
# retrieve OP_RETURN message given trannsaction id
#    needs txindex=1 in bitcoin.conf
#    function returns tuple (success, message, timestamp, nb_confirmations)   
# ------------------------------------------------------------------------------
def retrieve(tx_id, net="btc-testnet"):

    # open rpc connexion
    rpc=rpc_connect(net)

    # get transaction details 
    try:
        tx_info = rpc.gettransaction(tx_id)
        tx_raw = rpc.getrawtransaction(tx_id)
        tx_detail = rpc.decoderawtransaction(tx_raw)
    except:
        sys.exit(jc_error.ERROR_RPC_RETRIEVE)

    # scan transaction outputs searching for OP_RETURN script
    # (OP_RETURN scripts begin with hev value '6a') 
    i=0
    message=""
    tstamp=0
    nb_confirmations=0
    is_op_return = False
    
    while i < len(tx_detail["vout"]) and not is_op_return:
        script_hex = tx_detail["vout"][i]["scriptPubKey"]["hex"]
        script_string = script_hex.decode("hex")
        if script_string[0] == "\x6a":
            is_op_return = True
            message = script_string[2:]
            tstamp = tx_info["time"]
            nb_confirmations = tx_info["confirmations"]
        i +=1
    return(is_op_return, message, tstamp, nb_confirmations)

# -------------------------------------------------------------------------------
# create and sign (but does not send) OP_RETURN transactionwith given string message
#    message length is 40 bytes max
# ------------------------------------------------------------------------------
def create(message, net="btc-testnet"):
    #print ("message length: "+str(len(message)))
    if len(message)==0 or len(message)>40:
        sys.exit(jc_error.ERROR_INVALID_MESSAGE_LENGTH)
        
    # open rpc connexion
    rpc=rpc_connect(net)

    # my bitcoin addresses for the change output
    # dummy address will later be owerwritten in the process  
    if net=="btc-testnet":
        ADDRESS_CHANGE = "mpFt9HiwiLpxBsxZWHVEY89AipPd5dj2SQ"
        dummy_address = "mfWxJ45yp2SFn7UciZyNpvDKrzbhyfKrY8"
    else:
        ADDRESS_CHANGE = "13V7qQEXqF7Tv1a6kpvSH8CzbE9pqAXu6m"
        dummy_address = "1111111111111111111114oLvT2"
        
    # OP_RETURN's output has zero amount  
    ZERO = Decimal("0.00000000")
    FEE = Decimal("0.0001")
    NB_MIN_CONFIRM = 6 # use only confirmed UTXOs 

    # search an utxo with enough amount 
    utxo = select_utxo(rpc, FEE, NB_MIN_CONFIRM)

    txid = utxo["txid"]
    vout = utxo['vout']
    input_amount = utxo['amount']
    change_amount = input_amount - FEE

    # create raw transaction
    # first create with a dummy output
    try:
        tx = rpc.createrawtransaction([{"txid": txid, "vout": vout}], \
                              {ADDRESS_CHANGE: change_amount, \
                               dummy_address: ZERO})
    except:
        sys.exit(jc_error.ERROR_CREATE_RAW_TX)
        
    #change the dummy output with the OP_RETURN one
    oldScriptPubKey = "1976a914000000000000000000000000000000000000000088ac"

    tmp = "6a" + hexlify(chr(len(message))) + hexlify(message)
    newScriptPubKey = hexlify(chr(len(unhexlify(tmp)))) + tmp
    tx = tx.replace(oldScriptPubKey, newScriptPubKey)

    # sign the transaction
    try:
        tx = rpc.signrawtransaction(tx)['hex']
    except:
        sys.exit(jc_error.ERROR_SIGNING_RAW_TX)

    return tx

# -------------------------------------------------------------------------------
# send raw transaction
# ------------------------------------------------------------------------------
def sendrawtx(raw_tx, net="btc-testnet"):

    if (len(raw_tx)> 540 or (len(raw_tx)< 400)):
        sys.exit(jc_error.ERROR_INVALID_RAW_TX_LENGTH+str(len(raw_tx)))
        
    # open rpc connexion
    rpc = rpc_connect(net)
    
    try:
        tx = rpc.sendrawtransaction(raw_tx)
    except:
        sys.exit(jc_error.ERROR_SENDING_RAW_TX)

    return tx 
    




