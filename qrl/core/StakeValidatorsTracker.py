# coding=utf-8
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.

from collections import OrderedDict, defaultdict
from pyqrllib.pyqrllib import bin2hstr
from qrl.core import logger, config
from qrl.core.StakeValidator import StakeValidator


class StakeValidatorsTracker:
    """
    Maintains the Stake validators list for current and next epoch
    """
    def __init__(self):
        # FIXME: the name sv_list is confusing because is actually a dictionary
        self.sv_list = OrderedDict()        # Active stake validator objects
        self._expiry = defaultdict(set)     # Maintains the blocknumber as key at which Stake validator has to be expired

        # FIXME: the name future_sv_list is confusing because is actually a dictionary
        self.future_sv_list = defaultdict(set)
        self.future_stake_addresses = dict()

    def calc_seed(self):
        epoch_seed = 0

        for staker in self.sv_list:
            sv = self.sv_list[staker]
            if not sv.hash:
                logger.error('sv.hash could not be empty %s', sv.hash)
                raise Exception
            epoch_seed |= int(bin2hstr(sv.hash), 16)

        return epoch_seed
    def calc_seed(self):
        staker_seeds = [s.hash for s in self.sv_dict.values()]
        return calc_seed(staker_seeds)

    def activate_sv(self, balance, stake_txn):
        sv = StakeValidator(balance, stake_txn)
        self.sv_list[stake_txn.txfrom] = sv
        self._expiry[stake_txn.activation_blocknumber + config.dev.blocks_per_epoch].add(stake_txn.txfrom)

    def activate_future_sv(self, sv):
        self.sv_list[sv.stake_validator] = sv
        self._expiry[sv.activation_blocknumber + config.dev.blocks_per_epoch].add(sv.stake_validator)

    def add_sv(self, balance, stake_txn, blocknumber):
        if stake_txn.activation_blocknumber > blocknumber:
            self.add_future_sv(balance, stake_txn)
        else:
            self.activate_sv(balance, stake_txn)

    def add_future_sv(self, balance, stake_txn):
        sv = StakeValidator(balance, stake_txn)
        self.future_stake_addresses[stake_txn.txfrom] = sv
        self.future_sv_list[stake_txn.activation_blocknumber].add(sv)

    def update_sv(self, blocknumber):
        next_blocknumber = blocknumber + 1
        if next_blocknumber in self._expiry:
            for sv_addr in self._expiry[next_blocknumber]:
                del self.sv_list[sv_addr]
            del self._expiry[next_blocknumber]

        if next_blocknumber in self.future_sv_list:
            sv_set = self.future_sv_list[next_blocknumber]
            for sv in sv_set:
                self.activate_future_sv(sv)
                del self.future_stake_addresses[sv.stake_validator]
            del self.future_sv_list[next_blocknumber]

    def get_sv_list(self, txfrom):
        if txfrom not in self.sv_list:
            return None
        return self.sv_list[txfrom]

    def validate_hash(self, hasharg, blocknum, stake_address=None):
        if stake_address not in self.sv_list:
            return False
        sv = self.sv_list[stake_address]
        return sv.validate_hash(hasharg, blocknum)