from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from core.models import Certification, ContactInfo, Education, Experience, Profile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "01_profile_v5.md"


def load_profile(path: Path | None = None) -> Profile:
    """Load Mihir's v5 profile authority into typed structures."""
    profile_path = path or PROFILE_PATH
    raw_markdown = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    profile = _default_profile()
    profile.raw_markdown = raw_markdown
    return profile


@lru_cache(maxsize=1)
def cached_profile() -> Profile:
    """Return the cached v5 profile."""
    return load_profile()


def _terms(*items: str) -> dict[str, str]:
    return {item.lower(): item for item in items}


def _default_profile() -> Profile:
    contact = ContactInfo(
        name="Mihir Trivedi",
        email="mihir1611t@gmail.com",
        phone="249-360-5901",
        linkedin="linkedin.com/in/mihirtrivedigm",
        website="mihirtrivedi.tech",
        location="Sudbury, Ontario, Canada",
        work_authorization="Canadian permanent resident",
        sponsorship="Legally eligible to work in Canada without sponsorship",
        relocation="Open to relocation for the right opportunity",
    )
    tier_a = _terms(
        "Python",
        "Java",
        "JavaScript",
        "SQL",
        "R",
        "OpenAI API",
        "Gemini API",
        "LLM integration",
        "prompt engineering",
        "document Q&A",
        "document-and-log Q&A",
        "retrieval",
        "retrieval-augmented generation",
        "RAG",
        "PostgreSQL",
        "dbt",
        "ETL",
        "ELT",
        "data warehouse",
        "data warehousing",
        "Tableau",
        "predictive inventory models",
        "Salesforce",
        "HubSpot",
        "ZoomInfo",
        "Lead Forensics",
        "Java Spring MVC",
        "Spring Boot",
        "Hibernate",
        "REST APIs",
        "microservices",
        "SAP Hybris",
        "SAP Commerce Cloud",
        "React Native",
        "Power Automate",
        "scikit-learn",
        "Random Forest",
        "classification models",
        "ML pipelines",
        "ArcGIS",
        "QGIS",
        "Azure",
        "Docker",
        "Git",
        "CI/CD",
        "GitHub Actions",
        "Linux",
        "Agile",
        "Scrum",
        "requirements gathering",
        "technical documentation",
        "stakeholder management",
        "medical-device logs",
        "regulated medical-device environment",
        "autonomous mining equipment",
        "geospatial survey datasets",
    )
    tier_b = _terms(
        "TypeScript",
        "Node.js",
        "MongoDB",
        "SQL Server",
        "data modeling",
        "data visualization",
        "business intelligence",
        "Power BI",
        "cloud platforms",
        "system integration",
    )
    tier_c = _terms("C#", ".NET", "FastAPI", "GraphQL")
    adjacency = {
        "aws": "Azure",
        "amazon web services": "Azure",
        "gcp": "Azure",
        "google cloud": "Azure",
        "snowflake": "PostgreSQL and dbt data warehouse",
        "looker": "Tableau and Power BI reporting",
        "looker studio": "Tableau and Power BI reporting",
        "rag": "document Q&A and retrieval-augmented generation patterns",
        "vector database": "document Q&A and retrieval patterns",
        "langchain": "LLM integration and prompt engineering",
        "kubernetes": "Docker and CI/CD",
        "airflow": "ETL and ELT pipelines",
        "spark": "ETL and ELT pipelines",
    }
    experiences = [
        Experience(
            company="Flosonics Medical",
            title="Business Intelligence Developer",
            location="Toronto, ON (Remote)",
            dates="Oct 2024 to Apr 2026",
            bullets=[
                "Wrote an internal AI assistant on the OpenAI and Gemini APIs so non-technical staff could query device logs, sales operations, and HR documents in plain language.",
                "Built the company's first centralized data warehouse in PostgreSQL and dbt, giving Finance, QA, Production, and HR one governed source of truth.",
                "Designed ETL and ELT pipelines joining medical-device logs with Salesforce, HubSpot, ZoomInfo, and Lead Forensics data into a single analytics layer feeding the AI assistant.",
                "Automated Tableau reporting and built predictive inventory models, cutting manual reporting overhead by 40% in a regulated medical-device environment.",
            ],
        ),
        Experience(
            company="Tata Consultancy Services (TCS)",
            title="Lead Software Engineer",
            location="Mumbai, India",
            dates="Nov 2017 to Oct 2021",
            bullets=[
                "Led four engineers on Edgepark, a high-traffic B2C commerce platform, owning requirements, solution design, and backlog.",
                "Built secure user management and order business logic in Java Spring MVC and Hibernate behind REST APIs and microservices.",
                "Launched 13 B2B commerce platforms across Europe and North America on SAP Hybris and SAP Commerce Cloud, handling multi-language and multi-currency builds.",
                "Owned production support for critical services and tightened the CI/CD pipeline and application performance release over release.",
            ],
        ),
        Experience(
            company="LoopX",
            title="Software Development Consultant",
            location="Sudbury, ON",
            dates="Jun 2024 to Jul 2025",
            bullets=[
                "Designed, built, and shipped the LoopX Safe and Smart Mining Data Platform solo, backend through frontend.",
                "Built real-time safety dashboards and automated reporting for autonomous mining equipment operating underground.",
            ],
        ),
        Experience(
            company="Mineral Exploration Research Centre",
            title="Research Associate (Data & ML)",
            location="Sudbury, ON",
            dates="Mar 2022 to Jul 2023",
            bullets=[
                "Developed Random Forest models for gold prospectivity mapping, reaching a 99.5% F1 score on geological classification.",
                "Processed large geospatial survey datasets in Python, ArcGIS, and QGIS to map mineralization probability across the Superior province.",
            ],
        ),
        Experience(
            company="Minax Inc.",
            title="Lead Software Developer",
            location="Sudbury, ON",
            dates="Oct 2023 to May 2024",
            bullets=[
                "Built an offline-first React Native app for Vale that collects inspection data underground with no network and syncs when connectivity returns.",
                "Automated Workplace Safety North compliance forms with Power Automate, taking engineer reporting from 5 hours to minutes.",
            ],
        ),
    ]
    education = [
        Education(
            institution="Laurentian University",
            location="Sudbury, ON",
            degree="Master of Computational Science",
            dates="2021 to 2023",
            bullets=[
                "Thesis: ML for Geological Discovery.",
                "Oral presentation at AICMSE 2023, Harvard Faculty Club, Boston.",
                "Co-author of a peer-reviewed Ore Geology Reviews paper on Random Forest fault analysis in the Superior province.",
            ],
        ),
        Education(
            institution="Gujarat Technological University",
            location="India",
            degree="Bachelor of Computer Engineering",
            dates="2013 to 2017",
        ),
    ]
    certifications = [
        Certification(
            name="Salesforce Certified Agentforce Specialist (AI-201)",
            date="2025",
            link="https://www.salesforce.com/trailblazer/ewzrm5h6s9f1si06c5",
        ),
        Certification(
            name="Microsoft Certified: Power BI Data Analyst Associate (PL-300)",
            date="2024",
            link="https://learn.microsoft.com/en-us/users/MihirTrivedi-0383/credentials/982D4E48445B5F5D",
        ),
        Certification(
            name="Microsoft Certified: Power Platform Developer Associate (PL-400)",
            date="2024",
            link="https://learn.microsoft.com/api/credentials/share/en-us/MihirTrivedi-0383/E94F1B4F03BC2E34",
        ),
        Certification(
            name="Microsoft Certified: Azure Fundamentals (AZ-900)",
            date="2024",
            link="https://learn.microsoft.com/en-us/users/mihirtrivedi-0383/credentials/c669a77f8f67fb6d",
        ),
    ]
    return Profile(
        contact=contact,
        retired_emails=["mtrivedi@laurentian.ca"],
        role_identities=[
            "AI Engineer",
            "Generative AI Engineer",
            "Business Intelligence Developer",
            "Data Engineer",
            "Data Analyst",
            "Software Engineer",
            "Lead Software Engineer",
            "ML Engineer",
            "Application Developer",
        ],
        tier_a=tier_a,
        tier_b=tier_b,
        tier_c=tier_c,
        adjacency=adjacency,
        experiences=experiences,
        education=education,
        certifications=certifications,
        supported_metrics=[
            "8+ years",
            "four engineers",
            "13 B2B commerce platforms",
            "40%",
            "99.5% F1 score",
            "5 hours to minutes",
        ],
    )
