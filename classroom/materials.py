def get_assignment_materials(assignment):

    materials = assignment.get("materials", [])

    files = []

    for material in materials:

        drive_wrapper = material.get("driveFile", {})
        drive_file = drive_wrapper.get("driveFile", {})

        if not drive_file:
            continue

        files.append({
            "file_id": drive_file.get("id"),
            "title": drive_file.get("title"),
            "alternate_link": drive_file.get("alternateLink"),
            "thumbnail_url": drive_file.get("thumbnailUrl"),
            "share_mode": drive_wrapper.get("shareMode"),
        })

    return files