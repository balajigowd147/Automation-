from classroom.api import (
    get_classroom_service,
    get_courses,
    get_assignments,
    get_announcement_materials,
    get_course_materials,
)


STUDY_KEYWORDS = [
    "unit",
    "notes",
    "lecture",
    "chapter",
    "module",
    "lab",
    "material",
    "reference",
    "problems",
    "syllabus",
]


class ClassroomPoller:

    def __init__(self):
        self.service = get_classroom_service()
        self.seen_assignments = set()
        self.seen_materials = set()

    def fetch_assignments(self):

        assignments = []

        courses = get_courses(self.service)

        for course in courses:

            course_id = course.get("id")
            course_name = course.get(
                "name",
                "Unnamed Course",
            )

            if not course_id:
                continue

            coursework = get_assignments(
                self.service,
                course_id,
            )

            for assignment in coursework:

                assignment["_course_id"] = course_id
                assignment["_course_name"] = course_name

                assignments.append(assignment)

        return assignments

    def fetch_study_materials(self):
        materials = []

        courses = get_courses(self.service)

        for course in courses:

            course_id = course.get("id")
            course_name = course.get(
                "name",
                "Unnamed Course",
            )

            if not course_id:
                continue


            course_materials = get_course_materials(
                self.service,
                course_id,
            )

            for material in course_materials:

                material_title = material.get(
                    "title",
                    "",
                )

                attached = material.get(
                    "materials",
                    [],
                )

                for item in attached:

                    drive_wrapper = item.get(
                        "driveFile"
                    )

                    if not drive_wrapper:
                        continue

                    drive_file = drive_wrapper.get(
                        "driveFile",
                        {},
                    )

                    file_id = drive_file.get(
                        "id"
                    )

                    file_name = drive_file.get(
                        "title"
                    )

                    if not file_id or not file_name:
                        continue

                    if not self.is_study_material(
                        file_name
                    ):
                        continue

                    materials.append({
                        "title": material_title,
                        "file_id": file_id,
                        "file_name": file_name,
                        "source": "coursework_material",
                        "coursework_material_title": material_title,
                        "_course_id": course_id,
                        "_course_name": course_name,
                    })

            announcement_materials = (
                get_announcement_materials(
                    self.service,
                    course_id,
                )
            )

            for material in announcement_materials:

                file_name = material.get(
                    "file_name",
                    "",
                )

                if not self.is_study_material(
                    file_name
                ):
                    continue

                material["_course_id"] = course_id
                material["_course_name"] = course_name

                materials.append(
                    material
                )

        return materials

    @staticmethod
    def is_study_material(file_name):

        name = file_name.lower()

        return any(
            keyword in name
            for keyword in STUDY_KEYWORDS
        )

    def get_new_assignments(self):

        assignments = self.fetch_assignments()

        new_assignments = []

        for assignment in assignments:

            assignment_id = assignment.get(
                "id"
            )

            if not assignment_id:
                continue

            if assignment_id not in self.seen_assignments:

                self.seen_assignments.add(
                    assignment_id
                )

                new_assignments.append(
                    assignment
                )

        return new_assignments

    def get_new_study_materials(self):

        materials = self.fetch_study_materials()

        new_materials = []

        for material in materials:

            file_id = material.get(
                "file_id"
            )

            if not file_id:
                continue

            if file_id not in self.seen_materials:

                self.seen_materials.add(
                    file_id
                )

                new_materials.append(
                    material
                )

        return new_materials

    def get_new_items(self):

        new_items = []

        assignments = self.get_new_assignments()

        for assignment in assignments:

            assignment["type"] = "assignment"

            new_items.append(
                assignment
            )

        materials = self.get_new_study_materials()

        for material in materials:

            material["type"] = "study_material"

            new_items.append(
                material
            )

        return new_items