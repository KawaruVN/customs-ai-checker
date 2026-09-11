# TASK-001 â€” Project Foundation

Status: DONE
Priority: P1  
Owner: Gemini #1 â€” Main Developer  
Reviewer: Gemini #2 â€” Reviewer / QA  
Target Version: V1  
Dependencies: None  
Related ADR: None

---

## 1. OBJECTIVE

Dá»±ng ná»n táº£ng code tá»‘i thiá»ƒu cho Customs AI Checker theo `PROJECT_CONSTITUTION.md`, `MASTER_SPEC.md` vÃ  `ARCHITECTURE.md`.

Sau task nÃ y, repository pháº£i trá»Ÿ thÃ nh má»™t Python project cÃ³ cáº¥u trÃºc rÃµ rÃ ng, cháº¡y Ä‘Æ°á»£c, test Ä‘Æ°á»£c vÃ  sáºµn sÃ ng cho cÃ¡c task nghiá»‡p vá»¥ tiáº¿p theo.

---

## 2. BACKGROUND

Hiá»‡n repository má»›i cÃ³ cÃ¡c tÃ i liá»‡u kiáº¿n trÃºc vÃ  thÆ° má»¥c khung.

ChÆ°a cÃ³ application foundation chÃ­nh thá»©c.

Task nÃ y chá»‰ táº¡o ná»n mÃ³ng ká»¹ thuáº­t.

KhÃ´ng triá»ƒn khai document AI, OCR, extraction, rule engine hay business logic trong task nÃ y.

---

## 3. SCOPE

Task nÃ y PHáº¢I:

1. Khá»Ÿi táº¡o Python project.
2. Táº¡o package `customs_ai`.
3. Táº¡o cáº¥u trÃºc module ná»n táº£ng theo `ARCHITECTURE.md`.
4. Táº¡o FastAPI application tá»‘i thiá»ƒu.
5. Táº¡o endpoint health check.
6. Táº¡o configuration foundation.
7. Táº¡o logging foundation.
8. Táº¡o test framework.
9. Táº¡o `.gitignore`.
10. Táº¡o `.env.example`.
11. Táº¡o dependency/project configuration.
12. Äáº£m báº£o project cháº¡y local.
13. Viáº¿t unit/integration test tá»‘i thiá»ƒu cho foundation.

---

## 4. OUT OF SCOPE

KHÃ”NG triá»ƒn khai:

- PDF parsing;
- Excel parsing;
- OCR;
- document classification;
- AI provider thá»±c;
- Gemini API;
- OpenAI API;
- document extraction;
- canonical customs schema chi tiáº¿t;
- rule engine;
- HS code;
- legal checking;
- customer profile;
- production authentication;
- Docker;
- PostgreSQL;
- Streamlit UI Ä‘áº§y Ä‘á»§.

KhÃ´ng gá»i báº¥t ká»³ LLM/API AI nÃ o trong TASK-001.

---

## 5. EXPECTED PROJECT STRUCTURE

Developer cÃ³ thá»ƒ Ä‘iá»u chá»‰nh nháº¹ náº¿u cÃ³ lÃ½ do ká»¹ thuáº­t há»£p lÃ½, nhÆ°ng pháº£i giá»¯ architecture boundaries.

Má»¥c tiÃªu tá»‘i thiá»ƒu:

```text
customs-ai-checker/
â”‚
â”œâ”€â”€ pyproject.toml
â”œâ”€â”€ .gitignore
â”œâ”€â”€ .env.example
â”‚
â”œâ”€â”€ config/
â”‚   â””â”€â”€ app.yaml
â”‚
â”œâ”€â”€ src/
â”‚   â””â”€â”€ customs_ai/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â”œâ”€â”€ main.py
â”‚       â”œâ”€â”€ api/
â”‚       â”‚   â”œâ”€â”€ __init__.py
â”‚       â”‚   â””â”€â”€ routes/
â”‚       â”‚       â”œâ”€â”€ __init__.py
â”‚       â”‚       â””â”€â”€ health.py
â”‚       â”œâ”€â”€ application/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ domain/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ ingestion/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ parsers/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ classification/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ extraction/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ normalization/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ matching/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ rules/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ checks/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ ai/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ repositories/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ reporting/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â”œâ”€â”€ audit/
â”‚       â”‚   â””â”€â”€ __init__.py
â”‚       â””â”€â”€ utils/
â”‚           â””â”€â”€ __init__.py
â”‚
â””â”€â”€ tests/
    â”œâ”€â”€ unit/
    â””â”€â”€ integration/
```

