# AtelierMarie Technical Documentation

Comprehensive technical reference organized by topic and audience.

## Quick Navigation

### 👤 For New Developers
- **Start here:** `guides/GETTING_STARTED.md` — Local setup in 5 minutes
- **Common workflows:** `guides/DEVELOPER_WORKFLOWS.md` — Add feature, fix bug, debug issues
- **Architecture:** `architecture/SYSTEM_DESIGN.md` — How the system works
- **API endpoints:** `api/ENDPOINTS.md` — All 60+ routes with examples

### 🏗️ For Architects & Tech Leads
- **System architecture:** `architecture/SYSTEM_DESIGN.md` — Layer 1 vs Layer 2, data flows
- **Database design:** `database/SCHEMA.md` — Tables, constraints, decisions
- **Design decisions:** `architecture/DECISIONS.md` — Why we chose X over Y

### 🔌 For API Consumers & Frontend Developers
- **API reference:** `api/ENDPOINTS.md` — 60+ endpoints with examples
- **Authentication:** `api/AUTHENTICATION.md` — OAuth, JWT, sessions
- **Error handling:** `api/ERROR_HANDLING.md` — Standard envelope, codes

### 🗄️ For DevOps & Database Administrators
- **Database schema:** `database/SCHEMA.md` — Tables, indexes, constraints
- **Migrations:** `database/MIGRATIONS.md` — Alembic schema changes
- **Operations:** `operations/` — Deployment, health, troubleshooting

### 🧪 For QA & Testing
- **Test plans:** `testing/` — Feature-specific test scenarios
- **Testing guide:** `guides/TESTING_GUIDE.md` — Standards + patterns

### 📚 For Reference
- **Research:** `research/` — Feature investigations, explorations
- **Notes:** `notes/` — Implementation details, archived decisions

---

## Folder Structure

```
technical_documentation/
├── guides/              # Developer guides
│   ├── GETTING_STARTED.md
│   ├── DEVELOPER_WORKFLOWS.md
│   ├── TESTING_GUIDE.md
│   └── CODING_STANDARDS.md
│
├── architecture/        # System design
│   ├── SYSTEM_DESIGN.md
│   ├── DECISIONS.md
│   └── LAYERS.md
│
├── api/                 # API reference
│   ├── ENDPOINTS.md
│   ├── AUTHENTICATION.md
│   ├── ERROR_HANDLING.md
│   ├── PAGINATION.md
│   └── WEBHOOKS.md
│
├── database/            # Database & schema
│   ├── SCHEMA.md
│   ├── INDEXES.md
│   ├── MIGRATIONS.md
│   ├── RELATIONSHIPS.md
│   └── ANALYTICS.md
│
├── operations/          # DevOps & operations
│   ├── DEPLOYMENT.md
│   ├── HEALTH_CHECKS.md
│   ├── TROUBLESHOOTING.md
│   ├── COURIER_OPERATIONS.md
│   └── BACKUP_RECOVERY.md
│
├── testing/             # QA & test plans
│   ├── FEATURE_TEST_PLANS/
│   └── MANUAL_TEST_FLOWS.md
│
├── research/            # Investigations & explorations
│   └── FEATURE_INVESTIGATIONS/
│
└── notes/               # Implementation notes
    ├── IMPLEMENTATION_NOTES/
    └── ARCHIVED_DECISIONS/
```

---

## Where to Start

**First time?** → `guides/GETTING_STARTED.md`

**Adding a feature?** → `guides/DEVELOPER_WORKFLOWS.md`

**Understanding the system?** → `architecture/SYSTEM_DESIGN.md`

**API question?** → `api/ENDPOINTS.md`

**Database question?** → `database/SCHEMA.md`

---

## Keep Docs in Sync

When you change code:
- New endpoint? Update `api/ENDPOINTS.md`
- New table? Update `database/SCHEMA.md`
- New workflow? Update `guides/DEVELOPER_WORKFLOWS.md`
- New issue found? Update `operations/TROUBLESHOOTING.md`

**Golden rule:** If code and docs disagree, docs are stale. Fix them.

---

See also: `CLAUDE.md` (project rules), `openspec/changes/*/design.md` (feature specs)
