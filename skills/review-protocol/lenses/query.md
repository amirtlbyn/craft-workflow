# Lens: query — database access cost

- **Ceiling:** High
- **Minimum confidence:** 0.7
- **Reads:** the diff, the models and migrations it touches, and these
  sections when an item needs them:
  `bin/craft-std technical TS-2 TS-3 TS-4 TS-5`. Load `django-practices` for the
  ORM conventions.

Do not repeat business-logic findings unless the defect **is** the query.

**Other stacks.** The items below name Django constructs. On another stack, run
`bin/craft-stack lens query --paths <changed paths>` and apply its notes in their
place.

## Evidence rule — not optional

Do not claim a query does or does not use an index unless you read the index
definition: `db_index=True`, `unique=True`, `ForeignKey`, `Meta.indexes`,
`Meta.unique_together`, `Meta.index_together`, or `AddIndex`, `AlterField`,
`RunSQL` in a migration. Quote it with `file:line`.

When you cannot find one, report the index status as unverified, and name the
table, the columns, and the files you searched. Never infer an index from a
column name. Composite indexes are prefix-ordered: `(a, b, c)` serves `a` and
`a, b`, not `b` alone. A leading-wildcard `LIKE`, or a function on the column
(`__date`, `__year`), defeats the index.

## Checklist — answer every item

1. **Index coverage** — for every changed filter, join, and `order_by`, an index
   you read covers the columns in order.
2. **N+1** — no loop, serializer, `__str__`, or admin display crosses a relation
   without `select_related` or `prefetch_related`. Count the queries.
3. **Boundedness** — every new queryset is bounded by a slice, a limit, or an
   indexed filter, on a table that grows.
4. **Query in a loop** — no per-row `.count()`, `.exists()`, `.get()`, or
   `.save()` where one aggregate, `in_bulk`, or `bulk_update` works.
5. **Lock scope** — no `select_for_update` or atomic block holds more rows or
   more time than needed.
6. **Replica routing** — reads use `read_db_alias` where correct, and no read on
   a replica follows its own write.
7. **Migration cost** — no migration locks or rewrites a large table. State the
   row-count order of magnitude.
8. **Raw SQL** — every raw query is parameterized.

## Severity

**High** — can stall a request path, lock a hot table, or scan a large table on a
common path. **Medium** — a measurable query-count or scan regression with
limited blast radius. **Low** — a smaller inefficiency.

In each finding, state the query, the table, the columns, the index with its
`file:line`, and the cost. Give the rewritten queryset or the index as code.
Always add a `Verification gaps:` line listing every unresolved index status.
