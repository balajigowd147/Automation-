from pathlib import Path
from playwright.sync_api import sync_playwright


PROFILE_DIR = Path.cwd() / "playwright_profile"


def open_classroom():

    playwright = sync_playwright().start()

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False
    )

    page = context.pages[0] if context.pages else context.new_page()

    page.goto("https://classroom.google.com")

    page.wait_for_load_state("domcontentloaded")

    return playwright, context, page


def open_course(page, course_link):

    print("\nOpening course with Playwright...")

    page.goto(course_link)

    page.wait_for_load_state("domcontentloaded")

    print("Opened:", page.url)


def open_add_or_create(page):

    print("\n===== OPENING ADD OR CREATE =====")

    button = page.get_by_role(
        "button",
        name="Add or create"
    )

    button.click()

    page.wait_for_timeout(1000)

    print("Add or create menu opened.")


def read_assignment(page):

    print("\n===== ASSIGNMENT PAGE =====")

    page.wait_for_timeout(2000)

    text = page.locator("body").inner_text()

    print(text)

    return text

def open_assignment(page, assignment_link):

    print("\nOpening assignment with Playwright...")

    page.goto(assignment_link)

    page.wait_for_load_state("domcontentloaded")

    page.wait_for_timeout(1500)

    print("Opened:", page.url)

    read_assignment(page)

    open_add_or_create(page)

