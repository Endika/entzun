from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from typing import Optional

from app.core.config import settings


class ReportGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name="gpt-3.5-turbo")
        self.memory = ConversationBufferMemory()
        self.chain = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            verbose=False
        )
        self.total_chars = 0
    
    async def generate_report(
        self, 
        transcript: str,
        report_type: Optional[str] = "standard"
    ) -> str:
        prompt = self._get_prompt_for_report_type(transcript, report_type)
        
        report = self.chain.predict(input=prompt)
        
        self.total_chars += len(transcript) + len(prompt) + len(report)
        
        if self.total_chars > settings.SUMMARIZE_AFTER:
            await self.summarize_history()
        
        return report
    
    def _get_prompt_for_report_type(self, transcript: str, report_type: str) -> str:
        if report_type == "executive":
            return (
                f"Please analyze the following transcript and provide an executive summary "
                f"focused on high-level insights, strategic implications, and key decisions:\n\n{transcript}"
            )
        elif report_type == "detailed":
            return (
                f"Please analyze the following transcript and provide a detailed report "
                f"with comprehensive analysis, specific points, context, and exhaustive action items:\n\n{transcript}"
            )
        elif report_type == "action":
            return (
                f"Please analyze the following transcript and provide a concise list of action items "
                f"and tasks derived from the discussion, with owners and deadlines where mentioned:\n\n{transcript}"
            )
        else:
            return (
                f"Please analyze the following transcript and provide a concise report "
                f"highlighting key points and action items:\n\n{transcript}"
            )
    
    async def summarize_history(self) -> None:
        if not self.memory.chat_memory.messages:
            return
            
        prompt = (
            "Summarize our conversation so far, keeping all essential information "
            "but making it more concise. Focus on key points, decisions, and action items."
        )
        
        summary = self.llm.predict(prompt)
        
        self.memory.clear()
        
        self.memory.chat_memory.add_user_message(
            "Here's a summary of our conversation so far:"
        )
        self.memory.chat_memory.add_ai_message(summary)
        
        self.total_chars = len(summary)


report_generator = ReportGenerator() 