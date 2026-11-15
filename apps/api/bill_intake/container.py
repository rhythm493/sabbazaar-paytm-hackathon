"""Wiring. Swap `memory_repositories()` for Ridam's ORM repositories here when they land."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Any

from apps.api.bill_intake.orm_sync import build_orm_sync
from apps.api.bill_intake.service import IngestionService
from apps.api.bill_intake.settings import Settings
from sabbazaar_agents.extraction import Extractor, FixtureExtractor, LLMExtractor
from sabbazaar_agents.ingestion_graph import GraphDeps, build_ingestion_graph
from sabbazaar_agents.models import build_chat_model
from sabbazaar_commerce.intake.apply import ApplyService
from sabbazaar_commerce.memory import memory_repositories
from sabbazaar_commerce.repositories import Repositories
from sabbazaar_connectors.fake import FakeConnector
from sabbazaar_connectors.registry import ConnectorRegistry
from sabbazaar_connectors.shopify_ops.connector import ShopifyConnector
from sabbazaar_connectors.shopify_ops.credentials import EnvCredentialsProvider

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
    on_lines_applied=None,
    on_jobs_run=None,
) -> Container:
    settings = settings or Settings()
    repos = repos or memory_repositories()
    registry = registry or build_registry(settings)
    extractor = extractor or build_extractor(settings)
    checkpointer = checkpointer if checkpointer is not None else build_checkpointer(settings)
    graph = build_ingestion_graph(
        GraphDeps(repos=repos, extractor=extractor, channels=registry.channels), checkpointer
    )
    if on_lines_applied is None and on_jobs_run is None:
        on_lines_applied, on_jobs_run = build_orm_sync(repos)
    apply = ApplyService(
        repos, registry, on_lines_applied=on_lines_applied, on_jobs_run=on_jobs_run
    )
    service = IngestionService(repos, graph, registry, apply, settings.upload_dir)
    return Container(settings=settings, repos=repos, registry=registry, service=service)
