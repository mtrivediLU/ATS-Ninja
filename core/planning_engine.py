from __future__ import annotations

from core.evidence_engine import build_evidence_matrix, interview_probability
from core.models import (
    AnswerPlan,
    ContactInfo,
    CoverLetterPlan,
    Education,
    EvidenceItem,
    Experience,
    JDProfile,
    Profile,
    ResumePlan,
)


def build_resume_plan(
    *,
    contacts: ContactInfo,
    jd_profile: JDProfile,
    profile: Profile,
) -> ResumePlan:
    """Create a silent v5 resume plan before any output is rendered."""
    evidence = build_evidence_matrix(jd_profile, profile)
    role_identity = choose_role_identity(jd_profile, profile)
    top_keywords = _top_keywords(evidence)
    summary = _build_summary(role_identity, top_keywords, jd_profile, profile)
    working_knowledge = [
        item.real_evidence for item in evidence if item.evidence_tier == "C" and item.real_evidence
    ]
    skill_groups = _build_skill_groups(evidence, profile, working_knowledge)
    experience = _select_experience(profile, evidence)
    residual_gap = _first_gap(evidence)
    probability = interview_probability(evidence)
    analysis = _analysis_lines(evidence, residual_gap, jd_profile)
    headline = _headline(jd_profile, role_identity)
    work_mode_line = _work_mode_line(jd_profile)

    return ResumePlan(
        contacts=contacts,
        jd_profile=jd_profile,
        evidence=evidence,
        role_identity=role_identity,
        headline=headline,
        work_mode_line=work_mode_line,
        summary=summary,
        skill_groups=skill_groups,
        experience=experience,
        education=profile.education,
        certifications=profile.certifications,
        working_knowledge=working_knowledge,
        residual_gap=residual_gap,
        interview_probability=probability,
        analysis=analysis,
    )


def build_cover_letter_plan(resume_plan: ResumePlan, profile: Profile) -> CoverLetterPlan:
    """Create a cover-letter plan with mandatory logistics and fast-ramp logic."""
    jd = resume_plan.jd_profile
    company = jd.company or "your team"
    title = jd.title or resume_plan.role_identity
    domain_hook = jd.domain or "data and AI systems"
    proof_points = _cover_proof_points(resume_plan)
    fast_ramp_items = [
        item.keyword
        for item in resume_plan.evidence
        if item.evidence_tier in {"C", "adjacency", "missing"} and item.required_or_preferred == "required"
    ]
    needs_fast_ramp = bool(fast_ramp_items)
    angle = f"{resume_plan.role_identity} fit for {title} at {company}"
    body = _build_cover_letter_body(
        title=title,
        company=company,
        domain_hook=domain_hook,
        proof_points=proof_points,
        plan=resume_plan,
        needs_fast_ramp=needs_fast_ramp,
        fast_ramp_items=fast_ramp_items,
    )
    word_count = _body_word_count(body)
    return CoverLetterPlan(
        contacts=resume_plan.contacts,
        jd_profile=jd,
        angle=angle,
        body_paragraphs=body,
        word_count=word_count,
        needs_fast_ramp=needs_fast_ramp,
    )


def build_answer_plan(
    *,
    questions: list[str],
    resume_plan: ResumePlan,
) -> AnswerPlan:
    """Create paste-ready answers for application and screening questions."""
    answers: list[str] = []
    placeholders: list[str] = []
    for question in questions:
        lowered = question.lower()
        if "salary" in lowered or "compensation" in lowered:
            answers.append(
                "My target range is [YOUR RANGE], depending on total compensation, role scope, and work mode."
            )
            placeholders.append("[YOUR RANGE]")
        elif "start" in lowered or "available" in lowered:
            answers.append(
                "I can start on [YOUR START DATE]. I am based in Sudbury, Ontario and can align with the role's work mode."
            )
            placeholders.append("[YOUR START DATE]")
        elif "sponsor" in lowered or "legally" in lowered or "work in canada" in lowered:
            answers.append(
                "I am a Canadian permanent resident and legally eligible to work in Canada without sponsorship."
            )
        elif "relocat" in lowered or "remote" in lowered or "hybrid" in lowered:
            answers.append(
                "I am based in Sudbury, Ontario, open to the role's work mode, and open to relocation for the right opportunity."
            )
        else:
            answers.append(_long_answer(question, resume_plan))
    return AnswerPlan(questions=questions, answers=answers, placeholders=_dedupe(placeholders))


