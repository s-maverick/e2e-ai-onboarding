# AI Product Operator Take-Home: End-to-End Candidate Onboarding System

**Author:** Sangam Patil

**Objective:** Build a functional end-to-end AI-powered candidate onboarding system from job listing to first day on Slack.

## Overview & Tech Stack

This prototype demonstrates a fully automated, AI-native hiring pipeline. It leverages a modern Python backend for heavy data-processing and LLM orchestration, paired with a React frontend for a clean candidate experience.

* **Frontend:** Next.js (React), TailwindCSS
* **Backend / API:** FastAPI (Python)
* **Database:** Supabase (PostgreSQL)
* **AI & Orchestration:** Google Gemini Pro/Flash, LangChain, `pdfplumber`

---

## Integration Architecture (Phases 1-6)

The system covers six distinct phases of the hiring lifecycle:

1.  **Career Portal (Next.js):** Fetches dynamic job listings from Supabase. Candidates submit standard forms + PDF resumes.
2.  **Resume Intake & AI Screening (FastAPI + Gemini):** A background task ingests the PDF in-memory. Gemini evaluates the resume against the JD, extracts a fit score, and generates a structured rationale. For top scorers, it simulates web research to generate a "Social Brief".
3.  **Calendar Orchestration (Google Calendar API):** Integrates natively via OAuth with Google Calendar to check Free/Busy status. It generates tentative holds in the database, and upon candidate confirmation, creates a live Google Calendar event.
4.  **Live Interview & Notetaker (Fireflies.ai - Mocked):** Simulates a post-meeting webhook from Fireflies. Gemini summarizes the raw transcript into 3 key bullet points for the hiring manager.
5.  **Offer Letter Generation (PandaDoc - Mocked):** Gemini takes structured compensation inputs and the candidate's background to draft a customized, Markdown-formatted offer letter. We simulate the PandaDoc e-signature webhook completion.
6.  **Slack Onboarding (Slack API - Mocked):** The signature webhook triggers a final LLM call to draft a highly personalized Slack welcome message (referencing the candidate's initial AI research brief), which is printed to the console simulating a `#general` channel broadcast.

---

## Top 5 Edge Cases Handled

1.  **Calendar Slot Conflict Prevention (Phase 3):** To prevent two candidates from booking the exact same time slot, I implemented a database-level transactional lock. When a candidate clicks a time, the system checks if the status in `interview_holds` is still exactly `'pending'`. If true, it confirms the slot and releases others; if false, the transaction fails and prompts the user to pick a new time.
2.  **Unpredictable LLM Formatting & List Outputs (Phase 2):** LLMs frequently wrap outputs in lists of dictionaries or inject unexpected Markdown (e.g., `**SCORE:** 90`). I implemented an `isinstance` check to unwrap list structures and utilized Regular Expressions (`re.search`) to bulletproof the extraction of the numerical score, regardless of surrounding text.
3.  **Silent Backend Crashes on PDF Uploads (Phase 1):** Directly passing a FastAPI `UploadFile` stream to `pdfplumber` can cause silent pointer crashes, resulting in dreaded `Failed to fetch` frontend errors. I mitigated this by reading the file into memory using `io.BytesIO` and wrapping the endpoint in a global `try/except` block to ensure HTTP 500 errors are properly bubbled up.
4.  **Dynamic Routing UUID Loss (Next.js):** During frontend form submissions on dynamic routes (`/apply/[jobId]`), Next.js can sometimes lose the context of the URL, sending `"undefined"` to the backend and crashing the PostgreSQL UUID syntax. I implemented a vanilla JavaScript fallback (`window.location.pathname.split('/')`) to guarantee the exact UUID is captured and passed.
5.  **OAuth Blocking in Background Tasks (Phase 3):** Since the calendar scheduling triggers automatically via a FastAPI `Background Task` for high-scoring candidates, a missing Google OAuth token would silently freeze the server waiting for a browser login prompt. The system is designed to gracefully catch this exception and log the failure without disrupting the candidate's frontend experience.

---

## Assumptions & Deliberate Trade-offs

1.  **Simulated Social Footprint Research (Phase 2C):**
    * *Trade-off:* I mocked the live web-scraping of LinkedIn, X, and GitHub.
    * *Why:* Live scraping requires paid enterprise APIs (like Proxycurl or Apify) to bypass anti-bot protections. To demonstrate the value of the intelligence layer quickly, I utilized an LLM prompt to "hallucinate" a highly realistic candidate brief based strictly on their resume context.
2.  **Mocked Enterprise Webhooks (Phases 4, 5 & 6):**
    * *Trade-off:* I simulated the incoming webhooks for Fireflies, PandaDoc, and Slack using direct POST endpoints rather than live integrations.
    * *Why:* Setting up multiple third-party developer accounts, OAuth scopes, and `ngrok` tunnels for a local prototype introduces massive friction and points of failure. Mocking the payloads proves the asynchronous system architecture and database state transitions work perfectly.
3.  **Tentative Calendar Holds via Database vs. Calendar UI:**
    * *Trade-off:* Rather than placing 3 actual "tentative" events directly onto the interviewer's Google Calendar (which severely clutters their daily view), I managed the pending holds strictly inside the Supabase database.
    * *Why:* The actual Google Calendar is only written to once the candidate makes their final selection. This keeps the hiring manager's calendar clean while still preventing double-booking via database locks.

---

## What I Would Improve Given More Time

* **Asynchronous Task Queue:** Move the AI screening and email dispatching from FastAPI's basic `BackgroundTasks` to a robust Celery + Redis worker queue to handle high-volume applicant spikes safely.
* **Live Web Scraping:** Integrate Apify or Proxycurl to fetch real-time JSON data from LinkedIn and GitHub to feed into the Candidate Research prompt.
* **Authentication & Security:** Add Supabase Auth to protect the Admin Dashboard routes, ensuring only authorized HR personnel can view PII and override AI screening decisions.

***

## Local Setup & Installation

Follow these steps to run the end-to-end pipeline on your local machine.

### Directory Structure
Ensure your project is organized as follows before starting:
```text
ai-operator-takehome/
│
├── backend/
│   ├── main.py                # FastAPI server & AI logic
│   ├── credentials.json       # Google Calendar OAuth credentials (Required for Phase 3)
│   ├── token.json             # Auto-generated after first Google login
│   └── .env                   # Backend environment variables
│
└── frontend/
    ├── package.json
    └── src/
        └── app/
            ├── page.tsx       # Job Board UI
            ├── apply/         # Dynamic application form
            └── success/       # Confirmation page
```

### Prerequisites
* **Python 3.9+**
* **Node.js 18+**
* **Supabase Account** (Free tier is sufficient)
* **Google Gemini API Key** (via Google AI Studio)

---

### Step 1: Backend Setup (FastAPI)

1. **Navigate to the backend directory and create a virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. **Install the required Python dependencies:**
   ```bash
   pip install fastapi uvicorn supabase langchain-google-genai langchain-core pdfplumber python-multipart python-dotenv requests google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

3. **Configure Environment Variables:**
   Create a `.env` file inside the `backend/` folder and paste your API keys:
   ```env
   # backend/.env
   SUPABASE_URL="your_supabase_project_url"
   SUPABASE_KEY="your_supabase_anon_key"
   GOOGLE_API_KEY="your_gemini_api_key"
   ```

4. **Add Google Calendar Credentials:**
   * Download your OAuth 2.0 Client ID JSON from the Google Cloud Console.
   * Rename the file to `credentials.json` and place it directly inside the `backend/` folder.

5. **Start the Backend Server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   *Note: The first time the calendar endpoint is triggered, a browser window will open asking you to authenticate with Google. This will generate a `token.json` file for future headless runs.*

---

### Step 2: Frontend Setup (Next.js)

1. **Open a new terminal tab and navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Start the Frontend Development Server:**
   ```bash
   npm run dev
   ```

4. **Launch the App:**
   Open your browser and navigate to `http://localhost:3000` to view the Job Board and interact with the AI pipeline.

## Walkthrough

<video src="https://raw.githubusercontent.com/s-maverick/e2e-ai-onboarding/main/Walkthrough/1.mp4" controls width="600" muted></video>
