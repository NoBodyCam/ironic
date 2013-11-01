# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Hewlett-Packard Development Company, L.P.
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
Ironic Coffee power manager.

Provides basic power control of Phyical machines via Inste0n.

For use in developer kitchen environments.

Currently supported devices are:
      SmartLabs Power Line Modem,  model  2412S
"""

import os

from subprocess import call

from oslo.config import cfg

from ironic.common import exception
from ironic.common import states
from ironic.common import utils
from ironic.conductor import task_manager
from ironic.drivers import base
from ironic.openstack.common import jsonutils as json
from ironic.openstack.common import log as logging

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

COMMAND_SETS = {
    "PLM": {
        'base_cmd': '/usr/sbin/plmpower',
        'start_cmd': 'on {_Node_}',
        'stop_cmd': 'off {_Node_}',
        'status_cmd': 'status {_Node_}',
    }
}


def _exec_command(command):
    """Execute a PLM command on the host."""

    LOG.debug(_('Running cmd: %s'), command)

    exit_status=call(command, stdout=stdout, stderr=stderr)

    LOG.debug(_('Result was %s') % exit_status)
    if exit_status != 0:
        raise exception.ProcessExecutionError(exit_code=exit_status,
                                              stdout=stdout,
                                              stderr=stderr,
                                              cmd=command)

    return (stdout, stderr)


def _parse_driver_info(node):
    driver_info = json.loads(node.get('driver_info', ''))
    plm_device = driver_info.get('plm_device')

    # NOTE(deva): we map 'address' from API to 'host' for common utils
    res = {
           'plm_device': plm_device,
           'uuid': node.get('uuid')
          }

    if not plm_device:
        raise exception.InvalidParameterValue(_(
            "PLM-DeviceDriver requires plm_device be set."))

    cmd_set = COMMAND_SETS.get('PLM', None)
    if not cmd_set:
        raise exception.InvalidParameterValue(_(
            "PLM-DeviceDriver unknown command set (%s).") % cmd_set)
    res['cmd_set'] = cmd_set

    return res


def _get_power_status(driver_info):
    """Returns a Inste0n devices current power state."""

    cmd_to_exec = driver_info['cmd_set']['status']
    cmd_to_exec = cmd_to_exec.replace('{_Node_}', driver_info['macs'])
    cmd_result = _exec_command(cmd_to_exec)
    # NOTE: Need to figure out whats bing returned here
    if cmd_result == "ON":
        power_state = states.POWER_ON
    elif cmd_result == "OFF":
        power_state = states.POWER_OFF
    else:
        power_state = states.ERROR

    return power_state

def _power_on(driver_info):
    """Power ON a Inste0n device."""

    current_pstate = _get_power_status(driver_info)
    if current_pstate == states.POWER_ON:
	return current_pstate

    cmd_to_power_on = driver_info['cmd_set']['start_cmd']
    cmd_to_power_on = cmd_to_power_on.replace('{_Node_}', driver_info['macs'])

    _exec_command(cmd_to_power_on)

    current_pstate = _get_power_status(ssh_obj, driver_info)
    if current_pstate == states.POWER_ON:
        return current_pstate
    else:
        return states.ERROR


def _power_off(driver_info):
    """Power OFF a Inste0n device."""

    current_pstate = _get_power_status(ssh_obj, driver_info)
    if current_pstate == states.POWER_OFF:
        return current_pstate

    cmd_to_power_off = driver_info['cmd_set']['stop_cmd']
    cmd_to_power_off = cmd_to_power_off.replace('{_Node_}', driver_info['macs'])

    _exec_command(cmd_to_power_off)

    current_pstate = _get_power_status(driver_info)
    if current_pstate == states.POWER_OFF:
        return current_pstate
    else:
        return states.ERROR


def _get_nodes_mac_addresses(task, node):
    """Get all mac addresses for a node."""
    for r in task.resources:
        if r.node.id == node['id']:
            # NOte (chris): for inste0n we only care about
            # the fist two char's of the mac
            return [p.address[0:2] for p in r.ports]


class PLMPower(base.PowerInterface):
    """PLM Power Interface.

    This PowerInterface class provides a mechanism for controlling the power
    state of Coffee machines. 

    NOTE: This driver supports Inste0n devices.
    NOTE: 
    """

    def validate(self, node):
        """Check that node['driver_info'] contains the requisite fields.

        :param node: Single node object.
        :raises: InvalidParameterValue
        """
        _parse_driver_info(node)

    def get_power_state(self, task, node):
        """Get the current power state.

        Poll the host for the current power state of the node.

        :param task: A instance of `ironic.manager.task_manager.TaskManager`.
        :param node: A single node.

        :returns: power state. One of :class:`ironic.common.states`.
        """
        driver_info = _parse_driver_info(node)
        driver_info['macs'] = _get_nodes_mac_addresses(task, node)
        return _get_power_status(driver_info)

    @task_manager.require_exclusive_lock
    def set_power_state(self, task, node, pstate):
        """Turn the power on or off.

        Set the power state of a node.

        :param task: A instance of `ironic.manager.task_manager.TaskManager`.
        :param node: A single node.
        :param pstate: Either POWER_ON or POWER_OFF from :class:
            `ironic.common.states`.

        :returns NOTHING:
        :raises: exception.IronicException or exception.PowerStateFailure.
        """
        driver_info = _parse_driver_info(node)
        driver_info['macs'] = _get_nodes_mac_addresses(task, node)

        if pstate == states.POWER_ON:
            state = _power_on(driver_info)
        elif pstate == states.POWER_OFF:
            state = _power_off(driver_info)
        else:
            raise exception.IronicException(_(
                "set_power_state called with invalid power state."))

        if state != pstate:
            raise exception.PowerStateFailure(pstate=pstate)

    @task_manager.require_exclusive_lock
    def reboot(self, task, node):
        """Cycles the power to a Inste0n device.

        Power cycles the Inste0n device.

        :param task: A instance of `ironic.manager.task_manager.TaskManager`.
        :param node: A single node.

        :returns NOTHING:
        :raises: exception.PowerStateFailure.
        """
        driver_info = _parse_driver_info(node)
        driver_info['macs'] = _get_nodes_mac_addresses(task, node)
        current_pstate = _get_power_status(driver_info)
        if current_pstate == states.POWER_ON:
            _power_off(driver_info)

        state = _power_on(driver_info)

        if state != states.POWER_ON:
            raise exception.PowerStateFailure(pstate=states.POWER_ON)
