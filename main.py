from classroom_api import (
    get_classroom_service,
    get_courses,
    get_assignments
)

from playwright_classroom import (
    open_classroom,
    open_assignment,
    upload_file,
    turn_in_assignment,
    review_before_turn_in
)


service = get_classroom_service()

courses = get_courses(service)



playwright, context, page = open_classroom()


print("\n===== CLASSROOM AUTOMATION =====")


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

    # Open assignment
    open_assignment(
        page,
        assignment["alternateLink"]
    )

    # Upload test file
    upload_file(
        page,
        "outputs/test.txt"
    )

    if review_before_turn_in(page):

        turn_in_assignment(page)

    else:

        print(
            "\nAssignment was NOT submitted."
        )

    break


print("\n===== COMPLETED =====")

input(
    "\nPress Enter to close..."
)


if not page.is_closed():

    context.close()

playwright.stop()