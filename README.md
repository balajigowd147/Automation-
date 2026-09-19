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
    A[Google Classroom] --> B[Classroom API]
    B --> C[Classroom Poller]
    C --> D[AI Router]

    D --> E[Assignment Flow]
    D --> F[Study Material Flow]

    %% Assignment Flow
    E --> G[Submission Status Check]
    G --> H[Artifact Matcher]
    H --> I[Python + Qwen3]
    I --> J[Correct Artifact]
    J --> K[Playwright Browser Agent]
    K --> L[Upload]
    L --> M[Human Review]
    M --> N[Turn In]

    %% Study Material Flow
    F --> O[Download Material]
    O --> P[Artifact Registry]
    P --> Q[File Reader]
    Q --> R[Qwen3 Summarization]
    R --> S[Summary Output]

    %% Local Documents
    T[Local Documents] --> U[Watchdog]
    U --> P

    %% Registry connection
    P --> H


