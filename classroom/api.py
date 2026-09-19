import os

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_classroom_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES,
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES,
            )

            creds = flow.run_local_server(
                port=0,
            )

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build(
        "classroom",
        "v1",
        credentials=creds,
    )


def get_courses(service):

    courses = []

    request = service.courses().list(
        pageSize=100,
    )

    while request is not None:

        response = request.execute()

        courses.extend(
            response.get("courses", [])
        )

        request = service.courses().list_next(
            request,
            response,
        )

    return courses


def get_assignments(service, course_id):
    assignments = []

    request = service.courses().courseWork().list(
        courseId=course_id,
        pageSize=100,
    )

    while request is not None:

        response = request.execute()

        assignments.extend(
            response.get("courseWork", [])
        )

        request = service.courses().courseWork().list_next(
            request,
            response,
        )

    return assignments


def get_student_submission(
    service,
    course_id,
    coursework_id,
):

    submissions = []

    request = (
        service.courses()
        .courseWork()
        .studentSubmissions()
        .list(
            courseId=course_id,
            courseWorkId=coursework_id,
            userId="me",
            pageSize=100,
        )
    )

    while request is not None:

        response = request.execute()

        submissions.extend(
            response.get(
                "studentSubmissions",
                [],
            )
        )

        request = (
            service.courses()
            .courseWork()
            .studentSubmissions()
            .list_next(
                request,
                response,
            )
        )

    if not submissions:
        return None

    return submissions[0]


def get_submission_status(
    service,
    course_id,
    coursework_id,
):

    submission = get_student_submission(
        service,
        course_id,
        coursework_id,
    )

    if submission is None:
        return None

    return submission.get("state")


def get_course_assignments_with_status(service, course_id):

    assignments = get_assignments(
        service,
        course_id,
    )

    results = []

    for assignment in assignments:

        coursework_id = assignment.get("id")

        if not coursework_id:
            continue

        status = get_submission_status(
            service,
            course_id,
            coursework_id,
        )

        results.append({
            "course_id": course_id,
            "assignment_id": coursework_id,
            "title": assignment.get(
                "title",
                "Untitled",
            ),
            "state": assignment.get(
                "state",
                "UNKNOWN",
            ),
            "submission_status": status,
            "assignment": assignment,
        })

    return results

def get_drive_service():

    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES,
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES,
            )

            creds = flow.run_local_server(
                port=0,
            )

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build(
        "drive",
        "v3",
        credentials=creds,
    )


def get_course_materials(service, course_id):

    materials = []

    request = (
        service.courses()
        .courseWorkMaterials()
        .list(
            courseId=course_id,
            pageSize=100,
        )
    )

    while request is not None:

        response = request.execute()

        materials.extend(
            response.get("courseWorkMaterial", [])
        )

        request = (
            service.courses()
            .courseWorkMaterials()
            .list_next(
                request,
                response,
            )
        )

    return materials


def get_announcement_materials(service, course_id):

    materials = []

    request = (
        service.courses()
        .announcements()
        .list(
            courseId=course_id,
            pageSize=100,
        )
    )

    while request is not None:

        response = request.execute()

        announcements = response.get("announcements", [])

        for announcement in announcements:

            announcement_text = announcement.get(
                "text",
                ""
            ).strip()

            for item in announcement.get("materials", []):

                drive_wrapper = item.get("driveFile")

                if not drive_wrapper:
                    continue

                drive_file = drive_wrapper.get(
                    "driveFile",
                    {}
                )

                file_id = drive_file.get("id")
                file_name = drive_file.get("title")

                if not file_id or not file_name:
                    continue

                materials.append({
                    "title": file_name,
                    "file_id": file_id,
                    "file_name": file_name,
                    "source": "announcement",
                    "announcement_text": announcement_text,
                })

        request = (
            service.courses()
            .announcements()
            .list_next(
                request,
                response,
            )
        )

    return materials