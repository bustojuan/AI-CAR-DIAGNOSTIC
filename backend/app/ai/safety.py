"""Conservative phrase triage, deliberately accepting some false positives."""

import re
import unicodedata

from app.models.diagnostic import Assessment, Check, SymptomExtraction, Urgency, UrgencyAssessment


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )


# Phrase rules are conservative triage, not a mechanical fault detector.
# Each positive clause wins over contradictory reassurance elsewhere in the history.
HAZARDS = {
    "Possible loss of braking": (
        r"brak\w*.{0,45}(fail|floor|barely|not work|not respond|stopped working|"
        r"doesn.t|not stop|won.t|don.t|lost)",
        r"(cannot|can.t|unable to).{0,20}(brake|stop)",
        r"\b(no brakes|sin frenos|no frena)\b",
        r"(freno|pedal).{0,45}(falla|suelo|fondo|no responde|apenas)",
        r"brak\w*.{0,20}(pedal.{0,15})?(soft|spongy|sinks)",
    ),
    "Possible loss of steering": (
        r"steer\w*.{0,40}(fail|lost|lock|not respond|not work|doesn.t|stuck|won.t)",
        r"(cannot|can.t|unable to).{0,15}steer|\bno steering\b",
        r"(lost|loss of).{0,15}(steering|braking)",
        r"direccion.{0,40}(falla|bloque|perd|no responde)|sin direccion",
    ),
    "Reported overheating or excessive temperature": (
        r"overheat\w*|sobrecalent\w*|temperatura.{0,20}(rojo|alta)",
        r"temperature.{0,30}(red|above normal|too high)|red.{0,15}temperature",
    ),
    "Reported fire or flames": (r"\bfire\b|\bflames?\b|incendio|\bllamas\b",),
    "Smoke near occupants or engine; source needs checking": (
        r"smoke.{0,40}(bonnet|hood|cabin|wire|engine bay)",
        r"(bonnet|hood|cabin|engine bay).{0,30}smok\w*",
        r"humo.{0,30}(capo|habitaculo|cable)",
        r"\b(smoke|humo)\s*(from (my |the )?(car|vehicle))?[.!?]*$",
    ),
    "Reported fuel leakage": (
        r"(fuel|diesel|petrol|gasoline).{0,35}(leak|pour|puddle)",
        r"(leak|pour|puddle|fuga|perdida|charco).{0,35}(fuel|petrol|combustible|gasoil|diesel|gasolina)",
    ),
    "Possible electrical burning or arcing": (
        r"(spark|arcing|burning).{0,25}(wire|electric|battery)",
        r"(chispa|quemad).{0,25}(cable|electric|bateria)",
    ),
    "Reported oil-pressure warning": (r"oil pressure|presion de aceite",),
}


def clauses(text: str) -> list[str]:
    return re.split(r"[.!?;\n]+|\b(?:but|however|although|pero|aunque)\b", normalize(text))


def negated(clause: str, match: re.Match) -> bool:
    # Restrict negation to the matched mention. 'Brakes not working' and 'no brakes'
    # are hazards; 'not overheating' and 'no fuel leaks' are explicit denials.
    prefix = clause[max(0, match.start() - 45) : match.start()]
    if re.search(
        r"\b(no|not|without|never|sin|no longer|not on)\s+(?:any\s+|signs? of\s+|active\s+)?$",
        prefix,
    ):
        return True
    if re.search(r"\bno (?:smoke|fire|flames?|fuel leaks?|overheating)(?:,? (?:or|and) )$", prefix):
        return True
    return bool(
        re.search(
            r"\b(?:is not|isn.t|not|never|no longer|are not|aren.t|does not|do not)\s+"
            r"(?:currently\s+)?(?:fail\w*|leak\w*|overheat\w*|on fire|burn\w*|lock\w*)",
            match.group(),
        )
    )


def critical_warning_signs(text: str) -> list[str]:
    return [
        label
        for label, patterns in HAZARDS.items()
        if any(
            not negated(clause, match)
            for clause in clauses(text)
            for pattern in patterns
            for match in re.finditer(pattern, clause)
        )
    ]


def has_critical_hazard(text: str) -> bool:
    return bool(critical_warning_signs(text))


