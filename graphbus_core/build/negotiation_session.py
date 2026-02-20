"""
Negotiation session management with git integration

Manages:
- Temporary draft storage in .graphbus/negotiations/
- Feature branch creation per negotiation
- Pull request tracking and context retrieval
- Developer feedback integration
"""

import os
import json
import uuid
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime
from dataclasses import dataclass, asdict

if TYPE_CHECKING:
    from graphbus_core.agents.negotiation_client import NegotiationClient


@dataclass
class NegotiationSession:
    """Represents a single negotiation session"""
    session_id: str
    intent: str
    timestamp: str
    branch_name: str
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    status: str = "in_progress"  # in_progress, pr_created, merged, abandoned
    modified_files: List[str] = None
    commit_count: int = 0
    developer_feedback: List[Dict[str, str]] = None

    def __post_init__(self):
        if self.modified_files is None:
            self.modified_files = []
        if self.developer_feedback is None:
            self.developer_feedback = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'NegotiationSession':
        """Create from dictionary"""
        return cls(**data)


class NegotiationSessionManager:
    """
    Manages negotiation sessions with git workflow integration.

    Directory structure:
    .graphbus/
    ├── negotiations.json         # Index of all sessions
    └── negotiations/
        └── <session-id>/
            ├── drafts/           # Temporary file drafts before commit
            ├── commits.json      # Commit history for this session
            ├── proposals.json    # All proposals made
            └── context.json      # Session context and metadata
    """

    def __init__(
        self,
        project_root: str = ".",
        remote_client: Optional["NegotiationClient"] = None,
    ):
        """
        Initialize session manager.

        Args:
            project_root: Root directory of the project (where .graphbus/ will be created)
            remote_client: Optional NegotiationClient for dual-write to a remote web service
        """
        self.remote_client = remote_client
        self.project_root = Path(project_root).resolve()
        self.graphbus_dir = self.project_root / ".graphbus"
        self.negotiations_dir = self.graphbus_dir / "negotiations"
        self.index_file = self.graphbus_dir / "negotiations.json"

        # Ensure directories exist
        self._init_directories()

        # Load session index
        self.sessions: Dict[str, NegotiationSession] = self._load_index()

    def _init_directories(self) -> None:
        """Create .graphbus directory structure"""
        self.graphbus_dir.mkdir(exist_ok=True)
        self.negotiations_dir.mkdir(exist_ok=True)

        # Create .gitignore for .graphbus
        gitignore_path = self.graphbus_dir / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, 'w') as f:
                f.write("# GraphBus internal files\n")
                f.write("negotiations/*/drafts/\n")
                f.write("*.backup\n")

        # Initialize index file if doesn't exist
        if not self.index_file.exists():
            with open(self.index_file, 'w') as f:
                json.dump({"sessions": [], "active_session": None}, f, indent=2)

    def _load_index(self) -> Dict[str, NegotiationSession]:
        """Load session index from negotiations.json"""
        if not self.index_file.exists():
            return {}

        try:
            with open(self.index_file, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            # Corrupt or empty file - return empty dict
            return {}

        # Handle both old format (list) and new format (dict with "sessions" key)
        sessions = {}

        if isinstance(data, list):
            # Old format - migrate to new format
            session_list = data
        elif isinstance(data, dict):
            # New format
            session_list = data.get("sessions", [])
        else:
            # Unknown format - return empty
            return {}

        # Load sessions
        for session_data in session_list:
            try:
                session = NegotiationSession.from_dict(session_data)
                sessions[session.session_id] = session
            except (KeyError, TypeError):
                # Skip malformed session data
                continue

        return sessions

    def _save_index(self) -> None:
        """Save session index to negotiations.json"""
        data = {
            "sessions": [session.to_dict() for session in self.sessions.values()],
            "active_session": None  # Will be set when creating new session
        }

        with open(self.index_file, 'w') as f:
            json.dump(data, f, indent=2)

    def create_session(self, intent: str) -> NegotiationSession:
        """
        Create a new negotiation session.

        Args:
            intent: User's intent/goal for this negotiation

        Returns:
            NegotiationSession object
        """
        # Generate unique session ID
        session_id = f"negotiate_{uuid.uuid4().hex[:8]}"

        # Generate branch name from intent
        branch_slug = intent.lower().replace(" ", "-")[:50]
        branch_name = f"graphbus/negotiate-{branch_slug}-{uuid.uuid4().hex[:6]}"

        # Create session object
        session = NegotiationSession(
            session_id=session_id,
            intent=intent,
            timestamp=datetime.now().isoformat(),
            branch_name=branch_name
        )

        # Create session directory structure
        session_dir = self.negotiations_dir / session_id
        session_dir.mkdir(exist_ok=True)
        (session_dir / "drafts").mkdir(exist_ok=True)

        # Initialize session files
        self._write_session_file(session_id, "context.json", {
            "intent": intent,
            "timestamp": session.timestamp,
            "branch_name": branch_name,
            "status": "in_progress"
        })

        self._write_session_file(session_id, "proposals.json", {"proposals": []})
        self._write_session_file(session_id, "commits.json", {"commits": []})

        # Add to index
        self.sessions[session_id] = session
        self._save_index()

        print(f"\n[SessionManager] Created negotiation session: {session_id}")
        print(f"  Intent: {intent}")
        print(f"  Branch: {branch_name}")
        print(f"  Directory: {session_dir}")

        # Dual-write to remote if configured
        if self.remote_client is not None:
            try:
                self.remote_client.create_session(intent)
            except Exception as exc:
                print(f"  [SessionManager] Warning: remote create_session failed: {exc}")

        return session

    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_active_sessions(self) -> List[NegotiationSession]:
        """Get all sessions in progress"""
        return [s for s in self.sessions.values() if s.status == "in_progress"]

    def save_draft(self, session_id: str, file_path: str, content: str) -> None:
        """
        Save a temporary draft of a file before committing.

        Args:
            session_id: Session ID
            file_path: Original file path (relative to project root)
            content: File content
        """
        session_dir = self.negotiations_dir / session_id / "drafts"

        # Create subdirectories if needed
        draft_path = session_dir / file_path
        draft_path.parent.mkdir(parents=True, exist_ok=True)

        # Write draft
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"  [SessionManager] Saved draft: {file_path}")

    def get_draft(self, session_id: str, file_path: str) -> Optional[str]:
        """Get draft content for a file"""
        draft_path = self.negotiations_dir / session_id / "drafts" / file_path

        if not draft_path.exists():
            return None

        with open(draft_path, 'r', encoding='utf-8') as f:
            return f.read()

    def record_proposal(self, session_id: str, proposal: Dict) -> None:
        """Record a proposal made during negotiation"""
        proposals_file = self.negotiations_dir / session_id / "proposals.json"

        with open(proposals_file, 'r') as f:
            data = json.load(f)

        data["proposals"].append(proposal)

        with open(proposals_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Dual-write to remote
        if self.remote_client is not None:
            try:
                self.remote_client.record_proposal(session_id, proposal)
            except Exception as exc:
                print(f"  [SessionManager] Warning: remote record_proposal failed: {exc}")

    def record_commit(self, session_id: str, commit_record: Dict) -> None:
        """Record a commit made during negotiation"""
        commits_file = self.negotiations_dir / session_id / "commits.json"

        with open(commits_file, 'r') as f:
            data = json.load(f)

        data["commits"].append(commit_record)

        with open(commits_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Update session
        if session_id in self.sessions:
            self.sessions[session_id].commit_count += 1
            self._save_index()

        # Dual-write to remote
        if self.remote_client is not None:
            try:
                self.remote_client.record_commit(session_id, commit_record)
            except Exception as exc:
                print(f"  [SessionManager] Warning: remote record_commit failed: {exc}")

    def update_session(self, session_id: str, **kwargs) -> None:
        """Update session fields"""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

        self._save_index()

        # Dual-write to remote
        if self.remote_client is not None:
            try:
                self.remote_client.update_session(session_id, **kwargs)
            except Exception as exc:
                print(f"  [SessionManager] Warning: remote update_session failed: {exc}")

    def _write_session_file(self, session_id: str, filename: str, data: Any) -> None:
        """Write JSON file to session directory"""
        file_path = self.negotiations_dir / session_id / filename
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _read_session_file(self, session_id: str, filename: str) -> Any:
        """Read JSON file from session directory"""
        file_path = self.negotiations_dir / session_id / filename
        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            return json.load(f)

    def get_session_context(self, session_id: str) -> Dict:
        """Get full context for a session (for PR description, etc.)"""
        # If remote client is configured, fetch from remote and merge
        if self.remote_client is not None:
            try:
                remote_session = self.remote_client.get_session(session_id)
                remote_proposals = self.remote_client.get_proposals(session_id)
                remote_commits = self.remote_client.get_commits(session_id)
                if remote_session is not None:
                    return {
                        **remote_session,
                        "proposals": remote_proposals,
                        "commits": remote_commits,
                    }
            except Exception as exc:
                print(f"  [SessionManager] Warning: remote get_session_context failed, falling back to local: {exc}")

        # Local fallback
        context = self._read_session_file(session_id, "context.json") or {}
        proposals = self._read_session_file(session_id, "proposals.json") or {"proposals": []}
        commits = self._read_session_file(session_id, "commits.json") or {"commits": []}

        return {
            **context,
            "proposals": proposals["proposals"],
            "commits": commits["commits"]
        }

    @classmethod
    def from_env(cls, project_root: str = ".") -> "NegotiationSessionManager":
        """
        Create a NegotiationSessionManager, optionally with a remote client
        if GRAPHBUS_NEGOTIATIONS_URL and GRAPHBUS_API_KEY env vars are set.
        """
        remote_client = None
        negotiations_url = os.environ.get("GRAPHBUS_NEGOTIATIONS_URL", "").strip()
        api_key = os.environ.get("GRAPHBUS_API_KEY", "").strip()

        if negotiations_url and api_key:
            from graphbus_core.agents.negotiation_client import NegotiationClient
            remote_client = NegotiationClient(base_url=negotiations_url, api_key=api_key)
            print(f"[SessionManager] Remote backend enabled: {negotiations_url}")

        return cls(project_root=project_root, remote_client=remote_client)

    def get_latest_session_with_pr(self, intent_keywords: List[str] = None) -> Optional[NegotiationSession]:
        """
        Get the most recent session that has a PR, optionally filtered by intent keywords.

        Args:
            intent_keywords: Optional list of keywords to match in intent

        Returns:
            NegotiationSession or None
        """
        pr_sessions = [s for s in self.sessions.values() if s.pr_number is not None]

        # Filter by intent keywords if provided
        if intent_keywords:
            filtered = []
            for session in pr_sessions:
                intent_lower = session.intent.lower()
                if any(keyword.lower() in intent_lower for keyword in intent_keywords):
                    filtered.append(session)
            pr_sessions = filtered

        if not pr_sessions:
            return None

        # Sort by timestamp (most recent first)
        pr_sessions.sort(key=lambda s: s.timestamp, reverse=True)
        return pr_sessions[0]

    def get_pr_feedback_context(self, session_id: str, git_workflow: 'GitWorkflowManager') -> Dict:
        """
        Retrieve feedback from a PR to use as context in subsequent negotiations.

        Args:
            session_id: Session ID
            git_workflow: GitWorkflowManager instance

        Returns:
            Dict with PR feedback context
        """
        session = self.sessions.get(session_id)
        if not session or not session.pr_number:
            return {}

        # Get PR comments
        comments = git_workflow.get_pr_comments(session.pr_number)
        review_comments = git_workflow.get_pr_review_comments(session.pr_number)

        # Format feedback for agents
        feedback_summary = {
            "session_id": session_id,
            "intent": session.intent,
            "pr_number": session.pr_number,
            "pr_url": session.pr_url,
            "comments": [],
            "review_comments": []
        }

        # Extract relevant comments
        for comment in comments:
            feedback_summary["comments"].append({
                "author": comment.get("author", {}).get("login", "Unknown"),
                "body": comment.get("body", ""),
                "created_at": comment.get("createdAt", "")
            })

        for review in review_comments:
            feedback_summary["review_comments"].append({
                "author": review.get("author", {}).get("login", "Unknown"),
                "state": review.get("state", ""),
                "body": review.get("body", ""),
                "created_at": review.get("submittedAt", "")
            })

        return feedback_summary


class GitWorkflowManager:
    """
    Manages git operations for negotiation workflow.

    Features:
    - Create feature branches per negotiation
    - Commit changes to branch
    - Create pull requests
    - Retrieve PR context and comments
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()

    def _run_git(self, *args) -> subprocess.CompletedProcess:
        """Run git command"""
        return subprocess.run(
            ["git"] + list(args),
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

    def get_current_branch(self) -> str:
        """Get current git branch"""
        result = self._run_git("branch", "--show-current")
        return result.stdout.strip()

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """
        Create a new feature branch for negotiation.

        Args:
            branch_name: Name of new branch
            from_branch: Base branch to branch from

        Returns:
            True if successful
        """
        print(f"\n[GitWorkflow] Creating branch: {branch_name}")

        # Ensure we're on base branch
        result = self._run_git("checkout", from_branch)
        if result.returncode != 0:
            print(f"  ✗ Failed to checkout {from_branch}: {result.stderr}")
            return False

        # Pull latest
        result = self._run_git("pull", "origin", from_branch)
        if result.returncode != 0:
            print(f"  ⚠️  Warning: Could not pull latest {from_branch}")

        # Create new branch
        result = self._run_git("checkout", "-b", branch_name)
        if result.returncode != 0:
            print(f"  ✗ Failed to create branch: {result.stderr}")
            return False

        print(f"  ✓ Created and switched to branch: {branch_name}")
        return True

    def commit_changes(self, files: List[str], message: str) -> bool:
        """
        Commit changes to current branch.

        Args:
            files: List of file paths to commit
            message: Commit message

        Returns:
            True if successful
        """
        print(f"\n[GitWorkflow] Committing changes...")

        # Stage files
        for file_path in files:
            result = self._run_git("add", file_path)
            if result.returncode != 0:
                print(f"  ✗ Failed to stage {file_path}: {result.stderr}")
                return False
            print(f"  + Staged: {file_path}")

        # Commit
        result = self._run_git("commit", "-m", message)
        if result.returncode != 0:
            print(f"  ✗ Failed to commit: {result.stderr}")
            return False

        print(f"  ✓ Committed changes")
        return True

    def push_branch(self, branch_name: str) -> bool:
        """
        Push branch to origin.

        Args:
            branch_name: Branch to push

        Returns:
            True if successful
        """
        print(f"\n[GitWorkflow] Pushing branch: {branch_name}")

        result = self._run_git("push", "-u", "origin", branch_name)
        if result.returncode != 0:
            print(f"  ✗ Failed to push: {result.stderr}")
            return False

        print(f"  ✓ Pushed branch to origin")
        return True

    def create_pr(self, branch_name: str, title: str, body: str, base: str = "main") -> Optional[Dict]:
        """
        Create a pull request using GitHub CLI.

        Args:
            branch_name: Feature branch
            title: PR title
            body: PR description
            base: Base branch (usually 'main')

        Returns:
            PR info dict with 'number' and 'url', or None if failed
        """
        print(f"\n[GitWorkflow] Creating pull request...")

        # Check if gh CLI is available
        result = subprocess.run(["which", "gh"], capture_output=True)
        if result.returncode != 0:
            print("  ✗ GitHub CLI (gh) not installed. Install with: brew install gh")
            return None

        # Create PR
        result = subprocess.run(
            ["gh", "pr", "create",
             "--base", base,
             "--head", branch_name,
             "--title", title,
             "--body", body],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ✗ Failed to create PR: {result.stderr}")
            return None

        # Parse PR URL from output
        pr_url = result.stdout.strip()

        # Get PR number
        pr_number = None
        if pr_url:
            # Extract number from URL: https://github.com/user/repo/pull/123
            parts = pr_url.split("/")
            if len(parts) > 0:
                pr_number = int(parts[-1])

        print(f"  ✓ Created PR: {pr_url}")

        return {
            "number": pr_number,
            "url": pr_url
        }

    def get_pr_comments(self, pr_number: int) -> List[Dict]:
        """
        Get comments from a pull request.

        Args:
            pr_number: PR number

        Returns:
            List of comment dicts with 'author', 'body', 'created_at'
        """
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "comments"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ✗ Failed to get PR comments: {result.stderr}")
            return []

        data = json.loads(result.stdout)
        return data.get("comments", [])

    def get_pr_review_comments(self, pr_number: int) -> List[Dict]:
        """
        Get review comments from a pull request.

        Args:
            pr_number: PR number

        Returns:
            List of review comment dicts
        """
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "reviews"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ✗ Failed to get PR reviews: {result.stderr}")
            return []

        data = json.loads(result.stdout)
        return data.get("reviews", [])
