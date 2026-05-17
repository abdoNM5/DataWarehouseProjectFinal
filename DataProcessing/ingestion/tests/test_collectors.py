"""Unit tests for ingestion collectors."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List

from ingestion.collectors.base_collector import Collector
from ingestion.collectors.france_travail_collector import FranceTravailCollector
from ingestion.collectors.indeed_collector import IndeedCollector
from ingestion.collectors.linkedin_collector import LinkedInCollector


class DummyCollector(Collector):
	source = "dummy"

	def fetch(self) -> Iterable[Dict[str, Any]]:
		yield {"job_id": "1"}


def test_base_collector_run_adds_housekeeping_fields() -> None:
	record = next(DummyCollector().run())
	assert record["source"] == "dummy"
	assert "retrieved_at" in record


class FakeResponse:
	def __init__(self, payload: Dict[str, Any]):
		self.payload = payload
		self.status_checked = False

	def raise_for_status(self) -> None:
		self.status_checked = True

	def json(self) -> Dict[str, Any]:
		return self.payload


class FakeClient:
	def __init__(self, response: FakeResponse):
		self.response = response
		self.request_args: tuple[Any, ...] | None = None
		self.request_kwargs: Dict[str, Any] | None = None

	def get(self, *args: Any, **kwargs: Any) -> FakeResponse:
		self.request_args = args
		self.request_kwargs = kwargs
		return self.response

	def __enter__(self) -> "FakeClient":
		return self

	def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - no cleanup
		return None


def test_indeed_collector_fetches_and_normalizes() -> None:
	payload = {"results": [{"job_id": "xyz", "title": "Data Scientist", "description": "desc"}]}
	response = FakeResponse(payload)
	client = FakeClient(response)
	collector = IndeedCollector(api_key="token", client_factory=lambda: client)

	records = list(collector.run())

	assert response.status_checked is True
	assert client.request_kwargs is not None
	assert client.request_kwargs["params"]["q"] == "data"
	assert records[0]["job_id"] == "xyz"


def test_linkedin_collector_uses_token_and_returns_jobs() -> None:
	payload = {
		"elements": [
			{
				"jobPosting": {
					"title": "ML Engineer",
					"description": {"text": "Build models"},
					"listedAt": int(datetime(2026, 3, 1).timestamp() * 1000),
				},
				"jobPostingUrn": "urn:job:123",
			}
		]
	}
	response = FakeResponse(payload)
	client = FakeClient(response)
	collector = LinkedInCollector(client_factory=lambda: client)
	collector._retrieve_token = lambda: "token"  # type: ignore[method-assign]

	records = list(collector.run())

	assert records[0]["job_id"] == "urn:job:123"
	assert "Build models" in records[0]["description"]


def test_france_travail_collector_maps_salary() -> None:
	payload = {
		"resultats": [
			{
				"id": "ft-1",
				"intitule": "Data Analyst",
				"salaire": {"min": 40_000, "max": 55_000, "unite": "EUR"},
				"competences": [{"libelle": "Python"}],
			}
		]
	}
	response = FakeResponse(payload)
	client = FakeClient(response)
	collector = FranceTravailCollector(client_factory=lambda: client)

	records = list(collector.run())

	assert records[0]["salary_min"] == 40000
	assert records[0]["skills"] == ["Python"]
