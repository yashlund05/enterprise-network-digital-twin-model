"""Enterprise Service Catalog and Dependency Graph Management.

Provides domain modeling, registration, validation, and graph traversal
for enterprise services and their consumer -> provider dependencies.
"""

from __future__ import annotations

import networkx as nx

from telecom_twin.models import EnterpriseService, ServiceDependency


def build_default_service_catalog() -> tuple[list[EnterpriseService], list[ServiceDependency]]:
    """Build the canonical 6-service enterprise catalog and dependency graph.

    Services:
    1. srv-dns: Enterprise DNS (infrastructure, tier-1)
    2. srv-auth: Enterprise Authentication / SSO (security, tier-1, depends on DNS)
    3. srv-db: Enterprise PostgreSQL Database (database, tier-1, depends on DNS)
    4. srv-api: Internal API Gateway (middleware, tier-1, depends on Auth, DB)
    5. srv-erp: Enterprise ERP (application, tier-1, depends on API, DB, Auth)
    6. srv-monitoring: Network & System Monitoring (operations, tier-2, standalone)

    Dependency Convention:
        consumer -> provider
        (e.g., srv-api -> srv-auth, srv-erp -> srv-api)
    """
    services = [
        EnterpriseService(
            service_id="srv-dns",
            name="Enterprise DNS",
            tier="infrastructure",
            host_node_id="host-dns",
            port=53,
            criticality="tier-1",
            health_status="healthy",
        ),
        EnterpriseService(
            service_id="srv-auth",
            name="Enterprise Authentication / SSO",
            tier="security",
            host_node_id="host-auth",
            port=443,
            criticality="tier-1",
            health_status="healthy",
        ),
        EnterpriseService(
            service_id="srv-db",
            name="Enterprise PostgreSQL Database",
            tier="database",
            host_node_id="host-db",
            port=5432,
            criticality="tier-1",
            health_status="healthy",
        ),
        EnterpriseService(
            service_id="srv-api",
            name="Internal API Gateway",
            tier="middleware",
            host_node_id="host-api",
            port=8080,
            criticality="tier-1",
            health_status="healthy",
        ),
        EnterpriseService(
            service_id="srv-erp",
            name="Enterprise ERP",
            tier="application",
            host_node_id="host-erp",
            port=443,
            criticality="tier-1",
            health_status="healthy",
        ),
        EnterpriseService(
            service_id="srv-monitoring",
            name="Network & System Monitoring",
            tier="operations",
            host_node_id="host-mon",
            port=9090,
            criticality="tier-2",
            health_status="healthy",
        ),
    ]

    dependencies = [
        # Auth depends on DNS
        ServiceDependency(
            consumer_service_id="srv-auth",
            provider_service_id="srv-dns",
            dependency_type="synchronous",
        ),
        # Database depends on DNS
        ServiceDependency(
            consumer_service_id="srv-db",
            provider_service_id="srv-dns",
            dependency_type="synchronous",
        ),
        # API Gateway depends on Auth and Database
        ServiceDependency(
            consumer_service_id="srv-api",
            provider_service_id="srv-auth",
            dependency_type="synchronous",
        ),
        ServiceDependency(
            consumer_service_id="srv-api",
            provider_service_id="srv-db",
            dependency_type="synchronous",
        ),
        # ERP depends on Internal API, Database, and Auth
        ServiceDependency(
            consumer_service_id="srv-erp",
            provider_service_id="srv-api",
            dependency_type="synchronous",
        ),
        ServiceDependency(
            consumer_service_id="srv-erp",
            provider_service_id="srv-db",
            dependency_type="synchronous",
        ),
        ServiceDependency(
            consumer_service_id="srv-erp",
            provider_service_id="srv-auth",
            dependency_type="synchronous",
        ),
    ]

    return services, dependencies


