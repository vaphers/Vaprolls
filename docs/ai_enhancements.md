# AI Enhancements & Gemini Integration

## 1. Module Overview

Vaprolls provides optional AI-assisted analysis capabilities via `ai/gemini_enhancer.py`. Powered by Google's Gemini models (`gemini-2.0-flash`), this subsystem transforms raw diagnostic crawl data into structured executive summaries, prioritized fix roadmaps, and content quality evaluations.

Related documentation:
- Core analysis: [Analysis Pipeline](analysis_pipeline.md)
- Reporting formats: [Reporting & Exports Guide](reporting_and_exports.md)
- Storage schema: [Database Architecture](database_architecture.md)

---

## 2. Configuration & Activation

The AI enhancement subsystem requires a Google Gemini API key:

### 2.1 Environment Variable
Set the API key in your operating environment:
- **Linux / macOS**:
  ```bash
  export GEMINI_API_KEY="your-api-key-here"
  ```
- **Windows (PowerShell)**:
  ```powershell
  $env:GEMINI_API_KEY="your-api-key-here"
  ```
- **Windows (Command Prompt)**:
  ```cmd
  set GEMINI_API_KEY=your-api-key-here
  ```

### 2.2 Graceful Degradation
If no API key is provided, the application continues to operate with all standard technical SEO crawl, indexing, and analysis features. AI enhancement tasks are skipped gracefully without error.

---

## 3. Core Capabilities

When enabled, `GeminiEnhancer` executes four key analytical tasks:

```
[Completed Audit Data]
         │
         ▼
[GeminiEnhancer.enhance()]
         │
         ├─► 1. generate_executive_summary()
         │     └─ High-level narrative for stakeholders & clients
         │
         ├─► 2. generate_fix_priorities()
         │     └─ Ranked top 10 impactful remediation actions
         │
         ├─► 3. analyze_content_quality()
         │     └─ E-E-A-T signals & content depth scoring
         │
         └─► 4. classify_keyword_intent()
               └─ Intent mapping (Informational, Commercial, etc.)
```

### 3.1 Executive Summary Generation
Synthesizes total page count, health score, and top critical issues into a clear 3-to-5 paragraph executive narrative. Highlights root-cause architecture problems (e.g. indexation traps, broken redirect loops, missing security headers) in plain business language suitable for non-technical stakeholders.

### 3.2 Prioritized Fix Roadmap
Evaluates discovered issues and produces a prioritized Top 10 remediation list. Each action item includes:
- Specific problem description.
- Business and search ranking impact.
- Concrete technical fix instructions.

### 3.3 Content Quality & E-E-A-T Analysis
Evaluates sample page titles, descriptions, headings, and body copy to assess:
- Content depth and informativeness.
- Experience, Expertise, Authoritativeness, and Trustworthiness (E-E-A-T) signals.
- Recommendations for addressing thin copy or keyword cannibalization.

### 3.4 Keyword Search Intent Classification
Analyzes primary keywords extracted by the keyword analyzer and maps them to standard search intents:
- **Informational**: Queries seeking knowledge or answers.
- **Commercial**: Queries evaluating products, brands, or comparison guides.
- **Transactional**: Queries ready to purchase or convert.
- **Navigational**: Queries seeking specific brand destinations or logins.

---

## 4. Output Storage and Presentation

AI-generated summaries and priority roadmaps are serialized into the `config_json` field of the `audits` database table:
- Embedded automatically into generated HTML, Excel, and Word reports.
- Displayed in the web dashboard's summary card when viewing completed audits.
