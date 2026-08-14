# django_drf — API Reference

A Django + DRF sandbox demonstrating a **standardized query-parameter contract** (filter / search / sort / paginate) and a **consistent JSON envelope** across both ORM-backed and non-model endpoints.

The shared machinery lives in `core/`; see [core/README.md](core/README.md) for how to replicate the pattern in a new project.

---

## Quick start

```bash
uv sync
```

```bash
.venv/bin/python manage.py migrate && .venv/bin/python manage.py runserver
```

Base URL below is assumed to be `http://localhost:8000`.

---

## Endpoint index

| Endpoint | Backing | Methods | Default sort |
|---|---|---|---|
| `/api/items/` | `miniapp.Item` (ORM) | GET, POST, PUT, PATCH, DELETE | `created_at,desc` |
| `/api/tenants/` | `miniapp.Tenant` (ORM) | GET, POST, PUT, PATCH, DELETE | `name,asc` |
| `/api/feedback/` | `miniapp.Feedback` (ORM, 2 FKs) | GET, POST, PUT, PATCH, DELETE | `created_at,desc` |
| `/api/analytics/feedback/` | `analytics.Feedback` (ORM) | GET, POST, PUT, PATCH, DELETE | `created_at,desc` |
| `/api/products/` | **static Python list — no ORM** | GET | `name,asc` |

Detail routes are `/<endpoint>/{id}/` for every ORM endpoint. `/api/products/` is list-only.

---

## The query-parameter contract

Every list endpoint accepts the same four families of parameter. They compose freely — filter, then search, then sort, then paginate.

| Concern | Syntax | Example |
|---|---|---|
| Pagination | `?page=N&size=M` | `?page=2&size=25` |
| Sorting | `?sort=field,asc` / `?sort=field,desc` | `?sort=name,asc` |
| Multi-sort (ORM only) | `?sort=f1,dir1,f2,dir2` | `?sort=rating,desc,created_at,asc` |
| Filtering | `?field=value` | `?rating=5` |
| Search | `?search=term` | `?search=widget` |

**Pagination notes**
- `page` is **1-based** in the request; `data.page.number` in the response is **0-based**.
- `size` defaults to `10` and is hard-capped at `100` — `?size=500` silently yields 100.
- A page past the end returns **HTTP 404** `{"detail": "Invalid page."}`, *not* an empty envelope.

**Sorting notes**
- The param is `sort`, not DRF's default `ordering`. **`?ordering=name` is silently ignored.**
- Direction is optional: `?sort=name` is treated as `name,asc`.
- A field not listed in the view's `ordering_fields` is silently dropped and the default ordering applies — the response's `data.sort` reports the ordering that actually took effect, so you can detect this.

---

## Response envelope

Every **list** response is wrapped:

```json
{
  "success": true,
  "timestamp": "2026-08-14T13:55:13.192620+00:00",
  "data": {
    "content": [ /* the actual rows */ ],
    "first": true,
    "last": false,
    "page":  { "elements": 2, "number": 0, "offset": 1, "size": 2 },
    "total": { "elements": 5, "pages": 3 },
    "sort":  {
      "default": false,
      "field": "price",
      "direction": "desc",
      "fields": [ { "field": "price", "direction": "desc" } ]
    }
  },
  "message": "Data retrieved successfully.",
  "status": 200
}
```

| Field | Meaning |
|---|---|
| `data.content` | The serialized rows for this page |
| `data.first` / `data.last` | Whether this is the first / last page |
| `data.page.elements` | Rows **on this page** |
| `data.page.number` | **0-based** page index |
| `data.page.offset` | 1-based index of the first row on this page |
| `data.page.size` | Effective page size after the 100 cap |
| `data.total.elements` | Rows matching the filter **across all pages** |
| `data.total.pages` | Total page count |
| `data.sort` | The ordering **actually applied**; `default: true` means the view's default was used |
| `data.sort.field` / `.direction` | The primary sort term |
| `data.sort.fields` | Every applied sort term, in precedence order (see multi-field sort) |

> **Detail, create, and update responses are NOT enveloped.** `GET /api/items/1/` returns the bare serialized object. The envelope comes from the paginator, which only runs on list actions.

---

## Endpoint reference

