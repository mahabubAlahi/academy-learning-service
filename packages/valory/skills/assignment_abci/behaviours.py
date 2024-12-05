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

"""This package contains round behaviours of TestAbciApp."""

from abc import ABC
from typing import Generator, Optional, Set, Type, cast

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype
from packages.valory.skills.assignment_abci.models import CoingeckoPublicCompanyHoldingsSpecs, Params
from packages.valory.skills.assignment_abci.rounds import (
    SynchronizedData,
    TestAbciApp,
    NewDataPullRound,
)
from packages.valory.skills.assignment_abci.rounds import (
    NewDataPullPayload,
)


class TestBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the assignment_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)
    
    @property
    def coingecko_public_company_holdings_specs(self) -> CoingeckoPublicCompanyHoldingsSpecs:
        """Get the Coingecko public company holdings api specs."""
        return self.context.coingecko_public_company_holdings_specs


class NewDataPullBehaviour(TestBaseBehaviour):
    """NewDataPullBehaviour"""

    """This behaviours pulls public companies’ ethereum holdings from API endpoints"""

    matching_round: Type[AbstractRound] = NewDataPullRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address

            # A method to call an API: use ApiSpecs
            response = yield from self.get_public_company_holdings_specs()

            self.context.logger.info(f"Got public company holding from Coingecko: {response}")

            # Store the public company holdings data in IPFS
            public_company_holdings_ipfs_hash = yield from self.send_public_company_holdings_to_ipfs(response)

            # Prepare the payload to be shared with other agents
            # After consensus, all the agents will have the same total_holdings, total_value_usd and market_cap_dominance variables in their synchronized data
            payload = NewDataPullPayload(
                sender=sender,
                total_holdings=response["total_holdings"],
                total_value_usd=response["total_value_usd"],
                market_cap_dominance=response["market_cap_dominance"],
                public_company_holdings_ipfs_hash=public_company_holdings_ipfs_hash
            )

        # Send the payload to all agents and mark the behaviour as done
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()
    
    def get_public_company_holdings_specs(self) -> Generator[None, None, Optional[dict]]:
        """Get company holdings from Coingecko using ApiSpecs"""

        # Get the specs
        specs = self.coingecko_public_company_holdings_specs.get_spec()

        # Make the call
        raw_response = yield from self.get_http_response(**specs)

        # Process the response
        response = self.coingecko_public_company_holdings_specs.process_response(raw_response)

        self.context.logger.info(f"Got public company holding from Coingecko: {response}")
        return response
    
    def send_public_company_holdings_to_ipfs(self, data) -> Generator[None, None, Optional[str]]:
        """Store the public company holdings in IPFS"""
        public_company_holdings_ipfs_hash = yield from self.send_to_ipfs(
            filename=self.metadata_filepath, obj=data, filetype=SupportedFiletype.JSON
        )
        self.context.logger.info(
            f"Public company holdings data stored in IPFS: https://gateway.autonolas.tech/ipfs/{public_company_holdings_ipfs_hash}"
        )
        return public_company_holdings_ipfs_hash


class TestRoundBehaviour(AbstractRoundBehaviour):
    """TestRoundBehaviour"""

    initial_behaviour_cls = NewDataPullBehaviour
    abci_app_cls = TestAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        NewDataPullBehaviour
    ]
