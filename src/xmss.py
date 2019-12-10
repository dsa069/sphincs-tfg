"""
XMSS Functions
"""

from src.parameters import *
from src.tweakables import *
from src.adrs import *
from src.wots import *
import math

# Input: Secret seed SK.seed, start index s, target node height z, public seed PK.seed, address ADRS
# Output: n-byte root node - top node on Stack
def treehash(secret_seed, s, z, public_seed, adrs: ADRS):
    if s % (1 << z) != 0:
        return -1

    stack = []

    for i in range(0,2**z):
        adrs.set_type(ADRS.WOTS_HASH)
        adrs.set_key_pair_address(s + i)
        node = wots_pk_gen(secret_seed, public_seed, adrs)
        adrs.set_type(ADRS.TREE)
        adrs.set_tree_height(1)
        adrs.set_tree_index(s + i)

        if len(stack) > 0:
            while stack[len(stack) - 1]['height'] == adrs.get_tree_height():
                adrs.set_tree_index((adrs.get_tree_index() - 1) // 2)
                node = hash(public_seed, adrs, (stack.pop()['node'] + node), n)
                adrs.set_tree_height(adrs.get_tree_height() + 1)
                if len(stack) <= 0:
                    break

        stack.append({'node': node, 'height': adrs.get_tree_height()})

    return stack.pop()['node']


# Input: Secret seed SK.seed, public seed PK.seed, address ADRS
# Output: XMSS public key PK
def xmss_pk_gen(secret_seed, public_key, adrs: ADRS):
    pk = treehash(secret_seed, 0, h_prime, public_key, adrs)
    return pk


# Input: n-byte message M, secret seed SK.seed, index idx, public seed PK.seed, address ADRS
# Output: XMSS signature SIG_XMSS = (sig || AUTH)
def xmss_sign(m, secret_key, idx, public_key, adrs):
    auth = []
    for j in range(0, h_prime):
        k = 0 if math.floor(idx / 2**j) == 1 else 1  # XORING
        auth += [treehash(secret_key, k * 2**j, j, public_key, adrs)]

    adrs.set_type(ADRS.WOTS_HASH)
    adrs.set_key_pair_address(idx)

    sig = wots_sign(m, secret_key, public_key, adrs)
    sig_xmss = sig + auth
    return sig_xmss


# Input: index idx, XMSS signature SIG_XMSS = (sig || AUTH), n-byte message M, public seed PK.seed, address ADRS
# Output: n-byte root value node[0]
def xmss_pk_from_sig(idx, sig_xmss, m, public_seed, adrs):
    adrs.set_type(ADRS.WOTS_HASH)
    adrs.set_key_pair_address(idx)
    sig = sig_wots_from_sig_xmss(sig_xmss)
    auth = auth_from_sig_xmss(sig_xmss)

    node_0 = wots_pk_from_sig(sig, m, public_seed, adrs)
    node_1 = 0

    adrs.set_type(ADRS.TREE)
    adrs.set_tree_index(idx)
    for k in range(0, h_prime):
        adrs.set_tree_height(k + 1)

        if math.floor(idx / 2**k) % 2 == 0:
            adrs.set_tree_index(adrs.get_tree_index() // 2)
            node_1 = hash(public_seed, adrs, node_0 + auth[k])
        else:
            adrs.set_tree_index( (adrs.get_tree_index() - 1) // 2)
            node_1 = hash(public_seed, adrs, auth[k] + node_0)

        node_0 = node_1

    return node_0