def choose_role_identity(jd_profile: JDProfile, profile: Profile) -> str:
    """Choose exactly one supported role identity."""
    target = f"{jd_profile.title} {' '.join(jd_profile.technical_keywords)}".lower()
    for role in profile.role_identities:
        role_tokens = [token for token in role.lower().split() if len(token) > 2]
        if any(token in target for token in role_tokens):
            return role
    if "ai" in target or "llm" in target:
        return "AI Engineer"
    if "data" in target:
        return "Data Engineer"
    return "Software Engineer"


def _headline(jd_profile: JDProfile, role_identity: str) -> str:
    title = jd_profile.title if jd_profile.title != "Target Role" else role_identity
    keywords = [keyword for keyword in jd_profile.technical_keywords if len(keyword) > 2][:3]
    suffix = ", ".join(keywords)
    return f"{title} | {suffix}" if suffix else title


def _work_mode_line(jd_profile: JDProfile) -> str:
    if jd_profile.work_mode == "unknown":
        return "Open to the role's work mode"
    if jd_profile.location:
        return f"Open to {jd_profile.work_mode} work in {jd_profile.location}"
    return f"Open to {jd_profile.work_mode} work"


def _top_keywords(evidence: list[EvidenceItem]) -> list[str]:
    useful = [
        item.keyword
        for item in evidence
        if item.evidence_tier in {"A", "B", "adjacency"} and item.required_or_preferred == "required"
    ]
    useful.extend(item.keyword for item in evidence if item.evidence_tier in {"A", "B"})
    return _dedupe(useful)[:5]


def _build_summary(
    role_identity: str,
    top_keywords: list[str],
    jd_profile: JDProfile,
    profile: Profile,
) -> str:
    first = top_keywords[0] if top_keywords else "Python"
    second = top_keywords[1] if len(top_keywords) > 1 else "data systems"
    domain = jd_profile.domain or "regulated and data-intensive environments"
    return (
        f"{role_identity} with 8+ years across {first} and {second}, combining production software delivery with applied data and AI systems. "
        f"Built document Q&A, data warehouse, ETL, analytics, and Java commerce platforms across medical-device, mining, research, and commerce settings. "
        f"Brings Python, SQL, LLM integration, BI, and software engineering depth with evidence tied to {domain} needs."
    )


def _build_skill_groups(
    evidence: list[EvidenceItem],
    profile: Profile,
    working_knowledge: list[str],
) -> list[tuple[str, list[str]]]:
    relevant = _dedupe(
        [
            item.real_evidence or item.keyword
            for item in evidence
            if item.evidence_tier in {"A", "B", "adjacency"} and item.real_evidence
        ]
    )
    ai = _filter_present(
        [
            "OpenAI API",
            "Gemini API",
            "LLM integration",
            "prompt engineering",
            "document Q&A",
            "retrieval-augmented generation",
        ],
        relevant,
    )
    languages = _filter_present(["Python", "Java", "JavaScript", "TypeScript", "SQL", "R"], relevant)
    data = _filter_present(
        [
            "PostgreSQL",
            "dbt",
            "ETL",
            "ELT",
            "Tableau",
            "Power BI",
            "Salesforce",
            "HubSpot",
            "data modeling",
        ],
        relevant,
    )
    backend = _filter_present(
        ["Java Spring MVC", "Spring Boot", "Hibernate", "REST APIs", "microservices", "React Native"],
        relevant,
    )
    ml = _filter_present(["scikit-learn", "Random Forest", "classification models", "ML pipelines"], relevant)
    cloud = _filter_present(["Azure", "Docker", "Git", "CI/CD", "GitHub Actions", "Linux"], relevant)
    methods = _filter_present(
        ["Agile", "Scrum", "requirements gathering", "technical documentation", "stakeholder management"],
        relevant,
    )

    groups = [
        ("Generative AI and LLM", ai),
        ("Languages", languages or ["Python", "Java", "SQL"]),
        ("Data and BI", data or ["PostgreSQL", "dbt", "ETL", "Tableau"]),
        ("Backend and APIs", backend),
        ("Machine Learning", ml),
        ("Cloud and DevOps", cloud),
        ("Methods", methods),
    ]
    if working_knowledge:
        groups.append(("Working knowledge", _dedupe(working_knowledge)))
    return [(category, items) for category, items in groups if items]