KhÃ´ng cáº§n táº¡o file rá»—ng vÃ´ nghÄ©a náº¿u package structure cÃ³ thá»ƒ giá»¯ báº±ng cÃ¡ch khÃ¡c, nhÆ°ng import path pháº£i rÃµ rÃ ng.

---

## 6. INPUT

KhÃ´ng cÃ³ business input.

Developer sá»­ dá»¥ng:

- repository hiá»‡n táº¡i;
- project documents;
- Python environment.

---

## 7. OUTPUT

Sau task nÃ y pháº£i cÃ³:

1. Python package import Ä‘Æ°á»£c.
2. FastAPI app khá»Ÿi Ä‘á»™ng Ä‘Æ°á»£c.
3. Health endpoint hoáº¡t Ä‘á»™ng.
4. Configuration load Ä‘Æ°á»£c.
5. Logging hoáº¡t Ä‘á»™ng.
6. Test runner cháº¡y Ä‘Æ°á»£c.
7. `.gitignore` há»£p lá»‡.
8. `.env.example` khÃ´ng chá»©a secret tháº­t.

---

## 8. FUNCTIONAL REQUIREMENTS

### FR-01 â€” Application startup

Pháº£i cÃ³ FastAPI application entry point.

VÃ­ dá»¥:

```python
app = FastAPI(...)
```

Application pháº£i cháº¡y Ä‘Æ°á»£c báº±ng command Ä‘Æ°á»£c ghi trong README hoáº·c Developer completion report.

### FR-02 â€” Health endpoint

Táº¡o:

```text
GET /health
```

Expected HTTP status:

```text
200
```

Expected response tá»‘i thiá»ƒu:

```json
{
  "status": "ok"
}
```

CÃ³ thá»ƒ thÃªm version/app name náº¿u há»£p lÃ½.

### FR-03 â€” Configuration

Táº¡o configuration mechanism cho non-secret settings.

Pháº£i há»— trá»£ Ã­t nháº¥t:

- app name;
- environment;
- log level.

Æ¯u tiÃªn:

```text
config/app.yaml
+
environment variable override
```

KhÃ´ng hard-code config ráº£i rÃ¡c.

### FR-04 â€” Logging

Táº¡o logging configuration cÆ¡ báº£n.

Log startup Ä‘Æ°á»£c phÃ©p.

KhÃ´ng log secret.

### FR-05 â€” Python package

`customs_ai` pháº£i import Ä‘Æ°á»£c trong test/runtime.

### FR-06 â€” Test foundation

`pytest` hoáº·c lá»±a chá»n tÆ°Æ¡ng Ä‘Æ°Æ¡ng pháº£i hoáº¡t Ä‘á»™ng.

### FR-07 â€” Dependency management

Dependency pháº£i Ä‘Æ°á»£c Ä‘á»‹nh nghÄ©a táº­p trung trong:

```text
pyproject.toml
```

KhÃ´ng táº¡o nhiá»u file dependency trÃ¹ng láº·p náº¿u khÃ´ng cÃ³ lÃ½ do.

---

## 9. NON-FUNCTIONAL REQUIREMENTS

### NFR-01

AI allowed: NO.

### NFR-02

KhÃ´ng thÃªm framework agent.

### NFR-03

KhÃ´ng thÃªm vector database.

### NFR-04

