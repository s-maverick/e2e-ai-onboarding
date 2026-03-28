import os
import io
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import pdfplumber
from dotenv import load_dotenv
import os.path
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

app = FastAPI(title="AI Recruitment Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
# llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.2)
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=0.2,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

@app.get("/api/jobs")
async def get_jobs():
    try:
        res = supabase.table("jobs").select("*").execute()
        return {"jobs": res.data}
    except Exception as e:
        print(f"Error fetching jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not fetch jobs")

# --- PHASE 1 & 2: Application Intake & AI Screening ---
@app.post("/api/apply")
async def submit_application(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    email: str = Form(...),
    job_id: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        pdf_bytes = await file.read()
        pdf_text = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    pdf_text += extracted + "\n"
                
        cand_res = supabase.table("candidates").insert({
            "name": name,
            "email": email,
            "job_id": job_id,
            "status": "Applied"
        }).execute()
        
        if not cand_res.data:
            raise HTTPException(status_code=500, detail="Failed to save to database")
            
        candidate_id = cand_res.data[0]['id']
        
        background_tasks.add_task(screen_candidate, candidate_id, pdf_text, job_id)
        
        return {"status": "Application received", "candidate_id": candidate_id}
        
    except Exception as e:
        print(f"Error in submit_application: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def screen_candidate(candidate_id: str, resume_text: str, job_id: str):
    job_res = supabase.table("jobs").select("description").eq("id", job_id).execute()
    jd = job_res.data[0]["description"]
    
    # --- 1. Base AI Resume Screening ---
    prompt = PromptTemplate.from_template("""
    Evaluate this resume against the job description.
    JD: {jd}
    Resume: {resume}
    Provide a score out of 100 and a 2-sentence rationale.
    Format exactly like this: 
    SCORE: [number] 
    RATIONALE: [text]
    """)
    
    raw_response = llm.invoke(prompt.format(jd=jd, resume=resume_text))
    response = raw_response.content
    
    if isinstance(response, list):
        try:
            response = response[0].get("text", str(response))
        except:
            response = str(response)
    
    try:
        match = re.search(r'SCORE[^\d]*(\d+)', response, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            score = min(score, 100)
        else:
            score = 50 
    except Exception as e:
        print(f"Parsing crash: {e}")
        score = 50 
    status = "Shortlisted" if score >= 75 else "Screened"
    
    # --- 2. PHASE 2C: Social Footprint Research (For Top Candidates) ---
    social_brief = None
    if score >= 85:
        print(f"Candidate {candidate_id} scored {score}. Generating Social Brief...")
        research_prompt = PromptTemplate.from_template("""
        You are an AI recruiting assistant conducting web research on a candidate.
        Based on the following resume, simulate a web research process as if you searched their LinkedIn, Twitter (X), and GitHub.
        
        Generate a 3-5 sentence candidate brief for the hiring manager that includes:
        1. A cross-reference of their stated experience matching their simulated LinkedIn.
        2. A simulated notable GitHub contribution or portfolio project.
        3. A note on relevant professional interests or tech opinions they might share on X.
        4. A statement confirming no major discrepancies were found between the resume and online profiles.
        
        Keep it strictly under 60 seconds of reading time (3-5 sentences).
        
        Resume: {resume}
        """)
        
        raw_brief = llm.invoke(research_prompt.format(resume=resume_text))
        social_brief = raw_brief.content
        
        if isinstance(social_brief, list):
            try:
                social_brief = social_brief[0].get("text", str(social_brief))
            except:
                social_brief = str(social_brief)
                
        social_brief = social_brief.strip()
    
    supabase.table("candidates").update({
        "ai_score": score,
        "ai_summary": response.strip(),
        "social_brief": social_brief, # This will be NULL if score <= 85, or text if > 85
        "status": status
    }).eq("id", candidate_id).execute()








# # --- PHASE 3: Calendar Orchestration ---


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Shows basic usage of the Google Calendar API."""
    print("def start")
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            # This will pop open a browser window for you to log in!
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    print("def ends")
    return build('calendar', 'v3', credentials=creds)



@app.post("/api/schedule/generate-holds/{candidate_id}")
async def generate_calendar_holds(candidate_id: str):
    """
    Connects to Google Calendar API, checks Free/Busy, and creates holds in DB.
    """
    service = get_calendar_service()
    
    # 1. Check Free/Busy for tomorrow (Simplified logic for the prototype)
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'
    
    body = {
        "timeMin": now,
        "timeMax": tomorrow,
        "timeZone": 'UTC',
        "items": [{"id": 'primary'}]
    }
    print("cal start")
    eventsResult = service.freebusy().query(body=body).execute()
    calendars = eventsResult.get('calendars', {})
    primary_busy = calendars.get('primary', {}).get('busy', [])
    
    # [ALGORITHM PLACEHOLDER]: Here you would compare `primary_busy` against your working hours 
    # to find open 45-minute gaps. To keep this prototype fast, we will propose fixed times 
    # for tomorrow and assume they are free if you don't have events there.
    
    base_time = datetime.now() + timedelta(days=1)
    slots = [
        {"start": base_time.replace(hour=10, minute=0), "end": base_time.replace(hour=10, minute=45)},
        {"start": base_time.replace(hour=13, minute=0), "end": base_time.replace(hour=13, minute=45)}
    ]
    
    holds_created = []
    for slot in slots:
        res = supabase.table("interview_holds").insert({
            "candidate_id": candidate_id,
            "start_time": slot["start"].isoformat(),
            "end_time": slot["end"].isoformat(),
            "status": "pending"
        }).execute()
        holds_created.append(res.data[0])
        
    return {"status": "Holds created", "holds": holds_created}


@app.post("/api/schedule/confirm/{hold_id}")
async def confirm_calendar_slot(hold_id: str):
    """
    Handles Candidate Response, Prevent Conflicts, and INSERTS real Google Event.
    """
    hold_res = supabase.table("interview_holds").select("*").eq("id", hold_id).execute()
    if not hold_res.data:
        raise HTTPException(status_code=404, detail="Slot not found")
        
    hold = hold_res.data[0]
    
    if hold["status"] != "pending":
        raise HTTPException(status_code=409, detail="Slot no longer available.")
    
    # 1. Update DB Locks
    supabase.table("interview_holds").update({"status": "confirmed"}).eq("id", hold_id).execute()
    supabase.table("interview_holds").update({"status": "released"})\
        .eq("candidate_id", hold["candidate_id"]).eq("status", "pending").execute()
    
    supabase.table("candidates").update({"status": "Interview_Scheduled"}).eq("id", hold["candidate_id"]).execute()
    
    # 2. CREATE THE REAL GOOGLE CALENDAR EVENT
    cand_res = supabase.table("candidates").select("*").eq("id", hold["candidate_id"]).execute()
    candidate = cand_res.data[0]
    
    service = get_calendar_service()
    event = {
      'summary': f'Interview: {candidate["name"]} (AI Product Operator)',
      'description': 'Automated interview scheduled via AI Onboarding Portal.',
      'start': {
        'dateTime': hold["start_time"],
        'timeZone': 'America/New_York', # Update to your timezone
      },
      'end': {
        'dateTime': hold["end_time"],
        'timeZone': 'America/New_York',
      },
      'attendees': [
        {'email': candidate["email"]},
      ],
      'reminders': {
        'useDefault': True,
      },
    }

    event = service.events().insert(calendarId='primary', sendUpdates='all', body=event).execute()
    print("cal ends")
    return {"status": "Confirmed!", "event_link": event.get('htmlLink')}



class FirefliesMockPayload(BaseModel):
    candidate_id: str
    transcript: str

@app.post("/api/webhooks/fireflies")
async def fireflies_webhook_receiver(payload: FirefliesMockPayload):
    """
    Simulates receiving a webhook from Fireflies.ai after the interview ends.
    """
    prompt = PromptTemplate.from_template("""
    Summarize the following interview transcript into a concise 3-bullet point summary highlighting the candidate's technical communication and cultural fit.
    Transcript: {transcript}
    """)
    
    summary_response = llm.invoke(prompt.format(transcript=payload.transcript)).content
    
    if isinstance(summary_response, list):
        summary_response = summary_response[0].get("text", str(summary_response))
    
    supabase.table("candidates").update({
        "status": "Interview_Completed",
        "ai_summary": summary_response # Overwriting the initial screen summary with the interview summary
    }).eq("id", payload.candidate_id).execute()
    
    return {"status": "Interview transcript processed and profile updated"}


class OfferDetails(BaseModel):
    candidate_id: str
    job_title: str
    start_date: str
    salary: str
    equity: str
    manager: str
    custom_terms: str

@app.post("/api/offer/generate")
async def generate_offer_letter(details: OfferDetails):
    cand_res = supabase.table("candidates").select("*").eq("id", details.candidate_id).execute()
    candidate = cand_res.data[0]
    
    prompt = PromptTemplate.from_template("""
    Draft a highly professional employment offer letter for {candidate_name}.
    Role: {job_title}
    Base Salary: {salary}
    Equity/Bonus: {equity}
    Start Date: {start_date}
    Reporting Manager: {manager}
    Custom Terms: {custom_terms}
    
    Output the letter in clean Markdown format, ready for the hiring manager to review.
    """)
    
    offer_letter_md = llm.invoke(prompt.format(
        candidate_name=candidate["name"],
        job_title=details.job_title,
        salary=details.salary,
        equity=details.equity,
        start_date=details.start_date,
        manager=details.manager,
        custom_terms=details.custom_terms
    )).content
    
    if isinstance(offer_letter_md, list):
        offer_letter_md = offer_letter_md[0].get("text", str(offer_letter_md))
        
    supabase.table("candidates").update({"status": "Offer_Generated"}).eq("id", details.candidate_id).execute()
    
    return {"offer_text": offer_letter_md, "status": "Ready for Review & Signature"}



# MOCK Slack Client Initialization (Add near top of file)
# slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

@app.post("/api/webhooks/pandadoc-signed/{candidate_id}")
async def offer_signed_webhook(candidate_id: str):
    """
    Triggered by PandaDoc when the candidate signs. Kicks off Slack Onboarding.
    """
    supabase.table("candidates").update({"status": "Onboarded"}).eq("id", candidate_id).execute()
    
    cand_res = supabase.table("candidates").select("*").eq("id", candidate_id).execute()
    candidate = cand_res.data[0]
    
    prompt = PromptTemplate.from_template("""
    Write an enthusiastic, highly personalized Slack welcome message for our new hire, {name}.
    They are joining as an AI Product Operator. 
    Use their AI research brief to mention a specific skill or interest they have to make them feel special.
    Brief: {social_brief}
    
    Include placeholder links for onboarding resources. Keep it fun and use emojis.
    """)
    
    welcome_msg = llm.invoke(prompt.format(
        name=candidate["name"], 
        social_brief=candidate.get("social_brief", "They are a great engineer.")
    )).content
    
    if isinstance(welcome_msg, list):
        welcome_msg = welcome_msg[0].get("text", str(welcome_msg))
    
    try:
        print(f"--- MOCK SLACK NOTIFICATION TO #general ---\n{welcome_msg}")
        print(f"--- MOCK SLACK NOTIFICATION TO #hr-internal ---\n{candidate['name']} has officially signed and joined the Slack workspace!")
        
        # slack_client.chat_postMessage(channel="#general", text=welcome_msg)
        # slack_client.admin_users_invite(team_id="T12345", email=candidate["email"], ...)
    except Exception as e:
        print(f"Slack API Mock Error: {e}")
        
    return {"status": "Candidate Onboarded and Slack Triggers Sent"}