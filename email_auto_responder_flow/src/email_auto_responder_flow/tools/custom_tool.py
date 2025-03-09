from typing import Type
import os
import pickle
import base64
import ssl
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import urllib3

# Disable SSL verification warning for telemetry only
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['CREWAI_DISABLE_TELEMETRY'] = 'true'  # Alternative solution: completely disable telemetry

class GmailFetcherInput(BaseModel):
    """Input schema for GmailFetcherTool."""
    max_results: int = Field(
        default=10, 
        description="Maximum number of emails to fetch. Example: 5 will fetch 5 most recent emails"
    )
    time_duration: int = Field(
        default=24, 
        description="Time duration in hours to fetch emails from. Example: 48 will fetch emails from last 48 hours"
    )
    last_mail_id: str = Field(
        default="", 
        description="ID of the last email fetched. Used for pagination and preventing duplicate fetches"
    )

class GmailDrafterInput(BaseModel):
    """Input schema for GmailDrafterTool."""
    to: str = Field(
        ..., 
        description="Email recipient address. Example: 'recipient@example.com'"
    )
    subject: str = Field(
        ..., 
        description="Email subject line. Example: 'Meeting Schedule for Tomorrow'"
    )
    body: str = Field(
        ..., 
        description="Email body content. Example: 'Dear Team,\n\nI hope this email finds you well...'"
    )

class BaseGmailTool:
    """Base class for Gmail tools with common functionality"""
    _creds = None  # Class variable to store credentials
    _default_scopes = ['https://mail.google.com/']  # Full access scope by default

    def get_gmail_service(self, scopes=None):
        if scopes is None:
            scopes = self._default_scopes

        if self._creds and self._creds.valid:
            # Check if we have all required scopes
            if all(scope in self._creds.scopes for scope in scopes):
                return build('gmail', 'v1', credentials=self._creds)
            else:
                # If we don't have all required scopes, reset credentials
                self._creds = None
                if os.path.exists('token.pickle'):
                    os.remove('token.pickle')

        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self._creds = pickle.load(token)
                
            # Only remove if invalid
            if not self._creds or not self._creds.valid:
                os.remove('token.pickle')
                self._creds = None

        if self._creds and self._creds.expired and self._creds.refresh_token:
            try:
                self._creds.refresh(Request())
            except Exception:
                self._creds = None
                if os.path.exists('token.pickle'):
                    os.remove('token.pickle')

        if not self._creds:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json is missing. Please download it from Google Cloud Console"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            self._creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(self._creds, token)

        return build('gmail', 'v1', credentials=self._creds)

class GmailFetcherTool(BaseTool, BaseGmailTool):
    name: str = "Gmail Fetcher"
    description: str = "Fetches recent emails from Gmail inbox within specified time duration"
    args_schema: Type[BaseModel] = GmailFetcherInput

    def _run(self, max_results: int = 10, time_duration: int = 24, last_mail_id: str = "") -> str:
        service = self.get_gmail_service()
        
        # Calculate time threshold
        time_threshold = datetime.now() - timedelta(hours=time_duration)
        query = f'after:{int(time_threshold.timestamp())}'
        
        # Add last_mail_id to query if provided
        if last_mail_id and os.getenv('LAST_MAIL_ID'):
            query += f' AND id > {os.getenv("LAST_MAIL_ID")}'
        
        results = service.users().messages().list(userId='me', maxResults=max_results, q=query).execute()
        messages = results.get('messages', [])
        
        emails = []
        if messages:
            # Save the most recent mail ID to environment
            most_recent_id = messages[0]['id']
            os.environ['LAST_MAIL_ID'] = most_recent_id
            
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                subject = next((header['value'] for header in msg['payload']['headers'] 
                              if header['name'] == 'Subject'), 'No Subject')
                sender = next((header['value'] for header in msg['payload']['headers'] 
                             if header['name'] == 'From'), 'Unknown')
                emails.append(f"From: {sender}\nSubject: {subject}\n---")
        
        return "\n".join(emails) if emails else f"No emails found in the last {time_duration} hours"

class GmailDrafterTool(BaseTool, BaseGmailTool):
    name: str = "Gmail Draft Creator"
    description: str = "Creates a draft email in Gmail"
    args_schema: Type[BaseModel] = GmailDrafterInput

    def _run(self, to: str, subject: str, body: str) -> str:
        service = self.get_gmail_service()
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        draft = {'message': {'raw': raw}}
        
        try:
            draft = service.users().drafts().create(userId='me', body=draft).execute()
            return f"Draft created successfully. Draft ID: {draft['id']}"
        except Exception as e:
            return f"An error occurred: {str(e)}"
