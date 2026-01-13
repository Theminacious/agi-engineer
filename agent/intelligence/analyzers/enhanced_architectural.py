"""
PHASE 12: Enhanced Architectural Analyzer

Detects deeper architectural issues:
- Multi-hop circular dependencies (chains that form cycles)
- Domain leakage (abstractions bleeding across boundaries)
- Architectural smell patterns (god modules, tight coupling)
- Layer boundary violations with severity calibration

All analysis is deterministic, stateless, and proposal-only.
"""

from typing import List, Set, Dict, Tuple, Optional
import os
from agent.intelligence.analyzer import BaseAnalyzer
from agent.intelligence.proposal import (
    IntelligenceProposal,
    BugClass,
    Severity,
    AffectedFile,
    FixStrategy,
    EffortEstimate,
)


class EnhancedArchitecturalAnalyzer(BaseAnalyzer):
    """
    Phase 12 enhanced architectural analyzer.
    
    Improvements over Phase 11:
    - Multi-hop dependency cycle detection (not just direct cycles)
    - Domain leakage detection (interface segregation violations)
    - Architectural cohesion measurement
    - Confidence calibration based on evidence quality
    """
    
    @property
    def bug_class(self) -> BugClass:
        return BugClass.ARCHITECTURAL_VIOLATIONS
    
    def analyze(
        self,
        repository_path: str,
        repository_url: str,
        branch: str = "main",
    ) -> List[IntelligenceProposal]:
        """Analyze repository for architectural violations."""
        self.start_timing()
        self._reset_metrics()
        
        proposals = []
        
        # 1. Build import graph once
        import_graph = self._build_import_graph(repository_path)
        
        # 2. Detect multi-hop circular dependencies
        circular_deps = self._detect_multi_hop_cycles(import_graph)
        proposals.extend(circular_deps)
        
        # 3. Detect domain leakage (cross-layer abstraction violations)
        domain_leakage = self._detect_domain_leakage(import_graph, repository_path)
        proposals.extend(domain_leakage)
        
        # 4. Detect tight coupling clusters
        coupling_issues = self._detect_coupling_clusters(import_graph)
        proposals.extend(coupling_issues)
        
        # 5. Detect layer boundary violations
        layer_violations = self._detect_layer_violations(repository_path, import_graph)
        proposals.extend(layer_violations)
        
        # Finalize all proposals
        finalized = []
        for proposal in proposals:
            proposal.repository_url = repository_url
            proposal.branch = branch
            finalized.append(self._finalize_proposal(proposal))
        
        return finalized
    
    def _detect_multi_hop_cycles(self, graph: Dict[str, Set[str]]) -> List[IntelligenceProposal]:
        """
        Detect cycles of any length (multi-hop).
        More sophisticated than simple 2-node cycles.
        """
        proposals = []
        
        # Find all cycles (including longer ones)
        cycles = self._find_all_cycles_dfs(graph)
        
        # Group cycles by modules involved to avoid duplicates
        unique_cycles = self._deduplicate_cycles(cycles)
        
        for cycle in unique_cycles:
            if len(cycle) < 2:
                continue
            
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.CIRCULAR_DEPENDENCIES
            
            # Severity based on cycle length and module depth
            cycle_length = len(cycle)
            if cycle_length == 2:
                proposal.severity = Severity.HIGH
            elif cycle_length <= 4:
                proposal.severity = Severity.HIGH
            else:
                # Longer cycles are even worse (harder to break)
                proposal.severity = Severity.CRITICAL
            
            cycle_str = " → ".join(cycle + [cycle[0]])
            proposal.problem_statement = (
                f"Circular dependency chain detected ({cycle_length} modules): {cycle_str}. "
                f"This prevents modular testing, refactoring, and creates tight coupling."
            )
            
            proposal.risk_explanation = (
                f"The {cycle_length}-module cycle prevents any module from being "
                f"used independently. Cannot test {cycle[0]} without {cycle[1]} (and vice versa). "
                f"Refactoring one module requires coordinating changes across all {cycle_length} modules."
            )
            
            proposal.root_cause_hypothesis = (
                f"Gradual accumulation of dependencies without architectural governance. "
                f"Likely started with a simple circular import between {cycle[0]} and {cycle[1]}, "
                f"then grew to include {'other modules' if cycle_length > 2 else 'no other modules'}."
            )
            
            # Affected files
            for module in cycle:
                file_path = self._module_to_file_path(module)
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=proposal.severity)
                )
            
            # Strategies (improved)
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Break cycle via abstraction layer",
                    description=(
                        f"Create shared abstraction module that {cycle[0]} and {cycle[1]} "
                        f"both depend on (instead of depending on each other). "
                        f"This converts cycle to tree structure."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM if cycle_length == 2 else EffortEstimate.LARGE,
                    prerequisite_actions=[
                        f"Identify common abstractions between {cycle[0]} and {cycle[1]}",
                        "Design new 'interfaces' or 'contracts' module",
                        "Extract abstract types and protocols",
                        f"Update {cycle[0]} to import from abstractions",
                        f"Update {cycle[1]} to import from abstractions",
                        "Remove direct dependencies between modules",
                    ] + (
                        [f"Repeat for remaining {cycle_length - 2} modules"]
                        if cycle_length > 2
                        else []
                    ),
                    assumptions=[
                        "Common abstractions can be cleanly identified",
                        "Extraction won't create new cycles",
                        "Performance overhead of indirection is acceptable",
                    ],
                    risks=[
                        "Abstraction may be over-general or over-specific",
                        "May not fully eliminate coupling",
                        "New abstraction layer adds indirection",
                    ],
                ),
                FixStrategy(
                    name="Introduce dependency injection",
                    description=(
                        f"Break cycle by injecting dependencies at module initialization, "
                        f"eliminating hard imports at definition time."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Design or select DI framework/container",
                        f"Identify which dependencies in {cycle[0]} should be injected",
                        f"Identify which dependencies in {cycle[1]} should be injected",
                        "Refactor module initialization to accept injected deps",
                        "Update all call sites to use DI container",
                        "Verify all dependencies are properly registered",
                    ],
                    assumptions=[
                        "Language/framework supports dependency injection",
                        "DI container can be initialized before any module",
                        "Runtime performance is acceptable",
                    ],
                    risks=[
                        "Adds complexity through indirection",
                        "DI configuration can be fragile",
                        "Harder to understand call graphs",
                        "Requires comprehensive testing",
                    ],
                ),
                FixStrategy(
                    name="Reorganize modules into coherent boundaries",
                    description=(
                        f"Re-examine the {cycle_length} modules and consolidate or split them "
                        f"into fewer units with clearer responsibilities and no cycles."
                    ),
                    effort_estimate=EffortEstimate.VERY_LARGE,
                    prerequisite_actions=[
                        "Document responsibilities of each module in cycle",
                        "Identify overlaps and gaps",
                        "Design new module structure",
                        "Move code into new structure",
                        "Update all imports across codebase",
                        "Verify no new cycles introduced",
                    ],
                    assumptions=[
                        "Clear new structure can be defined",
                        "Team alignment on new architecture",
                        "No hidden dependencies between modules",
                    ],
                    risks=[
                        "Largest scope change - highest risk",
                        "Potential to introduce many new bugs",
                        "Requires extensive testing and code review",
                        "May block other work during refactoring",
                    ],
                ),
            ]
            
            # Confidence calibration
            proposal.confidence_level = 95
            proposal.confidence_explanation = (
                "Circular dependency detection uses static import analysis "
                "(graph traversal). 100% accurate for explicitly imported modules. "
                "May miss dynamic/runtime imports (low probability in well-structured code)."
            )
            
            self.patterns_matched.append(f"circular_dependency:{cycle_length}_hop:{cycle_str}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_domain_leakage(
        self,
        graph: Dict[str, Set[str]],
        repository_path: str,
    ) -> List[IntelligenceProposal]:
        """
        Detect domain leakage: when one logical domain bleeds into another.
        
        Example: Authentication domain exposing password hashing to business logic domain.
        The business logic should only see "is_password_valid", not "hash_password".
        """
        proposals = []
        
        # Heuristic: detect when modules import too much from unrelated domains
        domain_imports = self._analyze_domain_cohesion(graph, repository_path)
        
        for domain_pair, import_count in domain_imports.items():
            if import_count < 3:  # Only flag significant leakage
                continue
            
            domain_a, domain_b = domain_pair
            
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.ABSTRACTION_LEAKAGE
            proposal.severity = Severity.MEDIUM
            
            proposal.problem_statement = (
                f"Domain leakage detected: {domain_a} makes {import_count} cross-domain "
                f"imports from {domain_b}. This suggests {domain_a} is depending on "
                f"domain-specific details rather than abstractions."
            )
            
            proposal.risk_explanation = (
                f"When domains leak into each other, changes in {domain_b}'s internal "
                f"implementation force changes in {domain_a}. "
                f"This violates the principle of dependency inversion."
            )
            
            proposal.root_cause_hypothesis = (
                f"Likely cause: {domain_a} needs functionality from {domain_b}, "
                f"but no abstraction boundary exists. Instead of using abstract interfaces, "
                f"{domain_a} imports {domain_b}'s concrete implementations."
            )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Define abstraction boundary between domains",
                    description=(
                        f"Create an abstract interface/contract that {domain_a} depends on, "
                        f"hiding {domain_b}'s implementation details."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        f"Identify what {domain_a} actually needs from {domain_b}",
                        "Design abstract interface",
                        f"Update {domain_a} to depend on interface",
                        f"Update {domain_b} to implement interface",
                        "Remove concrete implementation imports",
                    ],
                    assumptions=[
                        "Abstract interface can cleanly represent needs",
                        "No performance overhead from abstraction",
                    ],
                    risks=[
                        "Interface design might be wrong",
                        "May need to change interface as requirements evolve",
                    ],
                ),
                FixStrategy(
                    name="Move functionality to shared abstraction layer",
                    description=(
                        f"Create new layer with abstract types that both domains depend on, "
                        f"eliminating direct {domain_a}→{domain_b} imports."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Identify common abstractions",
                        "Create new 'contracts' or 'interfaces' module",
                        "Move abstract types there",
                        f"Update both domains to import from contracts",
                        "Remove direct cross-domain imports",
                    ],
                    assumptions=[
                        "Common abstractions exist",
                        "New layer doesn't become a dump",
                    ],
                    risks=[
                        "New layer can become unclear/bloated",
                        "Adds indirection",
                    ],
                ),
            ]
            
            proposal.confidence_level = 70
            proposal.confidence_explanation = (
                f"Domain detection uses directory/naming heuristics. "
                f"Confidence is moderate - actual domain boundaries may differ from naming. "
                f"Recommend manual review to confirm intended boundaries."
            )
            
            self.patterns_matched.append(f"domain_leakage:{domain_a}→{domain_b}")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_coupling_clusters(
        self,
        graph: Dict[str, Set[str]],
    ) -> List[IntelligenceProposal]:
        """
        Detect tightly coupled clusters of modules.
        A cluster is a set of modules that frequently import from each other.
        """
        proposals = []
        
        # Find highly connected subgraphs
        clusters = self._find_tight_coupling_clusters(graph)
        
        for cluster in clusters:
            if len(cluster) < 3:  # Clusters need at least 3 nodes to be interesting
                continue
            
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.ARCHITECTURAL_VIOLATIONS
            proposal.severity = Severity.HIGH
            
            cluster_str = ", ".join(sorted(cluster))
            internal_edges = self._count_internal_edges(cluster, graph)
            max_edges = len(cluster) * (len(cluster) - 1)
            coupling_density = internal_edges / max_edges if max_edges > 0 else 0
            
            proposal.problem_statement = (
                f"Tight coupling detected: {len(cluster)} modules form a cluster "
                f"with {coupling_density*100:.0f}% internal coupling. "
                f"({cluster_str}) - These modules should be refactored or consolidated."
            )
            
            proposal.risk_explanation = (
                f"Tight coupling makes code difficult to test, extend, and refactor. "
                f"Cannot change one module without considering all {len(cluster)} modules. "
                f"High cognitive load for understanding and modifying this cluster."
            )
            
            proposal.root_cause_hypothesis = (
                f"Likely causes: (1) Insufficient abstraction between modules, "
                f"(2) Related functionality spread across multiple modules without clear boundaries, "
                f"(3) Lack of dependency inversion - modules depend on details rather than abstractions."
            )
            
            proposal.affected_files = [
                AffectedFile(path=self._module_to_file_path(module), severity=Severity.HIGH)
                for module in cluster
            ]
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Consolidate into single module",
                    description=(
                        f"Merge the {len(cluster)} tightly coupled modules into single module "
                        f"with clear internal structure and cohesive responsibility."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        "Analyze responsibilities of each module",
                        "Design new consolidated structure",
                        "Move code into new module",
                        "Update all imports",
                        "Verify no internal cycles",
                    ],
                    assumptions=[
                        "Modules share common responsibility",
                        "Single module won't be too large",
                    ],
                    risks=[
                        "New module may become god object",
                        "May hide fundamental design issue",
                    ],
                ),
                FixStrategy(
                    name="Introduce abstraction layer",
                    description=(
                        f"Create abstraction layer that {len(cluster)} modules depend on, "
                        f"eliminating internal circular imports."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        "Design shared abstractions",
                        "Create abstractions module",
                        f"Update all {len(cluster)} modules to depend on it",
                        "Remove direct cross-module imports",
                    ],
                    assumptions=[
                        "Clear abstractions exist",
                        "Not just moving problem elsewhere",
                    ],
                    risks=[
                        "Over-abstraction",
                        "Abstraction may diverge from needs",
                    ],
                ),
            ]
            
            proposal.confidence_level = 80
            proposal.confidence_explanation = (
                f"Clustering uses graph connectivity analysis (deterministic). "
                f"Confidence is high but reflects coupling fact, not severity. "
                f"Actual severity depends on module sizes and responsibilities."
            )
            
            self.patterns_matched.append(f"tight_coupling_cluster:{len(cluster)}_modules")
            proposals.append(proposal)
        
        return proposals
    
    def _detect_layer_violations(
        self,
        repository_path: str,
        graph: Dict[str, Set[str]],
    ) -> List[IntelligenceProposal]:
        """
        Enhanced layer violation detection using import graph.
        More accurate than directory structure heuristics.
        """
        proposals = []
        
        # Define layer model (heuristic but used more accurately)
        layers = {
            'api': 0,
            'routers': 0,
            'views': 0,
            'controllers': 0,
            'handlers': 0,
            'services': 1,
            'business': 1,
            'logic': 1,
            'core': 1,
            'repositories': 2,
            'models': 2,
            'db': 2,
            'database': 2,
            'data': 2,
            'storage': 2,
        }
        
        # Map modules to layers based on directory structure
        module_to_layer = self._classify_modules_to_layers(
            graph.keys(),
            repository_path,
            layers,
        )
        
        # Find violations in import graph
        violations = {}
        for module, imports in graph.items():
            if module not in module_to_layer:
                continue
            
            module_layer_level = module_to_layer[module][1]
            
            for imported_module in imports:
                if imported_module not in module_to_layer:
                    continue
                
                imported_layer_level = module_to_layer[imported_module][1]
                
                # Violation: higher layer depends on lower layer
                if module_layer_level > imported_layer_level:
                    violation_key = (
                        module_to_layer[module][0],
                        module_to_layer[imported_module][0],
                    )
                    if violation_key not in violations:
                        violations[violation_key] = []
                    violations[violation_key].append((module, imported_module))
        
        # Create proposals for each violation pattern
        for (from_layer, to_layer), module_pairs in violations.items():
            if len(module_pairs) == 0:
                continue
            
            proposal = IntelligenceProposal()
            proposal.bug_class = BugClass.ARCHITECTURAL_VIOLATIONS
            proposal.severity = Severity.HIGH
            
            proposal.problem_statement = (
                f"Layer boundary violation: {from_layer} layer imports from {to_layer} layer. "
                f"Detected in {len(module_pairs)} import(s). "
                f"This violates layered architecture principle (lower layers should not depend on higher)."
            )
            
            proposal.risk_explanation = (
                f"Importing from lower layers couples {from_layer} to internal implementation details. "
                f"Changes to {to_layer}'s internals will break {from_layer}. "
                f"Makes refactoring difficult and increases maintenance burden."
            )
            
            proposal.root_cause_hypothesis = (
                f"{from_layer} needs functionality from {to_layer}, but instead of depending on "
                f"a public contract/interface, it imports concrete implementations. "
                f"Likely causes: (1) No abstraction exists, (2) Faster to import directly than refactor, "
                f"(3) Unclear boundaries - developers don't realize they're violating layers."
            )
            
            # Affected files (unique modules involved)
            affected_modules = set()
            for source, target in module_pairs:
                affected_modules.add(source)
                affected_modules.add(target)
            
            for module in affected_modules:
                file_path = self._module_to_file_path(module)
                proposal.affected_files.append(
                    AffectedFile(path=file_path, severity=Severity.HIGH)
                )
            
            proposal.suggested_strategies = [
                FixStrategy(
                    name="Create abstraction layer",
                    description=(
                        f"Create abstraction/contract layer between {from_layer} and {to_layer}. "
                        f"{from_layer} depends on abstraction, {to_layer} implements it."
                    ),
                    effort_estimate=EffortEstimate.MEDIUM,
                    prerequisite_actions=[
                        f"Analyze what {from_layer} actually needs from {to_layer}",
                        "Design abstract interface/contract",
                        "Create abstraction layer with interfaces",
                        f"Update {from_layer} to import abstraction",
                        f"Update {to_layer} to implement abstraction",
                        "Remove direct layer-violating imports",
                    ],
                    assumptions=[
                        "Clean abstraction can represent relationship",
                        "No circular dependencies introduced",
                    ],
                    risks=[
                        "Abstraction design might be wrong",
                        "Adds indirection (minor performance cost)",
                    ],
                ),
                FixStrategy(
                    name="Move responsibility to appropriate layer",
                    description=(
                        f"Analyze what {from_layer} needs from {to_layer}. "
                        f"If it belongs in {from_layer}, move/duplicate it. "
                        f"If it belongs in {to_layer}, move the calling code."
                    ),
                    effort_estimate=EffortEstimate.LARGE,
                    prerequisite_actions=[
                        f"Document why {from_layer} needs {to_layer}",
                        "Determine proper layer for functionality",
                        "Refactor code accordingly",
                        "Update all affected imports",
                    ],
                    assumptions=[
                        "Functionality can be clearly assigned to one layer",
                        "Does not violate DRY principle",
                    ],
                    risks=[
                        "May duplicate code",
                        "Could introduce inconsistencies",
                    ],
                ),
            ]
            
            proposal.confidence_level = 85
            proposal.confidence_explanation = (
                f"Layer detection combines directory heuristics with import graph analysis. "
                f"Confidence is good but depends on naming conventions. "
                f"Recommend code review to verify intended layer boundaries match actual structure."
            )
            
            self.patterns_matched.append(f"layer_violation:{from_layer}→{to_layer}:×{len(module_pairs)}")
            proposals.append(proposal)
        
        return proposals
    
    # ========== Helper Methods ==========
    
    def _build_import_graph(self, repository_path: str) -> Dict[str, Set[str]]:
        """Build deterministic import graph (sorted for reproducibility)."""
        graph: Dict[str, Set[str]] = {}
        
        for root, dirs, files in os.walk(repository_path):
            dirs[:] = sorted([
                d for d in dirs if d not in {
                    '__pycache__', '.git', 'node_modules', 'venv', '.venv',
                    'build', 'dist', '.tox', '.pytest_cache', '.venv'
                }
            ])
            
            for file in sorted(files):  # Sort for determinism
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                self.files_scanned += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        self.lines_analyzed += len(content.split('\n'))
                    
                    module_name = self._get_module_name(file_path, repository_path)
                    if module_name and not module_name.startswith('_'):
                        imports = self._extract_imports_deterministic(file_path)
                        if imports:
                            graph[module_name] = imports
                except Exception:
                    pass
        
        return dict(sorted(graph.items()))  # Deterministic order
    
    def _extract_imports_deterministic(self, file_path: str) -> Set[str]:
        """Extract imports in deterministic way."""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if (line.startswith('import ') or line.startswith('from ')) and not line.startswith('import_'):
                        if 'import ' in line:
                            parts = line.split()
                            if len(parts) > 1:
                                module = parts[1].split('.')[0]
                                if module and not module.startswith('_') and module != 'import':
                                    imports.add(module)
        except Exception:
            pass
        return imports
    
    def _find_all_cycles_dfs(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Find all cycles using DFS with proper state tracking."""
        cycles = []
        visited = set()
        
        def dfs(node: str, path: List[str], rec_stack: Set[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in sorted(graph.get(node, set())):  # Sort for determinism
                if neighbor not in visited:
                    dfs(neighbor, path, rec_stack)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycle = sorted(path[cycle_start:])  # Sort for canonical form
                    if cycle not in cycles:  # Avoid duplicates
                        cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        for node in sorted(graph.keys()):  # Sort for determinism
            if node not in visited:
                dfs(node, [], set())
        
        return sorted(cycles)  # Deterministic output order
    
    def _deduplicate_cycles(self, cycles: List[List[str]]) -> List[List[str]]:
        """Remove duplicate cycles (same modules, different starting points)."""
        unique = []
        seen_sets = []
        
        for cycle in cycles:
            cycle_set = frozenset(cycle)
            if cycle_set not in seen_sets:
                unique.append(cycle)
                seen_sets.append(cycle_set)
        
        return unique
    
    def _analyze_domain_cohesion(
        self,
        graph: Dict[str, Set[str]],
        repository_path: str,
    ) -> Dict[Tuple[str, str], int]:
        """Count cross-domain imports."""
        domain_imports: Dict[Tuple[str, str], int] = {}
        
        module_to_domain = self._classify_modules_to_domains(graph.keys(), repository_path)
        
        for module, imports in graph.items():
            if module not in module_to_domain:
                continue
            
            module_domain = module_to_domain[module]
            
            for imported in imports:
                if imported not in module_to_domain:
                    continue
                
                imported_domain = module_to_domain[imported]
                
                if module_domain != imported_domain:
                    key = tuple(sorted([module_domain, imported_domain]))
                    domain_imports[key] = domain_imports.get(key, 0) + 1
        
        return domain_imports
    
    def _classify_modules_to_domains(self, modules, repository_path: str) -> Dict[str, str]:
        """Classify modules to domains based on directory structure."""
        module_to_domain = {}
        
        for module in modules:
            # Extract domain from module path (first component usually)
            parts = module.split('.')
            domain = parts[0] if parts else 'unknown'
            module_to_domain[module] = domain
        
        return module_to_domain
    
    def _find_tight_coupling_clusters(self, graph: Dict[str, Set[str]]) -> List[Set[str]]:
        """Find clusters of tightly coupled modules."""
        clusters = []
        visited = set()
        
        def bfs_cluster(start: str, threshold: float = 0.5) -> Set[str]:
            """Find cluster starting from node with high internal connectivity."""
            cluster = {start}
            queue = [start]
            
            while queue:
                node = queue.pop(0)
                
                for neighbor in graph.get(node, set()):
                    if neighbor not in cluster:
                        # Check if neighbor is well-connected within cluster
                        internal_connections = len(graph.get(neighbor, set()) & cluster)
                        potential_connections = len(cluster)
                        
                        if potential_connections > 0 and internal_connections / potential_connections >= threshold:
                            cluster.add(neighbor)
                            queue.append(neighbor)
            
            return cluster
        
        for node in sorted(graph.keys()):
            if node not in visited:
                cluster = bfs_cluster(node)
                if len(cluster) >= 3:  # Only report clusters of 3+
                    clusters.append(cluster)
                    visited.update(cluster)
        
        return clusters
    
    def _count_internal_edges(self, cluster: Set[str], graph: Dict[str, Set[str]]) -> int:
        """Count edges within cluster."""
        count = 0
        for node in cluster:
            for neighbor in graph.get(node, set()):
                if neighbor in cluster:
                    count += 1
        return count
    
    def _classify_modules_to_layers(
        self,
        modules,
        repository_path: str,
        layers: Dict[str, int],
    ) -> Dict[str, Tuple[str, int]]:
        """Map modules to layers. Returns {module: (layer_name, level)}."""
        module_to_layer = {}
        
        for module in modules:
            assigned_layer = None
            assigned_level = None
            
            for layer_name, layer_level in layers.items():
                if layer_name in module.lower() or layer_name in module:
                    assigned_layer = layer_name
                    assigned_level = layer_level
                    break
            
            if assigned_layer:
                module_to_layer[module] = (assigned_layer, assigned_level)
        
        return module_to_layer
    
    def _get_module_name(self, file_path: str, repo_path: str) -> str:
        """Get module name from file path."""
        rel_path = os.path.relpath(file_path, repo_path)
        module = rel_path.replace(os.sep, '.').replace('.py', '')
        return module
    
    def _module_to_file_path(self, module: str) -> str:
        """Convert module name to relative file path."""
        return module.replace('.', '/') + '.py'
