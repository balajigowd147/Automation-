from pathlib import Path
from playwright.sync_api import sync_playwright


PROFILE_DIR = Path.cwd() / "playwright_profile"


def open_classroom():


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

    page.goto(course_link)

    page.wait_for_load_state(
        "domcontentloaded"
    )

    print("Opened:", page.url)


def read_assignment(page):

    page.wait_for_timeout(2000)

    text = page.locator(
        "body"
    ).inner_text()

    print(text)

    return text


def open_assignment(page, assignment_link):

    page.goto(assignment_link)

    page.wait_for_load_state(
        "domcontentloaded"
    )

    page.wait_for_timeout(1500)

    print("Opened:", page.url)

    return read_assignment(page)