### `GET /api/items/`

| Param | Type | Match |
|---|---|---|
| `name` | string | partial, case-insensitive |
| `feedback_content` | string | partial — traverses `feedback__content` |
| `feedback_rating` | number | exact — traverses `feedback__rating` |
| `feedback_tenant_name` | string | partial — traverses `feedback__tenant__name` |
| `search` | string | across `name`, `description` |
| `sort` | `created_at` \| `name` | default `created_at,desc` |

```bash
curl "http://localhost:8000/api/items/?name=mount&sort=name,asc&page=1&size=5"
```

<details>
<summary>Expected response</summary>

```json
{
  "success": true,
  "timestamp": "2026-08-14T13:55:13.192620+00:00",
  "data": {
    "content": [
      {
        "id": 3,
        "name": "Mount Flex",
        "description": "A flexible mounting bracket.",
        "created_at": "2026-03-28T02:10:09.568548Z"
      }
    ],
    "first": true, "last": true,
    "page":  { "elements": 1, "number": 0, "offset": 1, "size": 5 },
    "total": { "elements": 1, "pages": 1 },
    "sort":  {
      "default": false, "field": "name", "direction": "asc",
      "fields": [ { "field": "name", "direction": "asc" } ]
    }
  },
  "message": "Data retrieved successfully.",
  "status": 200
}
```
</details>

> The `feedback_*` filters cross a reverse FK. They carry `distinct=True`, so an `Item` with several matching `Feedback` rows is returned once and counted once in `total.elements`.

---

### `GET /api/tenants/`

| Param | Type | Match |
|---|---|---|
| `name` | string | **exact** (declared via `filterset_fields`, not a `FilterSet`) |
| `sort` | `name` \| `created_at` | default `name,asc` |

```bash
curl "http://localhost:8000/api/tenants/?name=Acme%20Corp&sort=created_at,desc"
```

> No `?search=` here — `TenantViewSet` omits `SearchFilter`. And `?name=acme` matches nothing; this filter is exact and case-sensitive, unlike every other `name` filter in the project.

---

### `GET /api/feedback/`  (miniapp)

| Param | Type | Match |
|---|---|---|
| `content` | string | partial |
| `rating` | number | exact |
| `item_name` | string | partial — traverses `item__name` |
| `tenant_name` | string | partial — traverses `tenant__name` |
| `search` | string | across `content`, `item__name`, `tenant__name` |
| `sort` | `rating` \| `created_at` \| `item__name` \| `tenant__name` | default `created_at,desc` |

```bash
curl "http://localhost:8000/api/feedback/?rating=5&tenant_name=acme&sort=created_at,desc&size=2"
```

<details>
<summary>Expected response</summary>

```json
{
  "success": true,
  "timestamp": "2026-08-14T13:55:23.621634+00:00",
  "data": {
    "content": [
      {
        "id": 45,
        "content": "Very satisfied with the performance.",
        "rating": 5,
        "created_at": "2026-03-28T02:10:09.574511Z",
        "item": 6,
        "tenant": 7
      }
    ],
    "first": true, "last": false,
    "page":  { "elements": 1, "number": 0, "offset": 1, "size": 2 },
    "total": { "elements": 7, "pages": 4 },
    "sort":  {
      "default": false, "field": "created_at", "direction": "desc",
      "fields": [ { "field": "created_at", "direction": "desc" } ]
    }
  },
  "message": "Data retrieved successfully.",
  "status": 200
}
```
</details>

> The FK sort fields use ORM double-underscore syntax directly: `?sort=tenant__name,asc`. The queryset uses `select_related('item', 'tenant')`, so sorting across the FK costs no extra queries.
>
> `item` and `tenant` serialize as bare integer PKs — `fields = '__all__'` on a plain `ModelSerializer` gives no nesting.

---

### `GET /api/analytics/feedback/`

A second, unrelated `Feedback` model. Demonstrates reusing `core/` from a different app with zero shared code.

| Param | Type | Match |
|---|---|---|
| `rating` | number 1–5 | exact |
| `is_resolved` | `true` \| `false` | exact |
| `search` | string | across `user_email`, `content` |
| `sort` | `created_at` \| `rating` | default `created_at,desc` |

