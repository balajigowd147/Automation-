from pathlib import Path
from playwright.sync_api import sync_playwright


# Persistent browser profile
# This keeps your Google Classroom login/session.
PROFILE_DIR = Path.cwd() / "playwright_profile"


def open_classroom():

    print("\n===== STARTING PLAYWRIGHT =====")

    playwright = sync_playwright().start()

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False
    )

    page = (
        context.pages[0]
        if context.pages
        else context.new_page()
    )

    page.goto(
    "https://classroom.google.com",
    wait_until="domcontentloaded",
    timeout=60000
    )

    page.wait_for_load_state(
        "domcontentloaded"
    )

    print("Google Classroom opened.")

    return playwright, context, page


def open_course(page, course_link):

    print("\n===== OPENING COURSE =====")

    page.goto(course_link)

    page.wait_for_load_state(
        "domcontentloaded"
    )

    print("Opened:", page.url)


def read_assignment(page):

    print("\n===== ASSIGNMENT PAGE =====")

    page.wait_for_timeout(2000)

    text = page.locator(
        "body"
    ).inner_text()

    print(text)

    return text


def open_assignment(page, assignment_link):

    print("\n===== OPENING ASSIGNMENT =====")

    page.goto(assignment_link)

    page.wait_for_load_state(
        "domcontentloaded"
    )

    page.wait_for_timeout(1500)

    print("Opened:", page.url)

    # Read the assignment page
    return read_assignment(page)