def _select_experience(profile: Profile, evidence: list[EvidenceItem]) -> list[Experience]:
    keywords = [item.keyword.lower() for item in evidence if item.evidence_tier != "missing"]
    selected: list[Experience] = []
    used_metrics: set[str] = set()

    for experience in profile.experiences:
        scored_bullets = sorted(
            experience.bullets,
            key=lambda bullet: _bullet_score(bullet, keywords),
            reverse=True,
        )
        bullets = []
        for bullet in scored_bullets:
            if _metric_reused(bullet, used_metrics, profile.supported_metrics):
                continue
            _remember_metrics(bullet, used_metrics, profile.supported_metrics)
            bullets.append(bullet)
            if len(bullets) >= (4 if experience.company == "Flosonics Medical" else 3):
                break
        if bullets:
            selected.append(
                Experience(
                    company=experience.company,
                    title=experience.title,
                    location=experience.location,
                    dates=experience.dates,
                    bullets=bullets,
                )
            )
        if len(selected) >= 5:
            break
    return selected


def _bullet_score(bullet: str, keywords: list[str]) -> int:
    lowered = bullet.lower()
    return sum(2 for keyword in keywords if keyword in lowered) + len(relevant_metrics(bullet))


def relevant_metrics(text: str) -> list[str]:
    return [token for token in ["40%", "99.5% F1 score", "13 B2B commerce platforms", "four engineers", "5 hours to minutes"] if token.lower() in text.lower()]


def _metric_reused(bullet: str, used_metrics: set[str], supported_metrics: list[str]) -> bool:
    return any(metric.lower() in bullet.lower() and metric in used_metrics for metric in supported_metrics)


def _remember_metrics(bullet: str, used_metrics: set[str], supported_metrics: list[str]) -> None:
    for metric in supported_metrics:
        if metric.lower() in bullet.lower():
            used_metrics.add(metric)


def _first_gap(evidence: list[EvidenceItem]) -> str:
    for item in evidence:
        if item.evidence_tier == "missing":
            return item.keyword
    for item in evidence:
        if item.evidence_tier == "C":
            return item.keyword
    return ""


def _analysis_lines(evidence: list[EvidenceItem], residual_gap: str, jd_profile: JDProfile) -> list[str]:
    strong = len([item for item in evidence if item.strength == "strong"])
    medium = len([item for item in evidence if item.strength == "medium"])
    missing = len([item for item in evidence if item.strength == "missing"])
    lines = [
        f"Coverage shows {strong} strong matches and {medium} medium matches against the role's required and preferred signals.",
        f"The strongest proof points are AI assistant delivery, data warehousing, ETL, Java commerce systems, and applied ML work.",
    ]
    if residual_gap:
        lines.append(f"One honest residual gap is {residual_gap}; it is not claimed as direct experience.")
    elif jd_profile.work_mode != "unknown":
        lines.append(f"Logistics are aligned with {jd_profile.work_mode} work and Canadian work eligibility.")
    if missing >= 2:
        lines.append("Two or more required signals are missing, so the probability is intentionally conservative.")
    return lines[:4]


def _cover_proof_points(plan: ResumePlan) -> list[str]:
    points: list[str] = []
    for experience in plan.experience:
        points.extend(experience.bullets[:2])
    return points[:3]


