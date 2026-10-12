"""Doctor Connect preview.

Everything served here is illustrative. Profiles are fictional placeholders that
exist only to show the intended information architecture; no credentials,
availability, reviews, or bookings are real. Real onboarding, verification and
appointment workflows are Phase 5 work (see docs/roadmap.md).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/doctors", tags=["doctor-connect (demo)"])

DEMO_NOTICE = (
    "Demonstration only. These are fictional sample profiles used to preview the Doctor Connect "
    "experience. No real clinician, credential, availability, or booking is represented."
)


class DemoDoctor(BaseModel):
    id: str
    display_name: str
    specialty: str
    focus_areas: list[str]
    languages: list[str]
    consultation_types: list[str]
    city: str
    is_demo: bool = True


class DoctorDirectory(BaseModel):
    notice: str
    doctors: list[DemoDoctor]


_DEMO_DOCTORS = [
    DemoDoctor(
        id="demo-1",
        display_name="Sample profile A",
        specialty="Obstetrics & Gynaecology",
        focus_areas=["Menstrual disorders", "PCOS education", "Adolescent health"],
        languages=["Hindi", "English"],
        consultation_types=["In person", "Video (planned)"],
        city="Example city",
    ),
    DemoDoctor(
        id="demo-2",
        display_name="Sample profile B",
        specialty="Gynaecology",
        focus_areas=["Endometriosis", "Pelvic pain", "Fertility counselling"],
        languages=["English", "Marathi"],
        consultation_types=["In person"],
        city="Example city",
    ),
    DemoDoctor(
        id="demo-3",
        display_name="Sample profile C",
        specialty="Family medicine",
        focus_areas=["General women's wellness", "Menopause", "Preventive care"],
        languages=["Hindi", "English", "Bengali"],
        consultation_types=["In person", "Audio (planned)"],
        city="Example city",
    ),
]


@router.get("", response_model=DoctorDirectory)
def list_demo_doctors() -> DoctorDirectory:
    return DoctorDirectory(notice=DEMO_NOTICE, doctors=_DEMO_DOCTORS)
