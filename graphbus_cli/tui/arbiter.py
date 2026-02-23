"""Arbiter agent for conflict resolution."""

from typing import Dict, Any, List


class ArbiterAgent:
    """Detect and resolve conflicts between agent proposals."""
    
    def __init__(self):
        self.conflicts = []
    
    def detect_conflicts(self, proposals):
        """Detect conflicting proposals."""
        conflicts = []
        
        # Check if multiple proposals affect the same file
        files_affected = {}
        for prop in proposals:
            files = prop.get("files", [])
            for f in files:
                if f not in files_affected:
                    files_affected[f] = []
                files_affected[f].append(prop.get("id"))
        
        for file, prop_ids in files_affected.items():
            if len(prop_ids) > 1:
                conflicts.append({
                    "file": file,
                    "proposals": prop_ids,
                })
        
        self.conflicts = conflicts
        return conflicts
    
    def propose_resolution(self, conflicts):
        """Propose resolution for conflicts."""
        resolutions = []
        
        for conflict in conflicts:
            # Simple strategy: propose merging changes
            resolution = {
                "type": "merge_changes",
                "conflicting_proposals": conflict.get("proposals", []),
                "file": conflict.get("file"),
                "suggested_action": "Merge the proposed changes carefully",
            }
            resolutions.append(resolution)
        
        return resolutions
