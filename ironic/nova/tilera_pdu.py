# vim: tabstop=4 shiftwidth=4 softtabstop=4
# coding=utf-8

# Copyright (c) 2011-2013 University of Southern California / ISI
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Baremetal PDU power manager.
"""

import time

from oslo.config import cfg

from ironic.common import exception
from ironic.common import states
from ironic.common import utils
from ironic.manager import base
from ironic.openstack.common import log as logging

opts = [
    cfg.StrOpt('tile_pdu_ip',
               default='10.0.100.1',
               help='ip address of tilera pdu'),
    cfg.StrOpt('tile_pdu_mgr',
               default='/tftpboot/pdu_mgr',
               help='management script for tilera pdu'),
    cfg.IntOpt('tile_pdu_off',
               default=2,
               help='power status of tilera PDU is OFF'),
    cfg.IntOpt('tile_pdu_on',
               default=1,
               help='power status of tilera PDU is ON'),
    cfg.IntOpt('tile_pdu_status',
               default=9,
               help='power status of tilera PDU'),
    cfg.IntOpt('tile_power_wait',
               default=9,
               help='wait time in seconds until check the result '
                    'after tilera power operations'),
    ]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class Pdu(base.PowerManager):
    """PDU Power Driver for Baremetal Nova Compute

    This PowerManager class provides mechanism for controlling the power state
    of physical hardware via PDU calls.
    """

    def __init__(self, node, **kwargs):
        self.state = None
        self.retries = None
        self.node_id = node['id']
        self.address = node['pm_address']
        self.user = node['pm_user']
        self.password = node['pm_password']
        self.port = node['terminal_port']

        if self.node_id is None:
            raise exception.InvalidParameterValue(_("Node id not supplied "
                "to PDU"))
        if self.address is None:
            raise exception.InvalidParameterValue(_("Address not supplied "
                "to PDU"))
        if self.user is None:
            raise exception.InvalidParameterValue(_("User not supplied "
                "to PDU"))
        if self.password is None:
            raise exception.InvalidParameterValue(_("Password not supplied "
                "to PDU"))

    def _exec_pdutool(self, mode):
        """Changes power state of the given node.

        According to the mode (1-ON, 2-OFF, 3-REBOOT), power state can be
        changed. /tftpboot/pdu_mgr script handles power management of
        PDU (Power Distribution Unit).
        """
        if mode == CONF.tile_pdu_status:
            try:
                utils.execute('ping', '-c1', self.address,
                       check_exit_code=True)
                return CONF.tile_pdu_on
            except exception.ProcessExecutionError:
                return CONF.tile_pdu_off
        else:
            try:
                utils.execute(CONF.tile_pdu_mgr,
                              CONF.tile_pdu_ip, mode)
                time.sleep(CONF.tile_power_wait)
                return mode
            except exception.ProcessExecutionError:
                LOG.exception(_("PDU failed"))

    def _is_power(self, state):
        out_err = self._exec_pdutool(CONF.tile_pdu_status)
        return out_err == state

    def _power_on(self):
        """Turn the power to this node ON."""

        try:
            self._exec_pdutool(CONF.tile_pdu_on)
            if self._is_power(CONF.tile_pdu_on):
                self.state = states.ACTIVE
            else:
                self.state = states.ERROR
        except Exception:
            self.state = states.ERROR
            LOG.exception(_("PDU power on failed"))

    def _power_off(self):
        """Turn the power to this node OFF."""

        try:
            self._exec_pdutool(CONF.tile_pdu_off)
            if self._is_power(CONF.tile_pdu_off):
                self.state = states.DELETED
            else:
                self.state = states.ERROR
        except Exception:
            self.state = states.ERROR
            LOG.exception(_("PDU power off failed"))

    def activate_node(self):
        """Turns the power to node ON."""
        if (self._is_power(CONF.tile_pdu_on)
            and self.state == states.ACTIVE):
            LOG.warning(_("Activate node called, but node %s "
                          "is already active") % self.address)
        self._power_on()
        return self.state

    def reboot_node(self):
        """Cycles the power to a node."""
        self._power_off()
        self._power_on()
        return self.state

    def deactivate_node(self):
        """Turns the power to node OFF, regardless of current state."""
        self._power_off()
        return self.state

    def is_power_on(self):
        return self._is_power(CONF.tile_pdu_on)

    def start_console(self):
        pass

    def stop_console(self):
        pass
