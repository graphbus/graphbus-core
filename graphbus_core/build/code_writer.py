"""
Code writer - applies agent-agreed changes to source files
"""

import os
from typing import List
from graphbus_core.model.message import CommitRecord
from graphbus_core.build.contract_validator import ContractValidator
from graphbus_core.build.refactoring import RefactoringValidator


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
            print("[CodeWriter] No commits to apply")
            return []

        print(f"\n[CodeWriter] Applying {len(commits)} commits...")

        for commit in commits:
            self._apply_commit(commit)

        print(f"[CodeWriter] Modified {len(self.modified_files)} files")
        return self.modified_files

    def _apply_commit(self, commit: CommitRecord) -> None:
        """
        Apply a single commit.

        Args:
            commit: CommitRecord to apply
        """
        file_path = commit.resolution.get("file_path")
        if not file_path:
            print(f"  Warning: Commit {commit.commit_id} has no file_path, skipping")
            return

        if not os.path.exists(file_path):
            print(f"  Warning: File not found: {file_path}, skipping")
            return

        # Read current file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
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
                    print(f"  ✗ REJECTED: Contract violation - public methods removed: {removed_public}")
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
                print(f"  ✗ REJECTED: Refactoring validation failed")
                print(f"    Reason: {refactoring_result.get('regressions', [])}")
                return

            if refactoring_result.get('regressions'):
                print(f"  ⚠️  Refactoring regressions detected:")
                for regression in refactoring_result['regressions']:
                    print(f"    - {regression}")
                print(f"  ✗ REJECTED: Code quality would degrade")
                return

            if refactoring_result.get('improvements'):
                print(f"  ✓ Refactoring improvements:")
                for improvement in refactoring_result['improvements']:
                    print(f"    + {improvement}")

        if not old_code:
            print(f"  Warning: Commit {commit.commit_id} has no old_code, skipping")
            return

        # Check if old code exists in file
        if old_code not in content:
            print(f"  Warning: Old code not found in {file_path}")
            print(f"  Looking for: {old_code[:100]}...")
            return

        # Replace old with new
        new_content = content.replace(old_code, new_code)

        if new_content == content:
            print(f"  Warning: No changes made to {file_path}")
            return

        # Write back (unless dry run)
        if self.dry_run:
            print(f"  [DRY RUN] Would modify {file_path}")
            print(f"    - Target: {commit.resolution.get('target')}")
            print(f"    - Old: {old_code[:50]}...")
            print(f"    - New: {new_code[:50]}...")
        else:
            # Backup original
            backup_path = f"{file_path}.backup"
            try:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"  Warning: Could not create backup: {e}")

            # Write new content
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  ✓ Modified {file_path}")
                print(f"    Backup saved to {backup_path}")

                if file_path not in self.modified_files:
                    self.modified_files.append(file_path)

            except Exception as e:
                print(f"  Error writing {file_path}: {e}")
                # Restore from backup
                if os.path.exists(backup_path):
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        original = f.read()
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(original)
                    print(f"  Restored from backup")

    def _extract_method_names(self, tree) -> set:
        """Extract all method names from an AST tree."""
        import ast
        methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                methods.add(node.name)
        return methods
