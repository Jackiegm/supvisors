#!/usr/bin/python
#-*- coding: utf-8 -*-

# ======================================================================
# Copyright 2016 Julien LE CLEACH
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ======================================================================

import sys
import unittest

from mock import Mock, call, patch

from supvisors.tests.base import MockedSupvisors


class DeploymentStrategyTest(unittest.TestCase):
    """ Test case for the deployment strategies of the strategy module. """

    def setUp(self):
        """ Create a dummy supvisors. """
        self.supvisors = MockedSupvisors()
        # add addresses to context
        from supvisors.address import AddressStatus
        from supvisors.ttypes import AddressStates
        def create_address_status(name, address_state, loading):
            address_status = Mock(spec=AddressStatus, address_name=name, state=address_state)
            address_status.loading.return_value = loading
            return address_status
        self.supvisors.context.addresses['10.0.0.0'] = create_address_status('10.0.0.0', AddressStates.SILENT, 0)
        self.supvisors.context.addresses['10.0.0.1'] = create_address_status('10.0.0.1', AddressStates.RUNNING, 50)
        self.supvisors.context.addresses['10.0.0.2'] = create_address_status('10.0.0.2', AddressStates.ISOLATED, 0)
        self.supvisors.context.addresses['10.0.0.3'] = create_address_status('10.0.0.3', AddressStates.RUNNING, 20)
        self.supvisors.context.addresses['10.0.0.4'] = create_address_status('10.0.0.4', AddressStates.UNKNOWN, 0)
        self.supvisors.context.addresses['10.0.0.5'] = create_address_status('10.0.0.5', AddressStates.RUNNING, 80)
        # initialize dummy address mapper with all address names (keep the alpha order)
        self.supvisors.address_mapper.addresses = sorted(self.supvisors.context.addresses.keys())

    def test_is_loading_valid(self):
        """ Test the validity of an address with an additional loading. """
        from supvisors.strategy import AbstractDeploymentStrategy
        strategy = AbstractDeploymentStrategy(self.supvisors)
        # test unknown address
        self.assertTupleEqual((False, 0), strategy.is_loading_valid('10.0.0.10', 1))
        # test not RUNNING address
        self.assertTupleEqual((False, 0), strategy.is_loading_valid('10.0.0.0', 1))
        self.assertTupleEqual((False, 0), strategy.is_loading_valid('10.0.0.2', 1))
        self.assertTupleEqual((False, 0), strategy.is_loading_valid('10.0.0.4', 1))
        # test loaded RUNNING address
        self.assertTupleEqual((False, 50), strategy.is_loading_valid('10.0.0.1', 55))
        self.assertTupleEqual((False, 20), strategy.is_loading_valid('10.0.0.3', 85))
        self.assertTupleEqual((False, 80), strategy.is_loading_valid('10.0.0.5', 25))
        # test not loaded RUNNING address
        self.assertTupleEqual((True, 50), strategy.is_loading_valid('10.0.0.1', 45))
        self.assertTupleEqual((True, 20), strategy.is_loading_valid('10.0.0.3', 75))
        self.assertTupleEqual((True, 80), strategy.is_loading_valid('10.0.0.5', 15))

    def test_get_loading_and_validity(self):
        """ Test the determination of the valid addresses with an additional loading. """
        from supvisors.strategy import AbstractDeploymentStrategy
        strategy = AbstractDeploymentStrategy(self.supvisors)
        # test valid addresses with different additional loadings
        self.assertDictEqual({'10.0.0.0': (False, 0), '10.0.0.1': (True, 50), '10.0.0.2': (False, 0), '10.0.0.3': (True, 20), '10.0.0.4': (False, 0), '10.0.0.5': (True, 80)},
            strategy.get_loading_and_validity('*', 15))
        self.assertDictEqual({'10.0.0.0': (False, 0), '10.0.0.1': (True, 50), '10.0.0.2': (False, 0), '10.0.0.3': (True, 20), '10.0.0.4': (False, 0), '10.0.0.5': (False, 80)},
            strategy.get_loading_and_validity(self.supvisors.context.addresses.keys(), 45))
        self.assertDictEqual({'10.0.0.1': (False, 50), '10.0.0.3': (True, 20), '10.0.0.5': (False, 80)},
            strategy.get_loading_and_validity(['10.0.0.1', '10.0.0.3', '10.0.0.5'], 75))
        self.assertDictEqual({'10.0.0.1': (False, 50), '10.0.0.3': (False, 20), '10.0.0.5': (False, 80)},
            strategy.get_loading_and_validity(['10.0.0.1', '10.0.0.3', '10.0.0.5'], 85))

    def test_sort_valid_by_loading(self):
        """ Test the sorting of the validities of the addresses. """
        from supvisors.strategy import AbstractDeploymentStrategy
        strategy = AbstractDeploymentStrategy(self.supvisors)
        self.assertListEqual([('10.0.0.3', 20), ('10.0.0.1', 50), ('10.0.0.5', 80)],
            strategy.sort_valid_by_loading({'10.0.0.0': (False, 0), '10.0.0.1': (True, 50), '10.0.0.2': (False, 0), '10.0.0.3': (True, 20), '10.0.0.4': (False, 0), '10.0.0.5': (True, 80)}))
        self.assertListEqual([('10.0.0.3', 20)],
            strategy.sort_valid_by_loading({'10.0.0.1': (False, 50), '10.0.0.3': (True, 20), '10.0.0.5': (False, 80)}))
        self.assertListEqual([],
            strategy.sort_valid_by_loading({'10.0.0.1': (False, 50), '10.0.0.3': (False, 20), '10.0.0.5': (False, 80)}))

    def test_config_strategy(self):
        """ Test the choice of an address according to the CONFIG strategy. """
        from supvisors.strategy import ConfigStrategy
        strategy = ConfigStrategy(self.supvisors)
        # test CONFIG strategy with different values
        self.assertEqual('10.0.0.1', strategy.get_address('*', 15))
        self.assertEqual('10.0.0.1', strategy.get_address('*', 45))
        self.assertEqual('10.0.0.3', strategy.get_address('*', 75))
        self.assertIsNone(strategy.get_address('*', 85))

    def test_less_loaded_strategy(self):
        """ Test the choice of an address according to the LESS_LOADED strategy. """
        from supvisors.strategy import LessLoadedStrategy
        strategy = LessLoadedStrategy(self.supvisors)
        # test LESS_LOADED strategy with different values
        self.assertEqual('10.0.0.3', strategy.get_address('*', 15))
        self.assertEqual('10.0.0.3', strategy.get_address('*', 45))
        self.assertEqual('10.0.0.3', strategy.get_address('*', 75))
        self.assertIsNone(strategy.get_address('*', 85))

    def test_most_loaded_strategy(self):
        """ Test the choice of an address according to the MOST_LOADED strategy. """
        from supvisors.strategy import MostLoadedStrategy
        strategy = MostLoadedStrategy(self.supvisors)
        # test MOST_LOADED strategy with different values
        self.assertEqual('10.0.0.5', strategy.get_address('*', 15))
        self.assertEqual('10.0.0.1', strategy.get_address('*', 45))
        self.assertEqual('10.0.0.3', strategy.get_address('*', 75))
        self.assertIsNone(strategy.get_address('*', 85))

    def test_get_address(self):
        """ Test the choice of an address according to a strategy. """
        from supvisors.ttypes import DeploymentStrategies
        from supvisors.strategy import get_address
        # test CONFIG strategy
        self.assertEqual('10.0.0.1', get_address(self.supvisors, DeploymentStrategies.CONFIG, '*', 15))
        self.assertEqual('10.0.0.3', get_address(self.supvisors, DeploymentStrategies.CONFIG, '*', 75))
        self.assertIsNone(get_address(self.supvisors, DeploymentStrategies.CONFIG, '*', 85))
        # test LESS_LOADED strategy
        self.assertEqual('10.0.0.3', get_address(self.supvisors, DeploymentStrategies.LESS_LOADED, '*', 15))
        self.assertEqual('10.0.0.3', get_address(self.supvisors, DeploymentStrategies.LESS_LOADED, '*', 75))
        self.assertIsNone(get_address(self.supvisors, DeploymentStrategies.LESS_LOADED, '*', 85))
        # test MOST_LOADED strategy
        self.assertEqual('10.0.0.5', get_address(self.supvisors, DeploymentStrategies.MOST_LOADED, '*', 15))
        self.assertEqual('10.0.0.3', get_address(self.supvisors, DeploymentStrategies.MOST_LOADED, '*', 75))
        self.assertIsNone(get_address(self.supvisors, DeploymentStrategies.MOST_LOADED, '*', 85))


