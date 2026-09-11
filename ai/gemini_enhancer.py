import os
import json
import logging
from typing import Dict, Any, List
import google.generativeai as genai
from database.db import Database

logger = logging.getLogger(__name__)

class GeminiEnhancer:
    def __init__(self, db: Database, audit_id: str, api_key: str = None):
        """
        Initialize the GeminiEnhancer with database connection and audit ID.
        """
        self.db = db
        self.audit_id = audit_id
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            logger.warning("Gemini API key not found. AI enhancements disabled.")

    async def enhance(self):
        """
        Main method to run all enhancements if API key is present.
        """
        if not self.enabled:
            logger.info("Enhancement skipped. API key missing.")
            return

        logger.info("Starting AI enhancement...")
        await self.generate_executive_summary()
        await self.generate_fix_priorities()
        await self.analyze_content_quality()
        await self.classify_keyword_intent()
        logger.info("AI enhancement completed.")

    async def generate_executive_summary(self) -> str:
        """
        Generate an executive summary based on the audit data.
        """
        try:
            summary_data = await self.db.get_audit_summary(self.audit_id)
            issues = await self.db.get_issues(self.audit_id)
            pages = await self.db.get_pages(self.audit_id)
            
            prompt_data = {
                "summary": summary_data,
                "top_issues": [i for i in issues if i.get('severity') == 'critical'][:20],
                "total_pages_crawled": len(pages)
            }
            
            prompt = f"You are an SEO expert. Based on this audit data, write a concise executive summary (3-5 paragraphs) highlighting the most critical findings and priority actions. Data: {json.dumps(prompt_data)}"
            
            response = self.model.generate_content(prompt)
            summary_text = response.text
            
            audit = await self.db.get_audit(self.audit_id)
            if audit:
                config_json = audit.get('config_json', '{}')
                try:
                    config = json.loads(config_json) if config_json else {}
                except json.JSONDecodeError:
                    config = {}
                config['ai_executive_summary'] = summary_text
                await self.db.update_audit(self.audit_id, config_json=json.dumps(config))
                
            return summary_text
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return ""

    async def generate_fix_priorities(self) -> list:
        """
        Generate a ranked list of top 10 most impactful issues to fix.
        """
        try:
            issues = await self.db.get_issues(self.audit_id)
            critical_warning = [i for i in issues if i.get('severity') in ('critical', 'warning')]
            
            prompt = f"Based on these SEO issues, rank the top 10 most impactful issues to fix first, considering their effect on search rankings and user experience. For each, provide a brief explanation of why it's important and a specific action step. Issues data: {json.dumps(critical_warning[:50])}"
            
            response = self.model.generate_content(prompt)
            priorities_text = response.text
            
            audit = await self.db.get_audit(self.audit_id)
            if audit:
                config_json = audit.get('config_json', '{}')
                try:
                    config = json.loads(config_json) if config_json else {}
                except json.JSONDecodeError:
                    config = {}
                config['ai_fix_priorities'] = priorities_text
                await self.db.update_audit(self.audit_id, config_json=json.dumps(config))
                
            return [priorities_text]
        except Exception as e:
            logger.error(f"Error generating fix priorities: {e}")
            return []

    async def analyze_content_quality(self) -> dict:
        """
        Evaluate content quality and E-E-A-T signals for a sample of pages.
        """
        try:
            pages = await self.db.get_pages(self.audit_id)
            sample_pages = pages[:10]
            page_data = []
            for p in sample_pages:
                page_data.append({
                    "url": p.get("url"),
                    "title": p.get("title"),
                    "meta_description": p.get("meta_description"),
                    "h1": p.get("h1"),
                    "word_count": p.get("word_count")
                })
                
            prompt = f"Evaluate the content quality and E-E-A-T signals of these pages. Rate each page's content quality on a scale of 1-10 and provide specific improvement suggestions. Output format should clearly state URL, score, and suggestions. Data: {json.dumps(page_data)}"
            
            response = self.model.generate_content(prompt)
            quality_text = response.text
            
            audit = await self.db.get_audit(self.audit_id)
            if audit:
                config_json = audit.get('config_json', '{}')
                try:
                    config = json.loads(config_json) if config_json else {}
                except json.JSONDecodeError:
                    config = {}
                config['ai_content_quality'] = quality_text
                await self.db.update_audit(self.audit_id, config_json=json.dumps(config))
                
            return {"analysis": quality_text}
        except Exception as e:
            logger.error(f"Error analyzing content quality: {e}")
            return {}

    async def classify_keyword_intent(self) -> dict:
        """
        Classify top keywords by search intent.
        """
        try:
            keywords = await self.db.get_keywords(self.audit_id)
            top_keywords = list(set([k.get('keyword') for k in keywords]))[:30]
            
            if not top_keywords:
                return {}
                
            prompt = f"Classify these keywords by search intent: Informational, Navigational, Transactional, or Commercial. Format: keyword | intent | reasoning. Keywords: {json.dumps(top_keywords)}"
            
            response = self.model.generate_content(prompt)
            classification_text = response.text
            
            audit = await self.db.get_audit(self.audit_id)
            if audit:
                config_json = audit.get('config_json', '{}')
                try:
                    config = json.loads(config_json) if config_json else {}
                except json.JSONDecodeError:
                    config = {}
                config['ai_keyword_intent'] = classification_text
                await self.db.update_audit(self.audit_id, config_json=json.dumps(config))
                
            return {"classification": classification_text}
        except Exception as e:
            logger.error(f"Error classifying keyword intent: {e}")
            return {}
