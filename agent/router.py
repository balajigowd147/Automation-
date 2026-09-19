from classroom.downloader import download_drive_file
from artifacts.file_reader import read_file
from artifacts.discovery import register_agent_file
from artifacts.registry import ArtifactRegistry
from artifacts.matcher import match_artifact
from qwen_summarizer import summarize_document
from classroom.api import get_drive_service


class ClassroomRouter:

    def __init__(self):
        self.drive_service = get_drive_service()
        self.registry = ArtifactRegistry()

    def route(self, item):

        item_type = item.get("type")

        if item_type == "study_material":
            return self.process_study_material(item)

        elif item_type == "assignment":
            return self.process_assignment(item)

        else:
            print(f"Unknown Classroom item type: {item_type}")
            return None

    def process_study_material(self, item):

        file_id = item.get("file_id")
        file_name = item.get("file_name")

        course_name = item.get(
            "_course_name",
            "Unknown Course",
        )
        print("Course:", course_name)
        print("File:", file_name)
        print("Drive ID:", file_id)

        if not file_id or not file_name:
            print("Missing file information.")
            return None

        print("\nDownloading material...")

        downloaded_path = download_drive_file(
            self.drive_service,
            file_id,
            file_name,
        )

        if not downloaded_path:
            print("Download failed.")
            return None

        print("Downloaded to:")
        print(downloaded_path)

        print("\nRegistering artifact...")

        artifact_id = register_agent_file(
            self.registry,
            downloaded_path,
            artifact_type="study_material",
            downloaded=True,
        )

        print("Artifact ID:", artifact_id)


        print("\nExtracting text...")

        text = read_file(
            downloaded_path,
            max_chars=None,
        )

        print(
            f"Extracted characters: {len(text)}"
        )

        if not text.strip():
            print("No text could be extracted.")
            return None

        print("\nSending material to Qwen...")

        summary = summarize_document(text)

        print(summary)


        return {
            "type": "study_material",
            "file_name": file_name,
            "file_id": file_id,
            "path": str(downloaded_path),
            "artifact_id": artifact_id,
            "summary": summary,
        }

    def process_assignment(self, item):

        course_name = item.get(
            "_course_name",
            "Unknown Course",
        )

        title = item.get("title")
        assignment_id = item.get("id")
        description = item.get("description", "")


        print("Course:", course_name)
        print("Title:", title)
        print("Assignment ID:", assignment_id)
        requirement = {
            "name": title,
            "evidence": description,
            "artifact_type": "unknown",
        }

        print("\n[router] Artifact requirement:")
        print("    Name:", requirement["name"])
        print("    Evidence:", requirement["evidence"])
        print("    Artifact type:", requirement["artifact_type"])

        print("\n[router] Searching for matching artifact...")

        match = match_artifact(
            requirement,
            self.registry,
        )

        if not match:
            print("\n[router] No matching artifact found.")

            return {
                "type": "assignment",
                "assignment_id": assignment_id,
                "title": title,
                "artifact": None,
            }

        artifact = match["artifact"]

        print("Artifact ID:", artifact["id"])
        print("File:", artifact["name"])
        print("Type:", artifact["artifact_type"])
        print("Path:", artifact["path"])
        print("Confidence:", match["confidence"])
        print("Reason:", match["reason"])

        return {
            "type": "assignment",
            "assignment_id": assignment_id,
            "title": title,
            "artifact": {
                "id": artifact["id"],
                "name": artifact["name"],
                "path": artifact["path"],
                "artifact_type": artifact["artifact_type"],
            },
            "confidence": match["confidence"],
            "reason": match["reason"],
        }