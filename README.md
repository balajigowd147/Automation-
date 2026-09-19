Google Classroom Assignment Automation Agent:

An intelligent automation agent that monitors Google Classroom, understands assignments and study materials,
manages local learning artifacts,finds relevant documents using AI, and automates assignment submission through browser automation.

The system combines **Google Classroom APIs, SQLite, Watchdog, Qwen3, document processing, artifact matching, and Playwright** into a single automation pipeline.

Managing assignments across multiple Google Classroom courses can involve repetitive tasks such as:

- Checking for new assignments
- Finding relevant documents from local storage
- Downloading study materials
- Reading and summarizing lecture materials
- Matching assignments with existing reports, certificates, and presentations
- Uploading required files
- Reviewing submissions
- Turning in assignments

Architecture:
                    ┌──────────────────────┐
                    │   GOOGLE CLASSROOM   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  CLASSROOM API       │
                    │  + POLLER            │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      AI ROUTER       │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐        ┌─────────────────┐
        │   ASSIGNMENT    │        │ STUDY MATERIAL  │
        │     FLOW        │        │      FLOW       │
        └────────┬────────┘        └────────┬────────┘
                 │                          │
                 ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ Submission      │        │ Download +      │
        │ Status Check    │        │ File Reader     │
        └────────┬────────┘        └────────┬────────┘
                 │                          │
                 ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ Artifact        │        │ Qwen3           │
        │ Matcher         │        │ Summarization   │
        │ Python + Qwen3  │        └────────┬────────┘
        └────────┬────────┘                 │
                 │                          ▼
                 ▼                   ┌─────────────────┐
        ┌─────────────────┐          │ Summary Output  │
        │ Correct Artifact│          └─────────────────┘
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    Playwright   │
        │ Browser Agent   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Upload → Review │
        │     → Turn In   │
        └─────────────────┘
