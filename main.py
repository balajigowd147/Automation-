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

    print("\n========================================")
    print("      GOOGLE CLASSROOM AUTOMATION")
    print("========================================")


    # --------------------------------
    # 1. Connect to Classroom API
    # --------------------------------

    print("\nConnecting to Google Classroom API...")

    service = get_classroom_service()

    courses = get_courses(service)

    print(
        f"Courses found: {len(courses)}"
    )


    # --------------------------------
    # 2. Start Playwright
    # --------------------------------

    playwright, context, page = open_classroom()


    try:

        # --------------------------------
        # 3. Find an assignment
        # --------------------------------

        for course in courses:

            assignments = get_assignments(
                service,
                course["id"]
            )

            if not assignments:
                continue

            assignment = assignments[0]

            print("\n========================================")
            print("COURSE")
            print("========================================")

            print(
                "Course:",
                course["name"]
            )

            print(
                "Assignment:",
                assignment["title"]
            )


            # --------------------------------
            # 4. Open assignment
            # --------------------------------

            open_assignment(
                page,
                assignment["alternateLink"]
            )


            # --------------------------------
            # 5. Open Add or create
            # --------------------------------

            open_add_or_create(page)


            # --------------------------------
            # 6. Upload local file
            # --------------------------------

            upload_file(
                page,
                "outputs/test.txt"
            )


            # --------------------------------
            # 7. User review + approval
            # --------------------------------

            approved = review_before_turn_in(
                page
            )


            # --------------------------------
            # 8. Turn in only if approved
            # --------------------------------

            if approved:

                turn_in_assignment(
                    page
                )

            else:

                print(
                    "\nAssignment was NOT submitted."
                )


            # --------------------------------
            # Currently process only one
            # assignment for testing
            # --------------------------------

            break


        print("\n========================================")
        print("          AUTOMATION COMPLETED")
        print("========================================")


        # Keep browser open so you can inspect it
        input(
            "\nPress Enter to close the browser..."
        )


    finally:

        # --------------------------------
        # 9. Close Playwright safely
        # --------------------------------

        if not page.is_closed():

            context.close()

        playwright.stop()


if __name__ == "__main__":

    main()