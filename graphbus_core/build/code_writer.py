"""
Code writer - applies agent-agreed changes to source files
"""

import logging
import os
from typing import List
from graphbus_core.model.message import CommitRecord
from graphbus_core.build.contract_validator import ContractValidator
from graphbus_core.build.refactoring import RefactoringValidator

logger = logging.getLogger(__name__)


class CodeWriter:
    """
    Applies code changes from commit records to actual source files.

    For Hello World version:
    - Simple string replacement
    - Backs up original files
    """

    def __init__(self, dry_run: bool = False, enforce_contracts: bool = True, enforce_refactoring: bool = True):
        """
        Initialize code writer.

        Args:
            dry_run: If True, don't actually write files (for testing)
            enforce_contracts: If True, validate API contracts before applying changes
            enforce_refactoring: If True, validate refactoring improvements
        """
        self.dry_run = dry_run
        self.enforce_contracts = enforce_contracts
        self.enforce_refactoring = enforce_refactoring
        self.modified_files: List[str] = []
        self.contract_validator = ContractValidator()
        self.refactoring_validator = RefactoringValidator()

    def apply_commits(self, commits: List[CommitRecord]) -> List[str]:
        """
        Apply all commits to source files.

        Args:
            commits: List of CommitRecords to apply

        Returns:
            List of modified file paths
        """
        if not commits:
            logger.info("No commits to apply")
            return []

        logger.info("Applying %d commits...", len(commits))

        for commit in commits:
            self._apply_commit(commit)

        logger.info("Modified %d files", len(self.modified_files))
        return self.modified_files

    def _apply_commit(self, commit: CommitRecord) -> None:
        """
        Apply a single commit.

        Args:
            commit: CommitRecord to apply
        """
        file_path = commit.resolution.get("file_path")
        if not file_path:
            logger.warning("Commit %s has no file_path, skipping", commit.commit_id)
            return

        if not os.path.exists(file_path):
            logger.warning("File not found: %s, skipping", file_path)
            return

        # Read current file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error("Error reading %s: %s", file_path, e)
            return

        # Apply the change
        old_code = commit.resolution.get("old_code", "")
        new_code = commit.resolution.get("new_code", "")

        # Get agent name from commit
        agent_name = commit.proposal_id.split('_')[0] if commit.proposal_id else "unknown"

        # Validate contract compatibility (if old and new code provided)
        if self.enforce_contracts and old_code and new_code:
            # Check if changes would break contracts
            # We validate that the new code maintains backward compatibility
            try:
                import ast
                old_tree = ast.parse(content)

                # Compute what the new content would be
                test_new_content = content.replace(old_code, new_code, 1)
                new_tree = ast.parse(test_new_content)

                # Extract method signatures from both versions
                old_methods = self._extract_method_names(old_tree)
                new_methods = self._extract_method_names(new_tree)

                # Check for removed public methods
                removed_methods = old_methods - new_methods
                removed_public = [m for m in removed_methods if not m.startswith('_')]

                if removed_public:
                    logger.warning("REJECTED commit %s: contract violation — public methods removed: %s", commit.commit_id, removed_public)
                    return

            except SyntaxError:
                # If we can't parse, skip contract validation
                pass

        # Validate refactoring quality
        if self.enforce_refactoring and old_code and new_code:
            refactoring_result = self.refactoring_validator.validate_refactoring_proposal(
                old_code, new_code, agent_name
            )

            if not refactoring_result['valid']:
                logger.warning("REJECTED commit %s: refactoring validation failed — %s", commit.commit_id, refactoring_result.get('regressions', []))
                return

            if refactoring_result.get('regressions'):
                logger.warning("REJECTED commit %s: code quality would degrade — regressions: %s", commit.commit_id, refactoring_result['regressions'])
                return

            if refactoring_result.get('improvements'):
                logger.info("Commit %s refactoring improvements: %s", commit.commit_id, refactoring_result['improvements'])

        if not old_code:
            logger.warning("Commit %s has no old_code, skipping", commit.commit_id)
            return

        # Check if old code exists in file
        if old_code not in content:
            logger.warning("Old code not found in %s (commit %s) — looking for: %.100s...", file_path, commit.commit_id, old_code)
            return

        # Replace old with new
        new_content = content.replace(old_code, new_code)

        if new_content == content:
            logger.warning("No changes made to %s after replacement (commit %s)", file_path, commit.commit_id)
            return

        # Write back (unless dry run)
        if self.dry_run:
            logger.info("[DRY RUN] Would modify %s (target: %s)", file_path, commit.resolution.get('target'))
            logger.debug("  old: %.50s...", old_code)
            logger.debug("  new: %.50s...", new_code)
        else:
            # Backup original
            backup_path = f"{file_path}.backup"
            try:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logger.warning("Could not create backup for %s: %s", file_path, e)

            # Write new content
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info("Modified %s (backup: %s)", file_path, backup_path)

                if file_path not in self.modified_files:
                    self.modified_files.append(file_path)

            except Exception as e:
                logger.error("Error writing %s: %s", file_path, e)
                # Restore from backup
                if os.path.exists(backup_path):
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        original = f.read()
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(original)
                    logger.info("Restored %s from backup", file_path)

    def _extract_method_names(self, tree) -> set:
        """Extract all method names from an AST tree."""
        import ast
        methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                methods.add(node.name)
        return methods