def power_warning(text: str) -> bool:
    def present(pattern):
        return any(
            not negated(clause, m) for clause in clauses(text) for m in re.finditer(pattern, clause)
        )

    return bool(
        present(
            r"(?:loss of |lost |losing |loses |reduced |low |lack of |no )power|"
            r"perdida de potencia|pierde potencia"
        )
        and present(r"warning|engine light|check engine|testigo|luz.{0,15}motor|averia")
    )


def no_symptoms(text: str) -> bool:
    return normalize(text).strip(" .!?") in {
        "no symptoms",
        "none",
        "nothing",
        "no problems",
        "everything is fine",
        "no symptoms provided",
        "sin sintomas",
        "ninguno",
        "todo bien",
    }


def missing_safety_information(text: str) -> list[str]:
    value = normalize(text)
    groups = (
        (
            r"(?:brak\w*|frenos?).{0,25}(?:normal|fine|work|fail|floor|impaired)"
            r"|no brakes|sin frenos",
            "Whether braking is normal or impaired",
        ),
        (
            r"(?:steer\w*|direccion).{0,25}(?:normal|fine|work|fail|lock|impaired)|cannot steer",
            "Whether steering is normal or impaired",
        ),
        (
            r"overheat|sobrecalent|(?:temperature|temperatura).{0,25}(?:normal|red|high|rojo|alta)",
            "Engine temperature",
        ),
        (
            r"no (?:red |dashboard )?warning lights|warning lights.{0,20}(?:off|none)|"
            r"red.{0,15}(?:warning|light)|(?:warning|light).{0,15}red",
            "Whether any red dashboard warning light is on",
        ),
        (r"smoke|fire|flame|humo|incendio", "Whether smoke or fire is present and its source"),
        (
            r"(?:fuel|diesel|petrol|combustible|gasoil).{0,25}(leak|fuga)|fuga.{0,20}(combustible|gasoil)",
            "Whether there is a fuel leak",
        ),
    )
    return [question for pattern, question in groups if not re.search(pattern, value)]


def finalize_urgency(
    assessment: Assessment,
    text: str,
    extraction: SymptomExtraction | None,
    *,
    cited_evidence: bool,
    reported_text: str | None = None,
) -> tuple[Assessment, UrgencyAssessment]:
    """Monotonic safety overrides, independent of retrieval and model reassurance."""
    signs = critical_warning_signs(text)
    extracted_signs = extraction.warning_signs if extraction else []
    signs = list(dict.fromkeys([*signs, *extracted_signs]))[:40]
    missing = list(
        dict.fromkeys(
            [
                *missing_safety_information(reported_text if reported_text is not None else text),
                *(extraction.missing_information if extraction else []),
            ]
        )
    )[:20]
    critical = has_critical_hazard(text) or assessment.urgency_level == Urgency.CRITICAL
    if critical or (extraction and extraction.safety_critical):
        assessment = critical_assessment(text)
        basis = "deterministic_safety" if has_critical_hazard(text) else "hybrid"
        if not signs:
            signs = ["Contextual assessment reported a possible safety-critical condition"]
        explanation = (
            "A possible immediate safety hazard was reported. Stop safely and do not drive; "
            "arrange professional assistance. Contradictory reassurance does not cancel an "
            "earlier danger report. This is conservative triage, not a confirmed diagnosis."
        )
    else:
        basis = "insufficient_information" if missing else "hybrid"
        if power_warning(text) and assessment.urgency_level in (Urgency.LOW, Urgency.MODERATE):
            assessment = assessment.model_copy(update={"urgency_level": Urgency.HIGH})
            signs = list(dict.fromkeys([*signs, "Loss of power with an engine warning"]))[:40]
        if missing and assessment.urgency_level == Urgency.LOW:
            assessment = assessment.model_copy(update={"urgency_level": Urgency.MODERATE})
        if missing or assessment.urgency_level == Urgency.HIGH:
            assessment = assessment.model_copy(
                update={
                    "driving_recommendation": "inspection_before_driving",
                    "professional_assistance_recommended": True,
                }
            )
        reason = (
            "Safety information is incomplete. Moderate is a precautionary minimum, "
            "not evidence of a minor fault or permission to drive. "
            if missing
            else ""
        )
        if assessment.urgency_level == Urgency.HIGH:
            reason = "High urgency requires professional inspection before further driving. "
            if missing:
                reason += "Safety information is also incomplete. "
        explanation = reason + assessment.summary[:1200]
        explanation += (
            " Retrieved citations informed the contextual assessment; their applicability "
            "and verification limits still apply."
            if cited_evidence
            else " No cited technical evidence supports this assessment."
        )
        explanation += " This is symptom triage, not a validated mechanical diagnosis."
    return assessment, UrgencyAssessment(
        level=assessment.urgency_level,
        explanation=explanation,
        warning_signs=signs,
        missing_safety_information=missing,
        driving_recommendation=assessment.driving_recommendation,
        professional_assistance_recommended=assessment.professional_assistance_recommended,
        basis=basis,
    )


