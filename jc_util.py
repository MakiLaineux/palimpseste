#!/usr/bin/python -tt

import sys
import hashlib

def print_bases(nb_tiers, num_tier, num_oldbase, num_newbase):
    print ("************ nbtiers : " + str(nb_tiers)
        + " - tier "+str(num_tier)
        + " - oldbase : " + str(num_oldbase)
        + " - newbase : " + str(num_newbase))

def print_tree(jctree, jctitre):
# print each leaf of some tree with some title 
    print "---- " + jctitre + "--------"
    i=0
    for leaf in jctree:
        print str(i) + ": " + str(leaf)
        i += 1

def print_proof(jctree):
# print each proof until n
    print("----preuves---------")
    i=0
    while i < len(jctree):
        print str(i)
        print str(jctree[i][2])
        i += 1

def allongement(list_lines):
# append dummy lines to list_lines until length of the list is 2**n
    nb = len(list_lines)
    i=nb-1
    nb_etages=0
    while i :
        i=i//2
        nb_etages+=1
    while i < (1<<nb_etages)-nb:
        list_lines.append([999, str(i), ''])
        i+=1
    #returns new list and number of tiers
    return (list_lines, nb_etages)    
    
def proof_start(hash):
    # format : '{"hashdoc":"---"},'
    return("[{\"mix\":\""+hash+"\"},")
    
def proof_part(tier, base, offset, tree):
# matching previous or following hash in current tier, depending on parity of the offset in current tier 
    if (offset % 2) == 0:
        # format : '{"toleftof":"---"},'
        tmp_str = "{\"toleftof\":\""+tree[base+offset+1][1]+"\"},"
    else:
        #format : '{"torightof":"---"},'
        tmp_str = "{\"torightof\":\""+tree[base+offset-1][1]+"\"},"
    return tmp_str

def proof_end(hash, tier):
    #format : '{"treeroot":"---"}'
    return("{\"treeroot\":\""+hash+"\"}]")

def jchash(string1, string2):
# returns the sha256 hash of the concatenation of the two strings passed  
    m = hashlib.sha256()
    m.update(string1)
    m.update(string2)
    return str(m.hexdigest())