```bash
curl "http://localhost:8000/api/analytics/feedback/?is_resolved=false&rating=1&sort=created_at,desc"
```

> Registered with an explicit router `basename='analytics-feedback'` — `miniapp` exposes a `Feedback` viewset too, and both would otherwise derive `feedback` from the model name and clobber each other's URL names. Reverse with `analytics-feedback-list` / `-detail`.

---

### `GET /api/products/`  — non-model endpoint

Backed by `STATIC_PRODUCTS`, a plain list of dicts in `miniapp/views.py`. **No model, no migration, no queryset.** It accepts the same contract as every ORM endpoint via `ListDataMixin` — this is the point of the whole exercise.

| Param | Type | Match |
|---|---|---|
| `name` | string | partial, case-insensitive |
| `category` | `hardware` \| `software` | partial, case-insensitive |
| `sort` | `name` \| `price` \| `category` | default `name,asc` |

```bash
curl "http://localhost:8000/api/products/?category=software&sort=price,desc&size=2"
```

<details>
<summary>Expected response</summary>

```json
{
  "success": true,
  "timestamp": "2026-08-14T13:55:13.192620+00:00",
  "data": {
    "content": [
      { "id": 10, "name": "Component Elite", "category": "software", "price": 249.99, "in_stock": true },
      { "id": 6,  "name": "Contraption X",   "category": "software", "price": 199.99, "in_stock": false }
    ],
    "first": true, "last": false,
    "page":  { "elements": 2, "number": 0, "offset": 1, "size": 2 },
    "total": { "elements": 5, "pages": 3 },
    "sort":  {
      "default": false, "field": "price", "direction": "desc",
      "fields": [ { "field": "price", "direction": "desc" } ]
    }
  },
  "message": "Data retrieved successfully.",
  "status": 200
}
```
</details>

**Differences from the ORM endpoints:**

| | ORM endpoints | `/api/products/` |
|---|---|---|
| Multi-field sort | supported | **single field only** — `?sort=a,asc,b,desc` sorts by `a` only |
| `?search=` | supported where `search_fields` is set | **not supported** |
| Filter matching | per-`FilterSet` (exact or partial) | always partial/`icontains` |
| `None` values | DB collation decides | always sort last |

---

## Developer notes

Behaviors worth knowing before you build a frontend against this. Each was verified against the running app.

**1. `data.sort` reports what was applied, not what was asked for.**
`CustomOrderingFilter` and `ListDataMixin` publish their resolved ordering, and the paginator reads it back. So `?sort=bogus_field,asc` reports `{"default": true, "field": "created_at", "direction": "desc"}` — the ordering the rows are genuinely in — rather than echoing the rejected field. Safe to drive sort indicators off. The one exception: a view that paginates *without* either component has no source of truth, so the paginator falls back to echoing the raw parameter.

**2. Multi-field sorts appear in full under `sort.fields`.**
`field`/`direction` carry the primary term only. `?sort=rating,desc,created_at,asc` reports `fields: [{rating, desc}, {created_at, asc}]`, in precedence order. Invalid terms are dropped from that list, so it always reflects the real ORDER BY.

**3. `/api/products/` sorts by `name,asc` by default — and says so.**
`ListDataMixin` views declare `default_ordering` rather than the `ordering` attribute ORM views use, and publish it explicitly so the envelope stays accurate on an endpoint that has no `created_at` field at all.

**4. `?ordering=` does nothing.**
`CustomOrderingFilter.ordering_param = 'sort'`, so DRF's stock param is inert. `?ordering=name`, `?ordering=-name` and `?ordering=bogus` all return rows in the view's default order, with no error. The envelope does stay honest — it reports `default: true` — so a client that asked for a sort and got `default: true` back can detect that something was ignored. It just won't be told *what*.

**5. `size` above 100 is capped silently.**
No error, no warning — `?size=500` returns `page.size: 100`. Requesting "everything in one page" fails quietly past 100 rows.

**6. Odd-length `sort` values drop trailing fields.**
The parser walks the CSV in pairs. `?sort=name,price` reads `price` as a *direction*, not a second field — it isn't `desc`, so it's discarded and you get `name,asc`. Always send explicit directions in multi-field sorts.

