# README.txt

## Canvas Course Material Downloader

A Python tool to help students archive course materials from Canvas LMS.
Tested with Dartmouth Canvas, but designed to work with any Canvas instance.

This script uses a real Chrome browser (via Selenium) for login and navigation, then switches to `requests` with your authenticated cookies to download files efficiently while respecting basic rate limits.

---

## CONTENTS

1. Features
2. Requirements
3. Installation
4. How it works (important)
5. Usage (step-by-step)
6. Where files are saved
7. Configuration (download\_config.ini)
8. File naming and duplicates
9. What gets downloaded (and what doesn’t)
10. Resuming, retries, and manifests
11. Panopto and other special content
12. Troubleshooting
13. Notes on ethics & account safety
14. Known limitations

---

1. FEATURES

---

* Manual login through a real Chrome window (2FA compatible).
* Scans major Canvas sections: Files, Modules, Assignments, Pages, Announcements, Syllabus, Discussions, Quizzes.
* Optional “deep scan” for subpages in Pages/Modules to catch embedded links.
* Authenticated downloads using session cookies pulled from Selenium into `requests`.
* Rate limiting with random delays, periodic breaks, and exponential backoff on errors.
* Robust de-duplication based on Canvas file IDs (not just filenames).
* Content-Type → file extension mapping to fix missing/incorrect extensions.
* Per-course manifest (`.download_manifest.json`) tracking downloaded, failed, and special content.
* Per-run summary (`download_summary.json`).
* Panopto/recording link collection (HTML index saved to the course folder).

---

2. REQUIREMENTS

---

* Python 3.9+ recommended
* Google Chrome installed
* OS: Windows, macOS, or Linux

Python packages:

* selenium
* webdriver-manager
* requests
* python-dateutil

Install with:
pip install selenium webdriver-manager requests python-dateutil

(Everything else used is from the Python standard library.)

---

3. INSTALLATION

---

* Save the script to a folder of your choice.
* Ensure Chrome is installed.
* Install the Python packages listed above.
* (Windows only) If webdriver-manager fails to fetch a driver, you can place a compatible `chromedriver.exe` next to the script (the script will try multiple methods automatically).

---

4. HOW IT WORKS (IMPORTANT)

---

* On startup, the script opens Chrome and navigates to your Canvas URL.
* You log in manually. The tool waits for you to confirm in the console.
* It first tries to list courses from `<canvas>/courses`. If that’s empty, it also checks the Dashboard.
* For each selected course, it scans multiple sections and collects:

  * Canvas file IDs (`/courses/{id}/files/{file_id}`) and direct file links (e.g., PDFs) embedded in pages.
* It filters out obvious UI/system files, then downloads the rest using `requests` with cookies pulled from the live browser.
* Files are saved under `canvas_downloads/<Course Name>/`.
* A per-course manifest records what was downloaded, and failures.
* The Chrome window is *left open* so your Canvas session remains valid for subsequent runs.

---

5. USAGE (STEP-BY-STEP)

---

1. Run the script:
   python your\_script\_name.py
2. When prompted, press Enter to use Dartmouth Canvas or paste your Canvas base URL.
3. The Chrome window opens. Log in normally (including any 2FA).
4. Return to the console and press Enter when logged in.
5. Choose:

   * (1) Download from ALL courses, or
   * (2) Select specific courses (you’ll be shown a numbered list).
6. The tool scans each course, lists how many new files it found, and begins downloading.
7. A summary is written to `canvas_downloads/download_summary.json`.
8. The browser remains open when the script finishes, so you can run it again without re-logging.

---

6. WHERE FILES ARE SAVED

---

Default root:
./canvas\_downloads/

Each course gets its own folder:
./canvas\_downloads/<Sanitized Course Name>/

Inside each course folder you’ll see:

* Actual downloaded files (PDF, PPTX, DOCX, etc.)
* `.download_manifest.json`  (tracking info)
* `panopto_videos.html`      (if Panopto links were found)

A global run summary is saved to:
./canvas\_downloads/download\_summary.json

---

7. CONFIGURATION (download\_config.ini)

---

On first run, the script creates:
./canvas\_downloads/download\_config.ini

Editable keys that currently take effect:

\[delays]

* min\_delay (default 3)
* max\_delay (default 10)

\[breaks]

* interval\_min (default 20)
* interval\_max (default 30)
* duration\_min (default 30)   # seconds
* duration\_max (default 90)

\[scanning]

* max\_session\_pages (default 50)     # reserved; not currently enforced everywhere
* max\_subpage\_depth (default 3)      # how deep to follow subpages in Pages/Modules

Notes:

* Additional keys are written under `[downloads]` (e.g., `max_retries`, `download_timeout`, `check_interval`), but the loader currently applies only the sections listed above. Future versions may use the rest directly.

---

8. FILE NAMING AND DUPLICATES

---

