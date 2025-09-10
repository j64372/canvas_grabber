# GeiselGrabber Canvas Course Material Downloader

A Python script I wrote to help grab all your course files from Canvas before you lose access. You paid a lot of money for this course material. You should keep it.

## What it does

Downloads most of the files from your Canvas courses - PDFs, PowerPoints, Word docs, etc. It scans through Files, Modules, Assignments, Pages, Announcements, Syllabus, Discussions, and Quizzes to find anything downloadable.

Automatically downloading videos from Panopto or YouTube is beyond my abilities, but this will create an HTML file with all the video links it finds. You'll find this in the folder for each course. This should help you manually download those videos if you want to.

## What you need

- Python 3.7+ 
- Chrome browser
- These packages: `pip install selenium webdriver-manager requests python-dateutil`

## How to use it

### For Mac users:

1. **Install Python packages**: Open Terminal (press Cmd+Space, type "Terminal", press Enter) and paste this command:
   
   pip install selenium webdriver-manager requests python-dateutil
   
   Press Enter and wait for it to finish, and leave the terminal window open (we'll need it).

2. **Download the script**: Save the `canvas_grabber_v6.py` file directly to your Desktop. This makes everything easier to find.

3. **Navigate to Desktop**: In Terminal, type:
   
   cd Desktop
   
   Press Enter. This tells your computer to look on the Desktop for files.

4. **Run the script**: Type:
   
   python geisel_grabber_v6.py
   
   Press Enter.

5. **Follow the prompts**: 
   - Enter your Canvas URL (or just hit Enter for Dartmouth)
   - Chrome will open a new window - log in like you normally would. This window will be controlled by the GeiselGrabber software, so don't close it, just leave it alone after logging into Canvas.
   - Back in the Terminal, choose to download from all courses or pick specific ones
   - Wait while it downloads everything. Just leave the Terminal window and Chrome window alone while they do their thing.

6. **Find your files**: When it's done, you'll have a new folder called `canvas_downloads` on your Desktop with all your course files.

### For PC users:

1. **Install Python packages**: Open Command Prompt (press Windows key, type "cmd", press Enter) and paste this command:
   
   pip install selenium webdriver-manager requests python-dateutil
   
   Press Enter and wait for it to finish.

2. **Download the script**: Save the `canvas_grabber_v6.py` file directly to your Desktop.

3. **Navigate to Desktop**: In Command Prompt, type:
   
   cd Desktop
   
   Press Enter.

4. **Run the script**: Type:
   
   python canvas_grabber_v6.py
   
   Press Enter.

5. **Follow the prompts**: Same as Mac - enter your Canvas URL, log in when Chrome opens, choose your courses.

6. **Find your files**: Look for the `canvas_downloads` folder on your Desktop when it's finished.

## What you get

Everything gets saved in a `canvas_downloads` folder:


canvas_downloads/
├── Course Name 1/
│   ├── lecture_slides.pdf
│   ├── assignment_1.docx
│   ├── course_videos.html    # video links if found
│   └── some_file.pdf
├── Course Name 2/
└── download_summary.json


## Misc.

- **Resumes where it left off**: Run it again and it skips files you already have
- **Handles duplicates**: Won't overwrite files or create naming conflicts
- **Rate limiting**: Plays nice with Canvas servers (1-3 second delays between requests)
- **Video cataloging**: Makes an HTML page with Panopto/YouTube links for manual download
- **File type issues**: The script tries to fix extensions and assign files the correct file types, but this is actually a hard problem to solve and it makes some mistakes. If you end up with files that are .bin files or are missing file types/extensions, these are probably .pdf or .pptx files. You should be able to manually change them and check.

## Speed expectations

- Small course (50 files): ~5-10 minutes
- Medium course (200 files): ~15-30 minutes  
- Large course (500+ files): ~45-90 minutes

Way faster than clicking through everything manually.

## If something breaks

**Can't install packages?**

python -m pip install --upgrade pip
python -m pip install selenium webdriver-manager requests python-dateutil


**Chrome issues?** Update Chrome, the script auto-downloads the right driver.

**Login problems?** Make sure you can normally access Canvas in a regular browser first.

## Important notes

- Only downloads stuff you already have access to
- Respects your school's policies (you're responsible for following them, but I couldn't find any rules that prohibit automated downloaders)
- Browser closes automatically when done (I tried to get it to stay open, but this caused other bugs)

## Configuration

The script creates a `download_config.ini` file where you can tweak delays and other settings if needed. Default settings work fine for most people.

## Technical stuff

Uses Selenium for browser automation, requests for actual downloading, and some file header analysis to fix extensions. Works on Windows, Mac, and Linux.

The script creates manifest files to track what's been downloaded, so you can safely interrupt and resume. It's pretty robust about handling Canvas's sometimes inconsistent file serving.
