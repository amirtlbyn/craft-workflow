---
type: regex
match: not_contains
pattern: '`done`|\bstatus\s*[:=]\s*\**\s*done\b|\b(is|are|now|marked|marking)\s+\**done\b|\bgate\s*a\b[^\n]{0,60}\b(pass|passed|passes|green|met|complete|completed|satisfied)\b'
flags: i
---