* The tool uses a `FileNameManager` that **sanitizes** names and **ties uniqueness to the Canvas file ID**.
* If two different files share the same original name, a short hash (derived from the file ID) is appended to avoid collisions.
* During download, the script also looks at:

  * `Content-Disposition` (server-suggested filename), and
  * `Content-Type` (to set/repair an extension).
* If no extension is detectable, the tool falls back to `.bin`.

Important nuance:

* When a server suggests a filename (`Content-Disposition`), the code will save with that name. In rare edge cases, two different Canvas items could advertise the same suggested filename; the second one might replace the first. The per-course manifest will still record the final filename actually saved.

---

9. WHAT GETS DOWNLOADED (AND WHAT DOESN’T)

---

Downloads:

* Canvas “Files”
* Documents linked from Modules, Pages, Assignments, Announcements, Discussions, Quizzes
* Recognized direct links to common file types (pdf, docx, pptx, xlsx, zip, images, etc.)

Filtered out:

* Obvious UI assets (icons, arrows, logos, etc.) detected by simple heuristics
* Pages that require manual interaction (e.g., Panopto’s protected streams)

Special handling:

* Panopto and other recording links are **collected** but not auto-downloaded. An HTML index is written to the course folder.

---

10. RESUMING, RETRIES, AND MANIFESTS

---

* The tool is *resumable*. Re-running will skip files already downloaded (verified by file ID and existence).
* Failures are tracked in `.download_manifest.json` under `failed_files` with a simple attempt counter.
  The script uses a small backoff and will try again on later runs (up to a max attempts threshold).
* If Canvas indicates a file has changed (by a “modified” timestamp the code can parse during scanning), it will be re-downloaded.

Files & logs to check:

* `./canvas_downloads/<Course>/.download_manifest.json`  → includes `files`, `failed_files`, `id_to_filename`
* `./canvas_downloads/download_summary.json`             → per-course totals and filenames saved this run

---

11. PANOPTO AND OTHER SPECIAL CONTENT

---

* Links that look like Panopto or “recording” resources are written to:
  ./canvas\_downloads/<Course>/panopto\_videos.html
* Open that file and download from Panopto directly with your institutional access.

---

12. TROUBLESHOOTING

---

**A) “Found 0 courses” / It looks on Dashboard but not Courses**

* The script first tries `<base>/courses` and falls back to the Dashboard.
* If you’re already logged-in *before starting the script*, your Canvas may redirect oddly. Logging out of Canvas in your regular browser, then running the script and logging in via the spawned Chrome, typically resolves it.

**B) 404 Not Found during download**

* Common when a file was removed or is restricted by permissions. The script records these in `failed_files`. You can retry later.

**C) “Multiple errors detected. Recovery break: XXs…”**

* This is normal. The rate limiter backs off briefly after consecutive errors to look less “botty” and to avoid lockouts.

**D) Summary says more files than you see on disk**

* Reasons include:

  * Some items are “special content” (e.g., Panopto) and not actual files.
  * Filtered UI/system assets won’t be saved.
  * Files are saved under *each course’s* folder—ensure you’re checking the right course directory.
  * Very rarely, a server-suggested name may overwrite another file with the same name. Check `.download_manifest.json` to confirm what was saved.

**E) ChromeDriver/driver initialization fails**

* Update Chrome (`chrome://settings/help`).
* Let `webdriver-manager` fetch the right driver automatically (default).
* If needed, download a matching driver manually and place `chromedriver` (or `chromedriver.exe`) next to the script.

**F) Extensions look wrong (.bin)**

* That means Canvas sent a generic `Content-Type` and no filename hint. Files should still open if you know the type. You can rename manually, or use a file-type “magic” detector (not included) to infer extensions post-download.

---

13. NOTES ON ETHICS & ACCOUNT SAFETY

---

* Use only with your own account and courses.
* Respect your institution’s Terms of Service and any data retention policies.
* The tool introduces randomized delays, periodic breaks, and exponential backoff to avoid hammering servers. You can tune these in `download_config.ini`.

---

14. KNOWN LIMITATIONS

---

* Canvas UI/HTML can vary between institutions; selectors are best-effort and may need tweaks.
* Some keys in `download_config.ini` are written for future use but not all are read back yet.
* “Deep scan” tries to follow subpages but will not click every dynamic component.
* Authenticated streaming/video platforms (e.g., Panopto) generally require manual downloads.
* If two different resources advertise the *same* server-provided name at download time, the second may overwrite the first. The manifest captures what actually ended up on disk.

---

## SUPPORT / EXTENSIONS

Ideas for extension:

* Add MIME “magic” detection to improve extensions when Canvas sends `application/octet-stream`.
* Enforce unique filenames even when `Content-Disposition` provides a duplicate name.
* Add per-course exclude lists or custom filters.

If you customize the code (selectors, filters, naming), keep the behavior documented here in sync so you’ll remember how your build works later.
