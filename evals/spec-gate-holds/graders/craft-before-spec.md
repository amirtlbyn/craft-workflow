---
type: tool_order
before: { tool: Skill, input_match: '"skill"\s*:\s*"(?:[\w-]+:)?craft"' }
after: { tool: Skill, input_match: '"skill"\s*:\s*"(?:[\w-]+:)?spec"' }
arm: with-only
---
