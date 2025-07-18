#!/usr/bin/env python3
"""
Dummy Data Generator for Call Center Database

This script creates sample data for testing the call center management system.
Run this script to populate your database with realistic dummy data.

Usage: python generate_dummy_data.py
"""

import random
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import (
    Base, Manager, Auditor, Counsellor, Call, CallAnalysis, 
    AuditReport, Lead, generate_uuid
)

# Database configuration
DATABASE_URL = "postgresql://neondb_owner:npg_Kx6nuVIiYAp3@ep-little-field-a52px0eo-pooler.us-east-2.aws.neon.tech/qc?sslmode=require&channel_binding=require" # Change this to match your database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_dummy_data():
    """Create dummy data for the call center database"""
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Clear existing data (optional - comment out if you want to keep existing data)
        print("Clearing existing data...")
        db.query(Lead).delete()
        db.query(AuditReport).delete()
        db.query(CallAnalysis).delete()
        db.query(Call).delete()
        db.query(Counsellor).delete()
        db.query(Auditor).delete()
        db.query(Manager).delete()
        db.commit()
        
        print("Creating dummy data...")
        
        # 1. Create 2 Managers
        managers = []
        manager_data = [
            {"name": "John Smith", "email": "john.smith@company.com", "phone": "+1-555-0101"},
            {"name": "Sarah Johnson", "email": "sarah.johnson@company.com", "phone": "+1-555-0102"}
        ]
        
        for data in manager_data:
            manager = Manager(
                name=data["name"],
                email=data["email"],
                phone=data["phone"],
                password="manager123"
            )
            db.add(manager)
            managers.append(manager)
        
        db.commit()
        print(f"Created {len(managers)} managers")
        
        # 2. Create 4 Auditors (2 per manager)
        auditors = []
        auditor_data = [
            {"name": "Mike Wilson", "email": "mike.wilson@company.com", "phone": "+1-555-0201"},
            {"name": "Lisa Chen", "email": "lisa.chen@company.com", "phone": "+1-555-0202"},
            {"name": "David Brown", "email": "david.brown@company.com", "phone": "+1-555-0203"},
            {"name": "Emma Davis", "email": "emma.davis@company.com", "phone": "+1-555-0204"}
        ]
        
        for i, data in enumerate(auditor_data):
            auditor = Auditor(
                manager_id=managers[i % 2].id,  # Distribute between managers
                name=data["name"],
                email=data["email"],
                phone=data["phone"],
                password="auditor123"
            )
            db.add(auditor)
            auditors.append(auditor)
        
        db.commit()
        print(f"Created {len(auditors)} auditors")
        
        # 3. Create 10 Counsellors (distribute among auditors)
        counsellors = []
        counsellor_names = [
            "Alice Cooper", "Bob Martinez", "Carol White", "Daniel Garcia",
            "Eva Rodriguez", "Frank Taylor", "Grace Anderson", "Henry Thomas",
            "Ivy Jackson", "Jack Robinson"
        ]
        
        for i, name in enumerate(counsellor_names):
            auditor = auditors[i % 4]  # Distribute among auditors
            counsellor = Counsellor(
                auditor_id=auditor.id,
                manager_id=auditor.manager_id,
                name=name,
                email=f"{name.lower().replace(' ', '.')}@company.com",
                phone=f"+1-555-{3000 + i:04d}"
            )
            db.add(counsellor)
            counsellors.append(counsellor)
        
        db.commit()
        print(f"Created {len(counsellors)} counsellors")
        
        # 4. Create 30 Calls with Analysis
        calls = []
        call_types = ["Inbound", "Outbound", "Follow-up", "Support"]
        client_numbers = [f"+1-555-{random.randint(1000, 9999):04d}" for _ in range(30)]
        
        # Sample transcripts and summaries
        sample_transcripts = [
            "Hello, thank you for calling. How can I help you today?",
            "I understand your concern. Let me look into this for you.",
            "I can see that you're interested in our premium package.",
            "Let me transfer you to our specialist team.",
            "Thank you for your patience. I have the information you need."
        ]
        
        sample_summaries = [
            "Customer inquiry about product features",
            "Support request for technical issue",
            "Sales call for premium service",
            "Follow-up on previous conversation",
            "General information request"
        ]
        
        keywords_list = [
            "product,inquiry,features",
            "support,technical,issue",
            "sales,premium,upgrade",
            "followup,callback,scheduled",
            "information,general,help"
        ]
        
        for i in range(30):
            counsellor = random.choice(counsellors)
            call_start = datetime.now() - timedelta(days=random.randint(0, 30))
            call_duration = random.randint(120, 1800)  # 2 minutes to 30 minutes
            
            call = Call(
                counsellor_id=counsellor.id,
                auditor_id=counsellor.auditor_id,
                manager_id=counsellor.manager_id,
                call_start=call_start,
                call_end=call_start + timedelta(seconds=call_duration),
                duration=call_duration,
                call_type=random.choice(call_types),
                client_number=client_numbers[i],
                recording_url=f"https://recordings.company.com/call_{i+1}.mp3",
                is_audited=random.choice([True, False]),
                is_flagged=random.choice([True, False]) if random.random() < 0.2 else False,
                audit_score=round(random.uniform(6.0, 10.0), 1),
                tags=random.choice(keywords_list)
            )
            db.add(call)
            calls.append(call)
        
        db.commit()
        print(f"Created {len(calls)} calls")
        
        # 5. Create Call Analysis for each call
        call_analyses = []
        for call in calls:
            analysis = CallAnalysis(
                call_id=call.id,
                sentiment_score=round(random.uniform(-1.0, 1.0), 2),
                transcript=random.choice(sample_transcripts),
                summary=random.choice(sample_summaries),
                anomalies="None detected" if random.random() > 0.3 else "Long silence detected",
                keywords=call.tags,
                ai_confidence=round(random.uniform(0.7, 0.98), 2)
            )
            db.add(analysis)
            call_analyses.append(analysis)
        
        db.commit()
        print(f"Created {len(call_analyses)} call analyses")
        
        # 6. Create Audit Reports for audited calls
        audit_reports = []
        audited_calls = [call for call in calls if call.is_audited]
        
        for call in audited_calls:
            report = AuditReport(
                call_id=call.id,
                auditor_id=call.auditor_id,
                manager_id=call.manager_id,
                score=round(random.uniform(6.0, 10.0), 1),
                comments=random.choice([
                    "Excellent customer service",
                    "Good call handling",
                    "Could improve on response time",
                    "Professional approach",
                    "Needs follow-up"
                ]),
                is_flagged=call.is_flagged,
                flag_reason="Compliance issue" if call.is_flagged else None
            )
            db.add(report)
            audit_reports.append(report)
        
        db.commit()
        print(f"Created {len(audit_reports)} audit reports")
        
        # 7. Create some Leads
        leads = []
        lead_statuses = ["New", "Contacted", "Qualified", "Proposal", "Closed Won", "Closed Lost"]
        
        for i in range(15):  # Create 15 leads
            counsellor = random.choice(counsellors)
            lead = Lead(
                counsellor_id=counsellor.id,
                auditor_id=counsellor.auditor_id,
                manager_id=counsellor.manager_id,
                client_name=f"Client {i+1}",
                client_number=f"+1-555-{random.randint(5000, 9999):04d}",
                status=random.choice(lead_statuses),
                note=f"Lead generated from call on {datetime.now().strftime('%Y-%m-%d')}"
            )
            db.add(lead)
            leads.append(lead)
        
        db.commit()
        print(f"Created {len(leads)} leads")
        
        print("\n=== DUMMY DATA CREATION COMPLETE ===")
        print(f"Managers: {len(managers)}")
        print(f"Auditors: {len(auditors)}")
        print(f"Counsellors: {len(counsellors)}")
        print(f"Calls: {len(calls)}")
        print(f"Call Analyses: {len(call_analyses)}")
        print(f"Audit Reports: {len(audit_reports)}")
        print(f"Leads: {len(leads)}")
        
        # Display sample login credentials
        print("\n=== SAMPLE LOGIN CREDENTIALS ===")
        print("Managers:")
        for manager in managers:
            print(f"  Email: {manager.email}, Password: manager123")
        
        print("\nAuditors:")
        for auditor in auditors:
            print(f"  Email: {auditor.email}, Password: auditor123")
        
        print("\nCounsellors:")
        for counsellor in counsellors[:3]:  # Show first 3 only
            print(f"  Email: {counsellor.email}, Password: (no password field)")
        print("  ... and 7 more counsellors")
        
    except Exception as e:
        print(f"Error creating dummy data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting dummy data generation...")
    create_dummy_data()
    print("Dummy data generation completed successfully!")