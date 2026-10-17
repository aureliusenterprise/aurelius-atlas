"""Parity scenarios: requests with the responses Apache Atlas 2.4.0 gives, run against Aurelius Atlas (ADR 052)."""

from aurelius_atlas_parity.run import ScenarioFailedError, load_scenarios, run_scenario
from aurelius_atlas_parity.scenario import Scenario, ScenarioError

__all__ = ["Scenario", "ScenarioError", "ScenarioFailedError", "load_scenarios", "run_scenario"]
