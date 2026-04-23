from __future__ import annotations

import re
from collections.abc import Iterable

FACULTY_NAMES: list[str] = [
    "Mr. Alla Pranav Sai Reddy",
    "Dr. Bhimavarapu Krishna Reddy",
    "MS. PAVANI KARRA",
    "Ms. Nandini vogirala",
    "Dr. James Deva Koresh H",
    "MS. R NITHYA",
    "Mr. U. Venkateswara Rao",
    "Mrs. Sunkara Anitha",
    "KALLURI MERCY BHIKSHAVATHI",
    "MS. POLEPALLI SAI VEERA VENKATA SAMHITHA",
    "Ms. G. Parimala",
    "Ms. T. Leelavathy",
    "MS. JARUGUMALLA DAYANIKA",
    "MS. SAJIDA SULTANA SHAIK",
    "Mr. Mohana Venkateswara Rao mathi",
    "Mr. Rudru Gowtham",
    "Ms. V. Sai Spandana",
    "Ms. Kolla Jyotsna",
    "MR. DULLA SRINIVAS",
    "MR. UTTEJ KUMAR NANNAPANENI",
    "Dr. J. Vijitha Ananthi",
    "Ms. Kollabathula Nimnagasri",
    "Mr. Chavva Ravi Kishore Reddy",
    "MR. BADHELI KRISHNAKANTH",
    "MS. CHUKKA SWARNA LALITHA",
    "Dr. Rambabu Kusuma",
    "Dr. E. deepak chowdary",
    "Mr. Akhil Babu Edara",
    "mR. NALLURI BRAHMANAIDU",
    "Mr. Akula Gopi",
    "Mr. Kumar Devapogu",
    "DR. T. R. RAJESH",
    "MS. NEELI SARVANI",
    "Mrs. Magham Sumalatha",
    "Dr. Vinoj J",
    "Ms. Nakkala MoUNIKA",
    "Mr. T Narasimha rao",
    "Ms. N. Bhargavi",
    "Mr. T. Latesh Babu",
    "Mr. Panthagani Vijaya Babu",
    "Mrs. M. Bhargavi",
    "MS. BHUKYA MANEESHA",
    "Dr. M. Vijai Meyyappan",
    "MR. S. SURESH BABU",
    "mrs. SD. Shareefunnisa",
    "MR. SYED NAFEES AHAMED",
    "Mr. Shaik Jani",
    "Mr. K. Pavan Kumar",
    "Mrs. N. Archana",
    "MS. TALARI PRIYABHARATHI",
    "Dr. P. Siva Prasad",
    "Ms. Shaik Reehana",
    "Dr. P. Jhansi Lakshmi",
    "Mr. Kiran Kumar Kalagadda",
    "Mr. Pagidipalli Kiran Kumar Raja",
    "MRS. ANUSHA VISWANADAPALLI",
]

STUDENTS_PER_FACULTY = 70
FACULTY_PASSWORD = "Faculty@123"
TEST_FACULTY_EMAIL = "hidden.test.faculty@vignan.ac.in"
TEST_FACULTY_PASSWORD = "Faculty@123"
TEST_FACULTY_NAME = "__hidden_test_faculty__"
LOGIN_ID_PREFIX = "VIG"
CURRENT_SEMESTER = 2


def faculty_name_for_position(index: int) -> str:
    faculty_index = min(index // STUDENTS_PER_FACULTY, len(FACULTY_NAMES) - 1)
    return FACULTY_NAMES[faculty_index]


def faculty_email(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    slug = re.sub(r"\.+", ".", slug)
    return f"{slug}@vignan.ac.in"


def cleaned_counselor_name(name: str | None) -> str:
    return (name or "").strip()


def active_counselor_names(names: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    counselors: list[str] = []
    for raw_name in names:
        name = cleaned_counselor_name(raw_name)
        if not name or name == "-":
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        counselors.append(name)
    return sorted(counselors, key=str.casefold)


def build_faculty_login_id(year: int, semester: int, section: str | int, batch: int) -> str:
    section_text = str(section).strip()
    return f"{LOGIN_ID_PREFIX}{year}{semester}{section_text}{batch}"


def build_faculty_login_ids(
    student_assignments: Iterable[tuple[object, ...]],
    counselor_names: Iterable[str],
    semester: int = CURRENT_SEMESTER,
) -> dict[str, str]:
    canonical_names = {name.casefold(): name for name in counselor_names}
    counselor_group_registrations: dict[str, dict[tuple[int, str], list[str]]] = {}

    for assignment in student_assignments:
        if len(assignment) >= 4:
            raw_year, raw_section, raw_counselor_name, raw_registration_number = assignment[:4]
        elif len(assignment) == 3:
            raw_year, raw_section, raw_counselor_name = assignment
            raw_registration_number = None
        else:
            continue

        counselor_name = canonical_names.get((raw_counselor_name or "").strip().casefold())
        if not counselor_name or raw_year is None:
            continue

        section_text = re.sub(r"[^0-9]", "", str(raw_section or "").strip())
        if not section_text:
            continue

        group = (int(raw_year), section_text)
        counselor_group_registrations.setdefault(counselor_name, {})
        counselor_group_registrations[counselor_name].setdefault(group, [])
        if raw_registration_number:
            counselor_group_registrations[counselor_name][group].append(raw_registration_number.strip())

    primary_groups: dict[str, tuple[int, str]] = {}
    for counselor_name, groups in counselor_group_registrations.items():
        primary_groups[counselor_name] = max(
            groups.items(),
            key=lambda item: (len(item[1]), item[0][0], int(item[0][1])),
        )[0]

    counselors_by_group: dict[tuple[int, str], list[str]] = {}
    for counselor_name, group in primary_groups.items():
        counselors_by_group.setdefault(group, []).append(counselor_name)

    login_ids: dict[str, str] = {}
    used_ids: set[str] = set()
    for (year, section), names in sorted(counselors_by_group.items(), key=lambda item: (item[0][0], int(item[0][1]))):
        ordered_names = sorted(
            names,
            key=lambda name: (
                min(counselor_group_registrations.get(name, {}).get((year, section), ["ZZZZZZZZZZ"])),
                name.casefold(),
            ),
        )
        for batch, counselor_name in enumerate(ordered_names, start=1):
            login_id = build_faculty_login_id(year, semester, section, batch)
            login_ids[counselor_name] = login_id
            used_ids.add(login_id)

    fallback_sequence = 1
    for counselor_name in sorted(counselor_names, key=str.casefold):
        if counselor_name in login_ids:
            continue
        while True:
            login_id = build_faculty_login_id(0, semester, "0", fallback_sequence)
            fallback_sequence += 1
            if login_id not in used_ids:
                login_ids[counselor_name] = login_id
                used_ids.add(login_id)
                break

    return login_ids
