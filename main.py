from classroom_api import (
    get_classroom_service,
    get_courses,
    get_assignments
)

from playwright_classroom import (
    open_classroom,
    open_assignment
)


# --------------------------------
# 1. Connect to Classroom API
# --------------------------------

service = get_classroom_service()

courses = get_courses(service)


# --------------------------------
# 2. Start Playwright
# --------------------------------

playwright, context, page = open_classroom()


print("\n===== CLASSROOM AUTOMATION =====")


# --------------------------------
# 3. API + PLAYWRIGHT
# --------------------------------

for course in courses:

    assignments = get_assignments(
        service,
        course["id"]
    )

    if not assignments:
        continue

    assignment = assignments[0]

    print("\nCourse:", course["name"])
    print("Assignment:", assignment["title"])

    open_assignment(
        page,
        assignment["alternateLink"]
    )

    break


print("\n===== COMPLETED =====")

input("\nPress Enter to close...")

if not page.is_closed():
    context.close()

playwright.stop()