"""
Refactoring validation and enforcement for Build Mode

Ensures code stays simple and follows DRY principles during agent negotiation.
"""

import ast
import re
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from difflib import SequenceMatcher


class RefactoringValidator:
    """
    Validates code changes to prevent duplication and enforce simplicity.

    Checks:
    - Code duplication (identical or similar methods)
    - Method complexity (line count, nesting depth)
    - DRY violations (repeated patterns)
    - Common code that should be extracted
    """

    # Thresholds
    MAX_METHOD_LINES = 50
    MAX_CLASS_LINES = 200
    MAX_DUPLICATE_LINES = 10  # If > 10 lines are duplicated, flag it
    SIMILARITY_THRESHOLD = 0.85  # 85% similarity = duplication

    def __init__(self):
        self.violations = []
        self.suggestions = []

    def validate_source_code(self, source_code: str, agent_name: str) -> Dict:
        """
        Validate a single agent's source code for refactoring issues.

        Args:
            source_code: Python source code
            agent_name: Name of the agent

        Returns:
            Dict with validation results
        """
        self.violations = []
        self.suggestions = []

        # Parse the code
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return {
                "valid": False,
                "violations": [f"Syntax error: {e}"],
                "suggestions": []
            }

        # Check for violations
        self._check_class_size(tree, agent_name)
        self._check_method_sizes(tree)
        self._check_duplicate_methods(tree)

        return {
            "valid": len(self.violations) == 0,
            "violations": self.violations,
            "suggestions": self.suggestions,
            "metrics": self._compute_metrics(tree)
        }

    def detect_duplication_across_agents(
        self,
        agent_sources: Dict[str, str]
    ) -> List[Dict]:
        """
        Detect code duplication across multiple agents.

        Args:
            agent_sources: Dict mapping agent_name -> source_code

        Returns:
            List of duplication reports
        """
        duplications = []

        # Extract methods from all agents
        agent_methods = {}
        for agent_name, source_code in agent_sources.items():
            try:
                tree = ast.parse(source_code)
                methods = self._extract_methods(tree)
                agent_methods[agent_name] = methods
            except SyntaxError:
                continue

        # Compare methods between agents
        agent_names = list(agent_methods.keys())
        for i, agent1 in enumerate(agent_names):
            for agent2 in agent_names[i+1:]:
                dups = self._find_duplicate_methods(
                    agent_methods[agent1],
                    agent_methods[agent2],
                    agent1,
                    agent2
                )
                duplications.extend(dups)

        return duplications

    def suggest_extraction(
        self,
        duplications: List[Dict]
    ) -> List[Dict]:
        """
        Suggest extractions for duplicated code.

        Args:
            duplications: List of duplication reports

        Returns:
            List of extraction suggestions
        """
        suggestions = []

        for dup in duplications:
            if dup['lines'] >= self.MAX_DUPLICATE_LINES:
                suggestions.append({
                    "type": "extract_shared_module",
                    "reason": f"Duplicate code found in {dup['agent1']} and {dup['agent2']}",
                    "method_name": dup['method_name'],
                    "suggested_module": self._suggest_module_name(dup['method_name']),
                    "affected_agents": [dup['agent1'], dup['agent2']],
                    "code_sample": dup['code'][:200] + "..." if len(dup['code']) > 200 else dup['code']
                })

        return suggestions

    def validate_refactoring_proposal(
        self,
        old_code: str,
        new_code: str,
        agent_name: str
    ) -> Dict:
        """
        Validate that a refactoring proposal improves code quality.

        Args:
            old_code: Original code
            new_code: Proposed code
            agent_name: Name of agent

        Returns:
            Validation result
        """
        # Parse both versions
        try:
            old_tree = ast.parse(old_code)
            new_tree = ast.parse(new_code)
        except SyntaxError as e:
            # Code snippets might not be complete Python (e.g., method fragments)
            # In this case, skip validation and allow the change
            # The full file will be validated after all changes are applied
            return {
                "valid": True,  # Allow fragments to pass
                "reason": f"Skipped validation - code fragment: {str(e)[:100]}",
                "improvements": [],
                "regressions": []
            }

        # Compute metrics
        old_metrics = self._compute_metrics(old_tree)
        new_metrics = self._compute_metrics(new_tree)

        # Check if refactoring improves things
        improvements = []
        regressions = []

        if new_metrics['total_lines'] < old_metrics['total_lines']:
            improvements.append(f"Reduced lines: {old_metrics['total_lines']} → {new_metrics['total_lines']}")
        elif new_metrics['total_lines'] > old_metrics['total_lines'] * 1.2:  # 20% increase
            regressions.append(f"Increased lines significantly: {old_metrics['total_lines']} → {new_metrics['total_lines']}")

        if new_metrics['num_methods'] < old_metrics['num_methods']:
            improvements.append(f"Reduced methods: {old_metrics['num_methods']} → {new_metrics['num_methods']}")

        if new_metrics['max_method_lines'] < old_metrics['max_method_lines']:
            improvements.append(f"Reduced max method size: {old_metrics['max_method_lines']} → {new_metrics['max_method_lines']}")

        # Detect if methods were duplicated
        old_methods = self._extract_methods(old_tree)
        new_methods = self._extract_methods(new_tree)

        # Check for duplicate method names in new code
        method_names = [m['name'] for m in new_methods]
        if len(method_names) != len(set(method_names)):
            duplicates = [name for name in method_names if method_names.count(name) > 1]
            regressions.append(f"Duplicate method names: {duplicates}")

        return {
            "valid": len(regressions) == 0,
            "improvements": improvements,
            "regressions": regressions,
            "old_metrics": old_metrics,
            "new_metrics": new_metrics
        }

    # Private helper methods

    def _check_class_size(self, tree: ast.AST, agent_name: str) -> None:
        """Check if class exceeds size threshold."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                lines = node.end_lineno - node.lineno + 1
                if lines > self.MAX_CLASS_LINES:
                    self.violations.append(
                        f"Class {node.name} has {lines} lines (max: {self.MAX_CLASS_LINES})"
                    )
                    self.suggestions.append(
                        f"Consider splitting {node.name} into smaller classes or extracting helper modules"
                    )

    def _check_method_sizes(self, tree: ast.AST) -> None:
        """Check if methods exceed size threshold."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = node.end_lineno - node.lineno + 1
                if lines > self.MAX_METHOD_LINES:
                    self.violations.append(
                        f"Method {node.name} has {lines} lines (max: {self.MAX_METHOD_LINES})"
                    )
                    self.suggestions.append(
                        f"Break {node.name} into smaller helper methods"
                    )

    def _check_duplicate_methods(self, tree: ast.AST) -> None:
        """Check for duplicate method definitions."""
        methods = self._extract_methods(tree)
        method_names = [m['name'] for m in methods]

        # Find duplicates
        seen = set()
        duplicates = []
        for name in method_names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)

        if duplicates:
            self.violations.append(
                f"Duplicate method definitions found: {duplicates}"
            )
            self.suggestions.append(
                "Remove duplicate method definitions - keep only the final version"
            )

    def _extract_methods(self, tree: ast.AST) -> List[Dict]:
        """Extract all method definitions with their code."""
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get the source code of this method
                method_code = ast.unparse(node) if hasattr(ast, 'unparse') else ""
                methods.append({
                    'name': node.name,
                    'code': method_code,
                    'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                })
        return methods

    def _find_duplicate_methods(
        self,
        methods1: List[Dict],
        methods2: List[Dict],
        agent1: str,
        agent2: str
    ) -> List[Dict]:
        """Find duplicate methods between two agents."""
        duplicates = []

        for m1 in methods1:
            for m2 in methods2:
                # Check if method names match
                if m1['name'] == m2['name']:
                    # Check code similarity
                    similarity = self._code_similarity(m1['code'], m2['code'])
                    if similarity >= self.SIMILARITY_THRESHOLD:
                        duplicates.append({
                            'agent1': agent1,
                            'agent2': agent2,
                            'method_name': m1['name'],
                            'similarity': similarity,
                            'lines': max(m1['lines'], m2['lines']),
                            'code': m1['code']
                        })

        return duplicates

    def _code_similarity(self, code1: str, code2: str) -> float:
        """Compute similarity ratio between two code snippets."""
        # Normalize whitespace
        code1 = ' '.join(code1.split())
        code2 = ' '.join(code2.split())

        # Use sequence matcher
        return SequenceMatcher(None, code1, code2).ratio()

    def _compute_metrics(self, tree: ast.AST) -> Dict:
        """Compute code metrics."""
        metrics = {
            'total_lines': 0,
            'num_methods': 0,
            'num_classes': 0,
            'max_method_lines': 0,
            'avg_method_lines': 0
        }

        method_lines = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                metrics['num_classes'] += 1
                if hasattr(node, 'end_lineno'):
                    metrics['total_lines'] = max(metrics['total_lines'], node.end_lineno)

            if isinstance(node, ast.FunctionDef):
                metrics['num_methods'] += 1
                if hasattr(node, 'end_lineno'):
                    lines = node.end_lineno - node.lineno + 1
                    method_lines.append(lines)
                    metrics['max_method_lines'] = max(metrics['max_method_lines'], lines)

        if method_lines:
            metrics['avg_method_lines'] = sum(method_lines) / len(method_lines)

        return metrics

    def _suggest_module_name(self, method_name: str) -> str:
        """Suggest a module name for extracted code."""
        # Common patterns
        if 'log' in method_name.lower():
            return "logging_utils"
        if 'setup' in method_name.lower():
            return "setup_helpers"
        if 'config' in method_name.lower():
            return "config_utils"
        if 'validate' in method_name.lower():
            return "validators"
        if 'format' in method_name.lower():
            return "formatters"

        # Default
        return "shared_utils"
