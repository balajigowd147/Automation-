from classroom.api import (
    get_classroom_service,
    get_courses,
    get_assignments
)

from browser_automation.browser import (
    open_classroom,
    open_assignment
)

from browser_automation.actions import (
    open_add_or_create,
    upload_file,
    review_before_turn_in,
    turn_in_assignment
)


def main():

    print("\nConnecting to Google Classroom API...")

    service = get_classroom_service()

    courses = get_courses(service)

    print(
        f"Courses found: {len(courses)}"
    )

    playwright, context, page = open_classroom()


    try:
        for course in courses:

            assignments = get_assignments(
                service,
                course["id"]
            )

            if not assignments:
                continue

            assignment = assignments[0]

            print(
                "Course:",
                course["name"]
            )

            print(
                "Assignment:",
                assignment["title"]
            )

            open_assignment(
                page,
                assignment["alternateLink"]
            )

            open_add_or_create(page)


            upload_file(
                page,
                "outputs/test.txt"
            )


            approved = review_before_turn_in(
                page
            )

            if approved:

                turn_in_assignment(
                    page
                )

            else:

                print(
                    "\nAssignment was NOT submitted."
                )

            break


        print("\n========================================")
        print("          AUTOMATION COMPLETED")
        print("========================================")


        input(
            "\nPress Enter to close the browser..."
        )


    finally:


        if not page.is_closed():

            context.close()

        playwright.stop()


if __name__ == "__main__":

    main()