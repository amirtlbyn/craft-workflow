---
description: A new endpoint that carries a business rule needs the task route.
tags: [routing]
plugins: ["../.."]
expected_outcome: The reply opens with a route line naming task, and never quick.
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite]
---

Add a `GET /api/v2/announcements/unread` endpoint to our Django REST project. It
returns the announcements the authenticated trader has not read yet, newest
first, and it returns at most 20 of them. An announcement counts as read when a
row exists in `AnnouncementRead` for that trader and that announcement.

No database schema changes. The models already exist.
