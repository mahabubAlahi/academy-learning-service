# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This package contains the rounds of TestAbciApp."""

from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    CollectSameUntilThresholdRound,
    CollectionRound,
    DegenerateRound,
    EventToTimeout,
    get_name,
    DeserializedCollection,
)

from packages.valory.skills.assignment_abci.payloads import (
    NewDataPullPayload,
)


class Event(Enum):
    """TestAbciApp Events"""

    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    DONE = "done"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """
    def _get_deserialized(self, key: str) -> DeserializedCollection:
        """Strictly get a collection and return it deserialized."""
        serialized = self.db.get_strict(key)
        return CollectionRound.deserialize_collection(serialized)
    
    @property
    def participant_to_data_round(self) -> DeserializedCollection:
        """Agent to payload mapping for the DataPullRound."""
        return self._get_deserialized("participant_to_data_round")


class NewDataPullRound(CollectSameUntilThresholdRound):
    """NewDataPullRound"""

    payload_class = NewDataPullPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY

    # Collection key specifies where in the synchronized data the agento to payload mapping will be stored
    collection_key = get_name(SynchronizedData.participant_to_data_round)

    # Selection key specifies how to extract all the different objects from each agent's payload
    # and where to store it in the synchronized data. Notice that the order follows the same order
    # from the payload class.
    selection_key = (
        get_name(SynchronizedData.total_holdings),
        get_name(SynchronizedData.total_value_usd),
        get_name(SynchronizedData.market_cap_dominance),
        get_name(SynchronizedData.public_company_holdings_ipfs_hash),
    )

    # Event.ROUND_TIMEOUT  # this needs to be referenced for static checkers


class FinishedNewDataPullRoundRound(DegenerateRound):
    """FinishedNewDataPullRoundRound"""


class TestAbciApp(AbciApp[Event]):
    """TestAbciApp"""

    initial_round_cls: AppState = NewDataPullRound
    initial_states: Set[AppState] = {NewDataPullRound}
    transition_function: AbciAppTransitionFunction = {
        NewDataPullRound: {
            Event.DONE: FinishedNewDataPullRoundRound,
            Event.NO_MAJORITY: NewDataPullRound,
            Event.ROUND_TIMEOUT: NewDataPullRound
        },
        FinishedNewDataPullRoundRound: {}
    }
    final_states: Set[AppState] = {FinishedNewDataPullRoundRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        NewDataPullRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedNewDataPullRoundRound: [],
    }