KhÃ´ng thÃªm Redis, Celery, Kafka hoáº·c queue system.

### NFR-05

KhÃ´ng thÃªm Docker náº¿u khÃ´ng thá»±c sá»± cáº§n cho task.

### NFR-06

Code pháº£i Ä‘Æ¡n giáº£n vÃ  dá»… hiá»ƒu.

### NFR-07

Business logic khÃ´ng Ä‘Æ°á»£c Ä‘áº·t trong FastAPI route.

### NFR-08

KhÃ´ng cÃ³ dependency vendor AI trong task nÃ y náº¿u chÆ°a cáº§n.

### NFR-09

KhÃ´ng commit generated cache/build artifacts.

---

## 10. BUSINESS RULES

None.

TASK-001 khÃ´ng triá»ƒn khai nghiá»‡p vá»¥ háº£i quan.

---

## 11. DATA MODEL IMPACT

KhÃ´ng táº¡o canonical customs schema hoÃ n chá»‰nh.

CÃ³ thá»ƒ táº¡o model/config tá»‘i thiá»ƒu phá»¥c vá»¥ app startup náº¿u cáº§n.

KhÃ´ng Ä‘Æ°á»£c tá»± thiáº¿t káº¿ sÃ¢u:

- Invoice;
- PackingList;
- CustomsDeclaration;
- Rule;
- CheckResult.

CÃ¡c entity Ä‘Ã³ thuá»™c task sau.

---

## 12. CONSTRAINTS

Developer pháº£i Ä‘á»c trÆ°á»›c:

```text
PROJECT_CONSTITUTION.md
MASTER_SPEC.md
ARCHITECTURE.md
TASK_TEMPLATE.md
```

Developer khÃ´ng Ä‘Æ°á»£c:

- thay Ä‘á»•i cÃ¡c file trÃªn náº¿u task khÃ´ng yÃªu cáº§u;
- thay architecture;
- thÃªm dependency lá»›n vÃ´ lÃ½;
- táº¡o secret;
- implement feature ngoÃ i scope.

Náº¿u phÃ¡t hiá»‡n conflict giá»¯a cÃ¡c tÃ i liá»‡u:

dá»«ng pháº§n bá»‹ conflict vÃ  bÃ¡o Project Leader.

---

## 13. EDGE CASES

Pháº£i xem xÃ©t tá»‘i thiá»ƒu:

- thiáº¿u `config/app.yaml`;
- environment variable override;
- invalid log level;
- import package trong test;
- app startup trong mÃ´i trÆ°á»ng development;
- config khÃ´ng chá»©a secret tháº­t.

KhÃ´ng cáº§n xá»­ lÃ½ file upload trong task nÃ y.

---

## 14. ACCEPTANCE CRITERIA

### AC-01

Given repository sau implementation  
When cÃ i dependencies theo hÆ°á»›ng dáº«n  
Then application khá»Ÿi Ä‘á»™ng thÃ nh cÃ´ng.

### AC-02

Given application Ä‘ang cháº¡y  
When gá»i:

```text
GET /health
```

Then tráº£ HTTP 200.

### AC-03

Health response cÃ³:

```json
{
  "status": "ok"
}
```

hoáº·c response tÆ°Æ¡ng Ä‘Æ°Æ¡ng Ä‘Æ°á»£c document rÃµ.

### AC-04

`pytest` cháº¡y thÃ nh cÃ´ng.

### AC-05

CÃ³ Ã­t nháº¥t má»™t integration test xÃ¡c minh health endpoint.

### AC-06

CÃ³ test hoáº·c validation cho configuration loading.

### AC-07

KhÃ´ng cÃ³ API key/password/token tháº­t trong repository.

### AC-08

`.gitignore` bá» qua tá»‘i thiá»ƒu:

```text
.env
.venv/
__pycache__/
.pytest_cache/
*.pyc
data/uploads/
data/cache/
*.db
```

CÃ³ thá»ƒ Ä‘iá»u chá»‰nh Ä‘á»ƒ khÃ´ng ignore file database fixture cáº§n test.

