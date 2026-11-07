# Data model

All tables live in a single SQLite database. Foreign keys are enabled on
every connection, so cascades and `SET NULL` behave as declared.

## Entities

- **`projects`** — top-level container. Unique by `name`.
- **`assignees`** — people. Unique by `name`.
- **`sprints`** — scheduled windows under a project (`project_id`).
  Unique by (`project_id`, `name`).
- **`tasks`** — work items. Carry `status`
  (`todo | in_progress | blocked | done`), `estimate`, optional
  `sprint_id` and `assignee_id`, optional `completed_at`.
- **`subtasks`** — nested work items under a task; cascade on delete.
- **`dependencies`** — directed edges between two tasks.
  `kind` is one of `blocks | relates_to | duplicates`. Unique per
  (from, to, kind). A task cannot depend on itself.
- **`labels`** — tags. Unique by `name`; M2M with tasks through
  `task_labels`.
- **`comments`** — threaded attachments, each belonging to either a
  task or a project (never both).

## FTS indexes

Three virtual tables keep search in sync with writes:

- `projects_fts(name, description)`
- `tasks_fts(title, description)`
- `comments_fts(body)`

Triggers (`ai`, `au`, `ad`) replicate inserts, updates and deletes to
the FTS tables so no manual reindex is needed.

## Cascades

- Deleting a project deletes its sprints, tasks, comments.
- Deleting a task deletes its subtasks, dependency edges, comments,
  `task_labels` rows.
- Deleting an assignee sets `tasks.assignee_id` to `NULL`.
- Deleting a sprint sets `tasks.sprint_id` to `NULL`.
- Deleting a label removes its `task_labels` rows.
