"""
Code writer - applies agent-agreed changes to source files
"""

import os
from typing import List
from graphbus_core.model.message import CommitRecord


class CodeWriter:
    """
    Applies code changes from commit records to actual source files.

    For Hello World version:
    - Simple string replacement
    - Backs up original files
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize code writer.

        Args:
            dry_run: If True, don't actually write files (for testing)
        """
        self.dry_run = dry_run
        self.modified_files: List[str] = []

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
