from pathlib import Path


def open_add_or_create(page):


    button = page.get_by_role(
        "button",
        name="Add or create"
    )

    button.click()

    page.wait_for_timeout(1000)

    print("Add or create menu opened.")


def find_browse(page):


    print("\nSearching for Browse...")

    for index, frame in enumerate(page.frames):

        browse = frame.get_by_text(
            "Browse",
            exact=True
        )

        for i in range(
            browse.count()
        ):

            element = browse.nth(i)

            if element.is_visible():

                print(
                    f"Browse found in frame {index}"
                )

                return element

    return None


def upload_file(page, file_path):

    file_path = Path(
        file_path
    ).resolve()

    # Make sure the file actually exists
    if not file_path.exists():

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    print(
        "File:",
        file_path
    )


    file_option = page.get_by_role(
        "menuitem",
        name="File"
    )

    file_option.click()

    print(
        "Google Drive file picker opened."
    )

    page.wait_for_timeout(
        1500
    )


    browse = find_browse(page)

    if browse is None:

        raise RuntimeError(
            "Could not find the Browse button "
            "inside the Google Drive file picker."
        )

    print(
        "Browse button found."
    )


    with page.expect_file_chooser() as file_chooser_info:

        browse.click()

    file_chooser = (
        file_chooser_info.value
    )

    print(
        "File chooser opened."
    )


    file_chooser.set_files(
        str(file_path)
    )

    print(
        "File selected:",
        file_path
    )


    page.wait_for_timeout(
        5000
    )

    print(
        "File upload processing completed."
    )


def review_before_turn_in(page):


    assignment_text = page.locator(
        "body"
    ).inner_text()

    print(assignment_text)


    print(
        "The browser is open so you can visually inspect"
    )

    print(
        "the assignment and uploaded files."
    )

    input(
        "\nPress Enter after you have reviewed the page..."
    )

    approval = input(
        "Do you want to TURN IN this assignment? (yes/no): "
    )

    if approval.strip().lower() == "yes":

        print(
            "\nUser approved submission."
        )

        return True

    print(
        "\nSubmission cancelled."
    )

    return False


def turn_in_assignment(page):

    page.wait_for_timeout(
        2000
    )

    turn_in_elements = page.get_by_text(
        "Turn in",
        exact=True
    )

    print(
        "Turn in elements found:",
        turn_in_elements.count()
    )

    visible_turn_in = None

    for _ in range(20):

        for i in range(
            turn_in_elements.count()
        ):

            element = turn_in_elements.nth(i)

            if element.is_visible():

                visible_turn_in = element

                break

        if visible_turn_in:

            break

        page.wait_for_timeout(
            500
        )

    if visible_turn_in is None:

        raise RuntimeError(
            "Could not find a visible Turn in element "
            "after waiting."
        )

    print(
        "Visible Turn in found."
    )

    turn_in_button = (
        visible_turn_in.locator("..")
    )

    print(
        "Clicking Turn in..."
    )

    turn_in_button.click()

    print(
        "Turn in confirmation opened."
    )
    page.wait_for_timeout(
        1000
    )

    confirmation_elements = page.get_by_text(
        "Turn in",
        exact=True
    )
    visible_confirmation = None

    for _ in range(20):

        for i in range(
            confirmation_elements.count()
        ):

            element = (
                confirmation_elements.nth(i)
            )

            if element.is_visible():

                visible_confirmation = element

        if visible_confirmation:

            break

        page.wait_for_timeout(
            500
        )

    if visible_confirmation is None:

        raise RuntimeError(
            "Could not find the Turn in confirmation."
        )

    print(
        "Confirmation Turn in found."
    )

    confirmation_button = (
        visible_confirmation.locator("..")
    )

    confirmation_button.click()

    print(
        "Assignment submitted successfully."
    )