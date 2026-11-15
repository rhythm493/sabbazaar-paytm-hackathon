"""Wiring. Swap `memory_repositories()` for Ridam's ORM repositories here when they land."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Any

from agents.extraction import Extractor, FixtureExtractor, LLMExtractor
from agents.ingestion_graph import GraphDeps, build_ingestion_graph
from agents.models import build_chat_model
from api.service import IngestionService
from api.settings import Settings
from commerce.intake.apply import ApplyService
from commerce.memory import memory_repositories
from commerce.repositories import Repositories
from connectors.fake import FakeConnector
from connectors.registry import ConnectorRegistry
from connectors.shopify.connector import ShopifyConnector
from connectors.shopify.credentials import EnvCredentialsProvider

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    repos: Repositories
    registry: ConnectorRegistry
    service: IngestionService


def build_extractor(settings: Settings) -> Extractor:
    if settings.model_enabled and settings.model_name and settings.model_api_key:
        model = build_chat_model(
            provider=settings.model_provider,
            model=settings.model_name,
            api_key=settings.model_api_key,
            base_url=settings.model_base_url or None,
        )
        return LLMExtractor(model, provider=settings.model_provider, model_name=settings.model_name)
    if settings.model_enabled:
        log.warning("MODEL_ENABLED but MODEL_NAME/MODEL_API_KEY missing; using recorded fixtures")
    return FixtureExtractor.from_dir(settings.fixture_dir)


def build_registry(settings: Settings) -> ConnectorRegistry:
    registry = ConnectorRegistry()
    if settings.channel_mode == "fake":
        registry.register(FakeConnector("shopify"))
    else:
        registry.register(ShopifyConnector(EnvCredentialsProvider()))
    return registry


def build_checkpointer(settings: Settings) -> Any:
    from langgraph.checkpoint.sqlite import SqliteSaver

    settings.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(settings.checkpoint_path, check_same_thread=False))


def build_container(
    settings: Settings | None = None,
    *,
    repos: Repositories | None = None,
    registry: ConnectorRegistry | None = None,
    extractor: Extractor | None = None,
    checkpointer: Any = None,
) -> Container:
    settings = settings or Settings()
    repos = repos or memory_repositories()
    registry = registry or build_registry(settings)
    extractor = extractor or build_extractor(settings)
    checkpointer = checkpointer if checkpointer is not None else build_checkpointer(settings)
    graph = build_ingestion_graph(
        GraphDeps(repos=repos, extractor=extractor, channels=registry.channels), checkpointer
    )
    apply = ApplyService(repos, registry)
    service = IngestionService(repos, graph, registry, apply, settings.upload_dir)
    return Container(settings=settings, repos=repos, registry=registry, service=service)