def spanish(text: str) -> bool:
    return bool(
        re.search(r"\b(mi|coche|freno|motor|humo|ruido|arranca|potencia)\b", normalize(text))
    )


def critical_assessment(text: str) -> Assessment:
    return Assessment(
        summary=("A potentially dangerous condition was reported; this is not a confirmed fault."),
        urgency_level=Urgency.CRITICAL,
        driving_recommendation="stop_safely_do_not_drive",
        follow_up_questions=[],
        possible_causes=[],
        recommended_checks=[
            Check(
                category="professional",
                description=(
                    "Arrange professional assistance or recovery. "
                    "If there is immediate danger, contact emergency services."
                ),
            )
        ],
        professional_assistance_recommended=True,
        limitations=["This is not a confirmed mechanical diagnosis."],
        next_steps=["Stop safely. Do not continue driving. Do not attempt repairs."],
    )


def unsafe_instruction(assessment: Assessment) -> bool:
    # This guard supplements the prompt; it is not a complete natural-language safety proof.
    recommendations = " ".join(
        [assessment.summary]
        + [check.description for check in assessment.recommended_checks]
        + [cause.recommended_verification for cause in assessment.possible_causes]
        + assessment.next_steps
    )
    value = normalize(recommendations)
    return any(
        re.search(pattern, value)
        for pattern in (
            r"\b(bypass|disable|disconnect)\b.{0,30}\b(abs|airbag|safety)\b",
            r"\b(road test|test drive|drive at high speed)\b",
            r"\b(open|remove)\b.{0,20}\b(hot radiator|hot coolant)\b",
            r"\b(anula|desactiva)\w*.{0,20}\b(abs|airbag)\b",
        )
    )


def professional_checks(assessment: Assessment) -> Assessment:
    """Conservatively remove the safe-observation label from hands-on/running checks.

    This finite keyword guard supplements model review; it is not a semantic safety proof.
    It changes neither the original symptom observations nor source evidence.
    """
    physical_work = re.compile(
        r"terminal|connector|\bfuse\b|voltage|multimeter|continuity|current draw|"
        r"load test|\bwiring\b|coolant (?:level|condition)|engine bay|"
        r"engine (?:is )?(?:running|idling)|(?:running|idling) engine|"
        r"\bat idle\b|\btop up\b|\bdriving\b|\bdrive\b"
    )

    def qualified_only(text):
        # A prohibition is addressed to the user, never only to a technician.
        if re.match(r"(?:stop safely|do not|never|avoid)\b", normalize(text)):
            return text
        prefix = "Qualified technician only: "
        return text if text.startswith(prefix) else (prefix + text)[:2000]

    checks = []
    for check in assessment.recommended_checks:
        category = check.category
        if category == "safe_observation" and physical_work.search(normalize(check.description)):
            category = "professional"
        description = check.description
        if category in {"technical", "professional"}:
            description = qualified_only(description)
        checks.append(Check(category=category, description=description))
    causes = []
    for cause in assessment.possible_causes:
        if physical_work.search(normalize(cause.recommended_verification)):
            cause = cause.model_copy(
                update={
                    "recommended_verification": qualified_only(cause.recommended_verification),
                    "professional_inspection_required": True,
                }
            )
        causes.append(cause)
    steps = [
        qualified_only(step) if physical_work.search(normalize(step)) else step
        for step in assessment.next_steps
    ]
    return assessment.model_copy(
        update={
            "recommended_checks": checks,
            "possible_causes": causes,
            "next_steps": steps,
        }
    )
