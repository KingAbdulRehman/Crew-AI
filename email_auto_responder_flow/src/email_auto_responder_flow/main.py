#!/usr/bin/env python
from random import randint
from typing import List
from pydantic import BaseModel

from crewai.flow import Flow, listen, start

from email_auto_responder_flow.crews.email_filter_crew.crew import EmailFilterCrew

class Email(BaseModel):
    id: str
    threadId: str
    snippet: str
    sender: str

class AutoResponderState(BaseModel):
    emails: List[Email] = []
    checked_emails_ids: set[str] = set()


class EmailAutoResponseFlow(Flow[AutoResponderState]):

    @start()
    def start_check_new_emails(self):
        print("Generating poem")
        result = (
            EmailFilterCrew()
            .crew()
            .kickoff(inputs={"topic": "Upwork Job Porposal"})
        )

        print("FInal Result in COde after crew process : ", result)


    # @listen(start_check_new_emails)
    # def generate_poem(self):
    #     # run after generate_sentence_count and if emails available then draft it 
    #     print("start")


def kickoff():
    poem_flow = EmailAutoResponseFlow()
    poem_flow.kickoff()


def plot():
    poem_flow = EmailAutoResponseFlow()
    poem_flow.plot()


if __name__ == "__main__":
    kickoff()
