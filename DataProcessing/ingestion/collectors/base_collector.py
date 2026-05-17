"""Shared collector interface for all job sources."""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Any, Dict, Iterable, Protocol

import httpx


class ClientFactory(Protocol):
	def __call__(self) -> httpx.Client:  # pragma: no cover - structural type
		...


class Collector(abc.ABC):
	"""Base class that enforces a consistent contract for source adapters."""

	source: str = "unknown"

	def __init__(
		self,
		*,
		since: datetime | None = None,
		client_factory: ClientFactory | None = None,
	) -> None:
		self.since = since
		self._client_factory: ClientFactory = client_factory or (
			lambda: httpx.Client(timeout=30.0)
		)

	@abc.abstractmethod
	def fetch(self) -> Iterable[Dict[str, Any]]:
		"""Yield normalized job postings for the specific source."""

	def run(self) -> Iterable[Dict[str, Any]]:
		"""Wrapper that injects bookkeeping fields shared across sources."""

		for record in self.fetch():
			record.setdefault("source", self.source)
			record.setdefault("retrieved_at", datetime.utcnow().isoformat())
			yield record

	def _prepare_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
		if self.since:
			params.setdefault("since", self.since.isoformat())
		return params