class ConciliationStrategyTest(unittest.TestCase):
    """ Test case for the conciliation strategies of the strategy module. """

    def setUp(self):
        """ Create a Supvisors-like structure and conflicting processes. """
        from supvisors.process import ProcessStatus
        self.supvisors = MockedSupvisors()
        # create conflicting processes
        def create_process_status(name, timed_addresses):
            process_status = Mock(spec=ProcessStatus, process_name=name,
                addresses=set(timed_addresses.keys()),
                infos={address_name: {'uptime': time} for address_name, time in timed_addresses.items()},
                mark_for_restart=False)
            process_status.namespec.return_value = name
            return process_status
        self.conflicts = [create_process_status('conflict_1', {'10.0.0.1': 5, '10.0.0.2': 10, '10.0.0.3': 15}),
            create_process_status('conflict_2', {'10.0.0.4': 6, '10.0.0.2': 5, '10.0.0.0': 4})]

    def test_senicide_strategy(self):
        """ Test the strategy that consists in stopping the oldest processes. """
        from supvisors.strategy import SenicideStrategy
        strategy = SenicideStrategy(self.supvisors)
        strategy.conciliate(self.conflicts)
        # check that the oldest processes are requested to stop on the relevant addresses
        self.assertItemsEqual([call('10.0.0.2', 'conflict_1'), call('10.0.0.3', 'conflict_1'),
            call('10.0.0.4', 'conflict_2'), call('10.0.0.2', 'conflict_2')],
            self.supvisors.zmq.pusher.send_stop_process.call_args_list)
        # check that all processes are not marked for a restart
        for process in self.conflicts:
            self.assertFalse(process.mark_for_restart)

    def test_infanticide_strategy(self):
        """ Test the strategy that consists in stopping the youngest processes. """
        from supvisors.strategy import InfanticideStrategy
        strategy = InfanticideStrategy(self.supvisors)
        strategy.conciliate(self.conflicts)
        # check that the youngest processes are requested to stop on the relevant addresses
        self.assertItemsEqual([call('10.0.0.1', 'conflict_1'), call('10.0.0.2', 'conflict_1'),
            call('10.0.0.2', 'conflict_2'), call('10.0.0.0', 'conflict_2')],
            self.supvisors.zmq.pusher.send_stop_process.call_args_list)
        # check that all processes are not marked for a restart
        for process in self.conflicts:
            self.assertFalse(process.mark_for_restart)

    def test_user_strategy(self):
        """ Test the strategy that consists in doing nothing (trivial). """
        from supvisors.strategy import UserStrategy
        strategy = UserStrategy(self.supvisors)
        strategy.conciliate(self.conflicts)
        # check that no processes are requested to stop
        self.assertEqual(0, self.supvisors.zmq.pusher.send_stop_process.call_count)
    # check that all processes are not marked for a restart
        for process in self.conflicts:
            self.assertFalse(process.mark_for_restart)

    def test_stop_strategy(self):
        """ Test the strategy that consists in stopping all processes. """
        from supvisors.strategy import StopStrategy
        strategy = StopStrategy(self.supvisors)
        strategy.conciliate(self.conflicts)
        # check that all processes are requested to stop on the relevant addresses
        self.assertItemsEqual([call('10.0.0.1', 'conflict_1'), call('10.0.0.2', 'conflict_1'), call('10.0.0.3', 'conflict_1'),
            call('10.0.0.4', 'conflict_2'), call('10.0.0.2', 'conflict_2'), call('10.0.0.0', 'conflict_2')],
            self.supvisors.zmq.pusher.send_stop_process.call_args_list)
        # check that all processes are not marked for a restart
        for process in self.conflicts:
            self.assertFalse(process.mark_for_restart)

    def test_restart_strategy(self):
        """ Test the strategy that consists in stopping all processes and restart a single one. """
        from supvisors.strategy import RestartStrategy
        strategy = RestartStrategy(self.supvisors)
        strategy.conciliate(self.conflicts)
        # check that all processes are requested to stop on the relevant addresses
        self.assertItemsEqual([call('10.0.0.1', 'conflict_1'), call('10.0.0.2', 'conflict_1'), call('10.0.0.3', 'conflict_1'),
            call('10.0.0.4', 'conflict_2'), call('10.0.0.2', 'conflict_2'), call('10.0.0.0', 'conflict_2')],
            self.supvisors.zmq.pusher.send_stop_process.call_args_list)
        # check that all processes are marked for a restart
        for process in self.conflicts:
            self.assertTrue(process.mark_for_restart)

    @patch('supvisors.strategy.SenicideStrategy.conciliate')
    @patch('supvisors.strategy.InfanticideStrategy.conciliate')
    @patch('supvisors.strategy.UserStrategy.conciliate')
    @patch('supvisors.strategy.StopStrategy.conciliate')
    @patch('supvisors.strategy.RestartStrategy.conciliate')
    def test_conciliation(self, mocked_restart, mocked_stop, mocked_user,
        mocked_infanticide, mocked_senicide):
        """ Test the actions on process according to a strategy. """
        from supvisors.ttypes import ConciliationStrategies
        from supvisors.strategy import conciliate
        # test senicide conciliation
        conciliate(self.supvisors, ConciliationStrategies.SENICIDE, self.conflicts)
        self.assertEqual([call(self.conflicts)], mocked_senicide.call_args_list)
        self.assertEqual(0, mocked_infanticide.call_count)
        self.assertEqual(0, mocked_user.call_count)
        self.assertEqual(0, mocked_stop.call_count)
        self.assertEqual(0, mocked_restart.call_count)
        mocked_senicide.reset_mock()
        # test infanticide conciliation
        conciliate(self.supvisors, ConciliationStrategies.INFANTICIDE, self.conflicts)
        self.assertEqual(0, mocked_senicide.call_count)
        self.assertEqual([call(self.conflicts)], mocked_infanticide.call_args_list)
        self.assertEqual(0, mocked_user.call_count)
        self.assertEqual(0, mocked_stop.call_count)
        self.assertEqual(0, mocked_restart.call_count)
        mocked_infanticide.reset_mock()
        # test user conciliation
        conciliate(self.supvisors, ConciliationStrategies.USER, self.conflicts)
        self.assertEqual(0, mocked_senicide.call_count)
        self.assertEqual(0, mocked_infanticide.call_count)
        self.assertEqual([call(self.conflicts)], mocked_user.call_args_list)
        self.assertEqual(0, mocked_stop.call_count)
        self.assertEqual(0, mocked_restart.call_count)
        mocked_user.reset_mock()
        # test stop conciliation
        conciliate(self.supvisors, ConciliationStrategies.STOP, self.conflicts)
        self.assertEqual(0, mocked_senicide.call_count)
        self.assertEqual(0, mocked_infanticide.call_count)
        self.assertEqual(0, mocked_user.call_count)
        self.assertEqual([call(self.conflicts)], mocked_stop.call_args_list)
        self.assertEqual(0, mocked_restart.call_count)
        mocked_stop.reset_mock()
        # test restart conciliation
        conciliate(self.supvisors, ConciliationStrategies.RESTART, self.conflicts)
        self.assertEqual(0, mocked_senicide.call_count)
        self.assertEqual(0, mocked_infanticide.call_count)
        self.assertEqual(0, mocked_user.call_count)
        self.assertEqual(0, mocked_stop.call_count)
        self.assertEqual([call(self.conflicts)], mocked_restart.call_args_list)


def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