class EnterpriseServiceCatalog:
    """Deterministic enterprise service registry and dependency graph manager.

    Maintains a directed acyclic graph (DAG) where directed edges represent:
        consumer -> provider
    """

    def __init__(
        self,
        services: list[EnterpriseService] | None = None,
        dependencies: list[ServiceDependency] | None = None,
    ):
        if services is None and dependencies is None:
            default_services, default_deps = build_default_service_catalog()
            self._services: dict[str, EnterpriseService] = {
                s.service_id: s for s in default_services
            }
            self._dependencies: list[ServiceDependency] = list(default_deps)
        else:
            if services is None:
                default_services, _ = build_default_service_catalog()
                self._services = {s.service_id: s for s in default_services}
            else:
                self._services = {s.service_id: s for s in services}

            if dependencies is None:
                _, default_deps = build_default_service_catalog()
                self._dependencies = list(default_deps)
            else:
                self._dependencies = list(dependencies)

        self._graph = nx.DiGraph()
        for service in self._services.values():
            self._graph.add_node(service.service_id, service=service)

        for dep in self._dependencies:
            self._graph.add_edge(
                dep.consumer_service_id,
                dep.provider_service_id,
                dependency_type=dep.dependency_type,
            )

        self.validate_dependencies()

    def get_all_services(self) -> list[EnterpriseService]:
        """Return all registered services in deterministic order by service_id."""
        return [self._services[sid] for sid in sorted(self._services.keys())]

    def get_service(self, service_id: str) -> EnterpriseService | None:
        """Retrieve an EnterpriseService by its unique ID."""
        return self._services.get(service_id)

    def get_services_by_host(self, host_node_id: str) -> list[EnterpriseService]:
        """Retrieve all services hosted on a specific infrastructure host node."""
        return [
            s for s in self.get_all_services()
            if s.host_node_id == host_node_id
        ]

    def get_direct_dependencies(self, service_id: str) -> list[str]:
        """Return direct providers that the given consumer service depends on.

        Edge direction: consumer -> provider, so direct dependencies are successors.
        """
        if service_id not in self._graph:
            return []
        return sorted(self._graph.successors(service_id))

    def get_transitive_dependencies(self, service_id: str) -> set[str]:
        """Return all direct and indirect providers that the service depends on.

        All reachable nodes along consumer -> provider directed paths.
        """
        if service_id not in self._graph:
            return set()
        return set(nx.descendants(self._graph, service_id))

    def get_direct_consumers(self, provider_id: str) -> list[str]:
        """Return direct consumers that depend on the given provider.

        Edge direction: consumer -> provider, so direct consumers are predecessors.
        """
        if provider_id not in self._graph:
            return []
        return sorted(self._graph.predecessors(provider_id))

    def get_transitive_consumers(self, provider_id: str) -> set[str]:
        """Return all direct and indirect consumers that depend on the given provider.

        All nodes that can reach provider_id along consumer -> provider directed paths.
        """
        if provider_id not in self._graph:
            return set()
        return set(nx.ancestors(self._graph, provider_id))

    def validate_dependencies(self) -> None:
        """Validate that all dependency consumer and provider IDs refer to registered services."""
        for dep in self._dependencies:
            if dep.consumer_service_id not in self._services:
                raise ValueError(
                    f"Dependency references unknown consumer: '{dep.consumer_service_id}'"
                )
            if dep.provider_service_id not in self._services:
                raise ValueError(
                    f"Dependency references unknown provider: '{dep.provider_service_id}'"
                )

    def is_acyclic(self) -> bool:
        """Return True if the dependency graph is a valid directed acyclic graph."""
        return nx.is_directed_acyclic_graph(self._graph)

    def detect_cycles(self) -> list[list[str]]:
        """Return any cycles detected within the service dependency graph."""
        return list(nx.simple_cycles(self._graph))

    @property
    def graph(self) -> nx.DiGraph:
        """Return an immutable/copy view of the internal NetworkX dependency graph."""
        return self._graph.copy()