### AC-09

`.env.example` chá»‰ chá»©a placeholder.

VÃ­ dá»¥:

```text
APP_ENV=development
LOG_LEVEL=INFO
```

KhÃ´ng cÃ³ credential tháº­t.

### AC-10

Developer khÃ´ng triá»ƒn khai functionality ngoÃ i pháº¡m vi task má»™t cÃ¡ch Ä‘Ã¡ng ká»ƒ.

---

## 15. TEST REQUIREMENTS

### Unit Tests

Tá»‘i thiá»ƒu:

- configuration load;
- configuration defaults/override náº¿u Ä‘Æ°á»£c implement;
- health response model náº¿u cÃ³.

### Integration Tests

Tá»‘i thiá»ƒu:

- FastAPI app startup;
- `GET /health` tráº£ HTTP 200.

### Failure Tests

Náº¿u config cÃ³ validation:

- invalid configuration pháº£i fail rÃµ rÃ ng.

### Regression Tests

ChÆ°a yÃªu cáº§u Golden Dataset trong TASK-001.

---

## 16. TEST DATA

Chá»‰ dÃ¹ng synthetic test data.

KhÃ´ng cáº§n document thá»±c.

---

## 17. OBSERVABILITY REQUIREMENTS

Application startup nÃªn log tá»‘i thiá»ƒu:

- app name;
- environment;
- startup success.

KhÃ´ng log:

- environment secrets;
- toÃ n bá»™ environment variables.

---

## 18. COST REQUIREMENTS

```text
AI allowed: NO
External paid API allowed: NO
```

TASK-001 pháº£i cháº¡y vá»›i chi phÃ­ váº­n hÃ nh AI báº±ng 0.

---

## 19. SECURITY / PRIVACY REQUIREMENTS

Pháº£i cÃ³ `.gitignore`.

KhÃ´ng commit:

- `.env`;
- secret;
- local production database;
- customer files.

`.env.example` chá»‰ chá»©a tÃªn biáº¿n + placeholder an toÃ n.

---

## 20. DEPENDENCIES

Depends on:

```text
None
```

NhÆ°ng pháº£i tuÃ¢n thá»§:

```text
PROJECT_CONSTITUTION.md
MASTER_SPEC.md
ARCHITECTURE.md
```

---

## 21. DELIVERABLES

Gemini #1 pháº£i cung cáº¥p:

1. Source code.
2. `pyproject.toml`.
3. `.gitignore`.
4. `.env.example`.
5. configuration file(s).
6. tests.
7. hÆ°á»›ng dáº«n cháº¡y ngáº¯n.
8. Developer Completion Report.

---

## 22. DEFINITION OF DONE

- [ ] Python project Ä‘Ã£ khá»Ÿi táº¡o.
- [ ] `customs_ai` import Ä‘Æ°á»£c.
- [ ] FastAPI app cháº¡y Ä‘Æ°á»£c.
- [ ] `/health` tráº£ HTTP 200.
- [ ] Configuration foundation hoáº¡t Ä‘á»™ng.
- [ ] Logging foundation hoáº¡t Ä‘á»™ng.
- [ ] Tests pass.
- [ ] KhÃ´ng gá»i AI.
- [ ] KhÃ´ng thÃªm dependency lá»›n ngoÃ i scope.
- [ ] KhÃ´ng cÃ³ secrets.
- [ ] Reviewer Gemini #2 APPROVE.
- [ ] Project Leader Ä‘á»“ng Ã½ Ä‘Ã³ng task.

---

## 23. DEVELOPER NOTES

Gemini #1 cáº­p nháº­t táº¡i Ä‘Ã¢y náº¿u cáº§n.

---

## 24. REVIEW NOTES

Gemini #2 cáº­p nháº­t táº¡i Ä‘Ã¢y khi review.

---

## 25. PROJECT LEADER DECISION

Pending.

---

# END OF TASK-001
