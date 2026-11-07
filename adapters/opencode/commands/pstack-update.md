---
description: Check and synchronize remote Pstack updates across all agents (/pstack-update)
---

Check and synchronize Pstack repository and global agent skills:
1. Run `pstack update --check` to query remote repository status.
2. If new commits are detected, execute `pstack update` to pull changes and remount global symlinks.
3. Run `pstack status` to confirm all 8 local agent mounts remain active.