def _build_cover_letter_body(
    *,
    title: str,
    company: str,
    domain_hook: str,
    proof_points: list[str],
    plan: ResumePlan,
    needs_fast_ramp: bool,
    fast_ramp_items: list[str],
) -> list[str]:
    first_proof = proof_points[0] if proof_points else "I have built data and software systems across regulated, commerce, and research environments."
    second_proof = proof_points[1] if len(proof_points) > 1 else "I have combined Python, SQL, Java, analytics, and stakeholder-facing delivery across multiple roles."
    third_proof = proof_points[2] if len(proof_points) > 2 else "My background includes BI, software engineering, applied ML, and technical leadership."
    ramp = ""
    if needs_fast_ramp:
        missing = ", ".join(_dedupe(fast_ramp_items)[:3])
        ramp = (
            f" Where the role calls for {missing}, I would approach the ramp directly: map the tool to the adjacent systems I have delivered, validate assumptions quickly, and keep claims grounded in working output."
        )
    work_mode_text = plan.jd_profile.work_mode if plan.jd_profile.work_mode != "unknown" else "the role's"

    paragraphs = [
        "Dear Hiring Manager,",
        (
            f"I am interested in the {title} role at {company} because it connects closely with my work building AI, data, and software systems for {domain_hook} teams. "
            f"I bring 8+ years across Python, SQL, Java, LLM integration, BI, and production software delivery, with a practical record of turning messy operational data and user needs into reliable tools."
        ),
        (
            f"My closest proof point is this: {first_proof} I also {second_proof[0].lower() + second_proof[1:]} "
            f"That combination matters for this role because it shows I can work across data pipelines, applications, stakeholders, and model-assisted workflows without stretching beyond the facts."
        ),
        (
            f"Earlier, {third_proof[0].lower() + third_proof[1:]} These experiences give me a useful base for the responsibilities in the posting, especially requirements translation, technical delivery, and clear communication across teams.{ramp}"
        ),
        (
            f"I am based in Sudbury, Ontario, a Canadian permanent resident, and legally eligible to work in Canada without sponsorship. "
            f"I am open to {work_mode_text} work mode and open to relocation for the right opportunity. "
            f"I would be glad to discuss how my AI, data, and software background can support {company}'s priorities."
        ),
    ]
    return _fit_cover_letter_word_count(paragraphs)


def _fit_cover_letter_word_count(paragraphs: list[str]) -> list[str]:
    filler = (
        "I work best where the problem is concrete, the users are close enough to learn from, and the output has to be useful in production or operations."
    )
    while _body_word_count(paragraphs) < 280:
        paragraphs[-2] = f"{paragraphs[-2]} {filler}"
    if _body_word_count(paragraphs) > 320:
        paragraphs[-2] = paragraphs[-2].split(" I work best where")[0]
    return paragraphs


def _body_word_count(paragraphs: list[str]) -> int:
    body = " ".join(paragraph for paragraph in paragraphs if not paragraph.lower().startswith("dear "))
    return len(body.split())


def _long_answer(question: str, resume_plan: ResumePlan) -> str:
    proof = resume_plan.experience[0].bullets[0] if resume_plan.experience else resume_plan.summary
    answer = (
        f"I would point to the same pattern that runs through my recent work: I translate ambiguous business or technical needs into shipped systems. "
        f"{proof} I have also worked across Python, SQL, Java, analytics, and stakeholder-facing delivery, which helps me connect implementation details with operational value. "
        f"For this question, my strongest answer is that I can bring practical engineering judgment, clear communication, and truthful scope control to the role."
    )
    words = answer.split()
    if len(words) > 140:
        return " ".join(words[:140]).rstrip(".") + "."
    return answer


def _filter_present(candidates: list[str], relevant: list[str]) -> list[str]:
    relevant_lower = " ".join(relevant).lower()
    return [candidate for candidate in candidates if candidate.lower() in relevant_lower]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key and key not in seen:
            out.append(item)
            seen.add(key)
    return out
