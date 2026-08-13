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


def get_courses(page):

    print("\n===== FINDING COURSES =====\n")

    # Classroom course cards normally contain links to /c/<course-id>
    course_links = page.locator('a[href*="/c/"]')

    courses = []

    for i in range(course_links.count()):

        link = course_links.nth(i)

        try:
            name = link.inner_text().strip()
            href = link.get_attribute("href")

            if name and href and "/c/" in href:

                # Avoid duplicates
                if not any(course["href"] == href for course in courses):

                    courses.append({
                        "name": name,
                        "href": href
                    })

        except Exception:
            continue

    print(f"Found {len(courses)} possible courses.\n")

    for course in courses:
        print(course["name"])
        print(course["href"])
        print()

    return courses


def get_assignments(page):

    print("\n===== READING ASSIGNMENTS =====\n")

    page.wait_for_timeout(1500)

    assignment_links = page.locator('a[href*="/a/"]')

    assignments = []

    for i in range(assignment_links.count()):

        link = assignment_links.nth(i)

        try:
            title = link.inner_text().strip()
            href = link.get_attribute("href")

            if not title or not href:
                continue

            # Avoid duplicates
            if any(a["url"] == href for a in assignments):
                continue

            assignments.append({
                "title": title,
                "url": href
            })

        except Exception:
            continue

    print(f"Found {len(assignments)} assignment links.")

    for assignment in assignments:

        print("\nTitle:", assignment["title"])
        print("URL:", assignment["url"])

    return assignments


if __name__ == "__main__":

    playwright, context, page = open_classroom()

    print("Google Classroom opened!")
    print("URL:", page.url)

    # Give the page time to finish rendering
    page.wait_for_timeout(2000)

    courses = get_courses(page)

    print("\n===== STARTING COURSE LOOP =====")

    for index, course in enumerate(courses, start=1):

        print("\n" + "=" * 60)
        print(f"COURSE {index}: {course['name']}")
        print("=" * 60)

        # Navigate directly to the course
        page.goto(
            "https://classroom.google.com" + course["href"]
            if course["href"].startswith("/")
            else course["href"]
        )

        page.wait_for_load_state("domcontentloaded")

        page.wait_for_timeout(1500)

        print("Course URL:", page.url)

        get_assignments(page)

        # Go back to Classroom home for the next course
        page.goto("https://classroom.google.com")

        page.wait_for_load_state("domcontentloaded")

        page.wait_for_timeout(1000)

    print("\n===== LOOP COMPLETED =====")

    input("\nPress Enter to close...")

    if not page.is_closed():
        context.close()

    playwright.stop()