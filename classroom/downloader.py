from pathlib import Path
import re
import time
import io

from googleapiclient.http import MediaIoBaseDownload

DOWNLOAD_ROOT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "classroom_materials"
)

MAX_RETRIES = 5

RETRY_DELAY = 2


def sanitize_filename(filename):


    filename = str(filename)

    filename = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        filename,
    )
    filename = filename.strip()

    filename = filename.rstrip(
        " ."
    )

    if not filename:

        filename = "downloaded_file"

    return filename

def download_drive_file(
    service,
    file_id,
    file_name,
):

    DOWNLOAD_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = sanitize_filename(
        file_name
    )

    destination = (
        DOWNLOAD_ROOT / safe_name
    )

    print(
        "\n[downloader] Downloading:"
    )

    print(
        f"    Original name: {file_name}"
    )

    print(
        f"    Safe name:     {safe_name}"
    )

    print(
        f"    Destination:   {destination}"
    )

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            request = service.files().get_media(
                fileId=file_id
            )

            file_buffer = io.BytesIO()

            downloader = MediaIoBaseDownload(
                file_buffer,
                request,
            )

            done = False

            while not done:

                _, done = downloader.next_chunk()

            file_buffer.seek(0)

            with destination.open(
                "wb"
            ) as file:

                file.write(
                    file_buffer.read()
                )

            if not destination.exists():

                raise IOError(
                    "Download completed but "
                    "destination file was not created."
                )

            print(
                "[downloader] Download successful:"
            )

            print(
                f"    {destination}"
            )

            return destination

        except Exception as error:

            last_error = error

            print(
                "[downloader] Download failed "
                f"(attempt {attempt}/"
                f"{MAX_RETRIES}): "
                f"{error}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )

    print(
        "[downloader] Download failed after "
        f"{MAX_RETRIES} attempts."
    )

    return None