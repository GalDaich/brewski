# Repository workflow

After a successful merge, delete the merged source branch both locally and on
GitHub, and prune stale remote-tracking references. Keep `main` and preserve
recovery tags. Verify that the source branch's commits are included in the
merge before deleting it; do not delete unmerged work.