**7. Envelope only wraps list responses.**
Detail, create, and update return bare serialized objects. Error responses are DRF's defaults (`{"detail": ...}`) and are never enveloped either — a frontend cannot assume `response.data.content` exists.

---

## ⚠️ Traps when extending this

The notes above describe stable behavior a client can rely on. These are the sharp edges you can cut yourself on while *adding* endpoints. Each was reproduced against this codebase.

### Never put a reverse-FK path in `ordering_fields`

Ordering across a multi-valued relation (`Item` → many `Feedback`) adds a JOIN, and the JOIN multiplies rows. This is a Django/SQL behavior that **DRF inherits and does not guard against** — reproduced below with stock `rest_framework.filters.OrderingFilter`, no project code involved and no filtering applied:

```
?ordering=feedback__content  ->  51 rows, 20 distinct items
```

It gets worse when paginated, because Django strips `ORDER BY` when building a `COUNT` query — so the count and the fetch disagree:

```
qs.count()     -> 20    (ORDER BY stripped, join vanishes)
len(list(qs))  -> 51    (fetch keeps the join)
```

The paginator trusts `count()`. Walking every page of such a view:

| | |
|---|---|
| envelope `total.elements` | 20 |
| `total.pages` | 2 |
| rows actually walked | 20 |
| distinct items among them | **14** |
| items never returned on any page | **6** |

Six records become unreachable through the API, silently. **Forward FKs are safe** — `Feedback` → `item`/`tenant` is many-to-one and cannot multiply rows (`count=50 fetched=50`), which is why `FeedbackViewSet` can sort on `item__name` and `tenant__name` without trouble. The rule is about the *direction* of the relation, not the presence of `__`.

DRF solves this for `SearchFilter` only, via `must_call_distinct()` → an `Exists()` subquery. Every `distinct`-related line in `rest_framework/filters.py` is in `SearchFilter`; `OrderingFilter` has none.

### `distinct=True` is defeated by ordering on a joined column

The `ItemFilter.feedback_*` filters carry `distinct=True`, which fixes duplicates from the filter join. But `SELECT DISTINCT` adds the `ORDER BY` column to the SELECT list, so rows differing only in that column stop being duplicates:

| Ordering applied alongside `?feedback_rating=5` | Rows |
|---|---|
| `name` (local column) | 5 ✅ |
| `feedback__rating` (joined, all values identical) | 5 ✅ |
| `feedback__content` (joined, values differ) | **7** ❌ |

Same root cause as above, and the same rule avoids it: keep `ordering_fields` free of reverse-relation paths.

### Pagination without an ordering component fabricates `data.sort`

`StandardResultsSetPagination` reads the ordering published by `CustomOrderingFilter` / `ListDataMixin`. A view that paginates with **neither** has no source of truth, so it falls back to echoing the raw `?sort=` parameter. A view wired with only `SearchFilter` returned rows in arbitrary database order — Django raised `UnorderedObjectListWarning` — while the envelope reported `{"field": "name", "direction": "desc"}`. Every view in this project is wired correctly; this is one forgotten `filter_backends` line away.

### `sort.field` can be `null`

A `ListDataMixin` view with no `default_ordering` and no `?sort=` reports `{"default": true, "field": null, "direction": null, "fields": []}`. That is honest — nothing was sorted — but a frontend assuming a string will break. Give mixin views a `default_ordering`.

### `ListDataMixin` sorts on one field only

`?sort=name,asc,id,desc` applies and reports only `name`. The metadata stays consistent with reality, but the client's second term is dropped without complaint. See the comparison table in the `/api/products/` section above.

### The applied ordering is request-scoped

`core/ordering.py` stashes the resolved ordering on the DRF `Request`. A view that paginates two different querysets within one request would have the second read the first's ordering. No such view exists here.

---

## Tests

```bash
.venv/bin/python manage.py test
```

| File | Covers |
|---|---|
| `core/tests/test_filtering.py` | sort translation, invalid-field fallback, FK-traversal filters |
| `core/tests/test_pagination.py` | envelope shape, page math |
| `core/tests/test_mixins.py` | `ListDataMixin` filter / sort / paginate on plain lists |

Lint and type-check:

```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/ty check
```
