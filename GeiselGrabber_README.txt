# GeiselGrabber Canvas Course Material Downloader

A Python script to help grab all your course files from Canvas before you lose access. You paid a lot of money for this course material. You should keep it.


## What it does

Downloads most of the files from your Canvas courses - PDFs, PowerPoints, Word docs, etc. It scans through Files, Modules, Assignments, Pages, Announcements, Syllabus, Discussions, and Quizzes to find anything downloadable.

Automatically downloading videos from Panopto or YouTube is beyond my abilities, but this *should* create an HTML file with all the video links it finds. If this works, you'll find this in the folder for each course. This will help you manually download those videos if you want to.


## What you will need

- Python 3+ 
- Chrome browser
- These packages: `selenium`, `webdriver-manager`, `requests`, `python-dateutil`


## Before you start

To do this GeiselGrabber thing, you will need to run python in a Terminal/Command Prompt window.
If you're not familiar with this, don't worry. It's easy and instructions are here:

**Mac users - Opening Terminal:**
Press `Cmd + Space` to open Spotlight Search, type "Terminal", and press Enter.
A window with a command line will open - this is where you'll type commands.

**Windows users - Opening Command Prompt:**
Press the Windows key, type "cmd" or "Command Prompt", and press Enter. A black window will open - this is where you'll type commands.


## Check if you have Python installed

Open Terminal and type:
python3 --version (Mac)
python --version (Windows)

If you see "command not found", download and install Python 3 from https://www.python.org/downloads/


## How to use GeiselGrabber

### For Mac users:

1. **Install Python packages**
Open Terminal (press Cmd+Space, type "Terminal", press Enter) and paste this command:
   pip3 install selenium webdriver-manager requests python-dateutil

   Press Enter and wait for it to finish. Leave the terminal window open (we'll need it).

2. **Download the script**: 
Save the `geisel_grabber_v6.py` file directly to your Desktop. This makes everything easier to find.

3. **Navigate to Desktop**: 
In Terminal, type:
   cd ~/Desktop
   
   Press Enter. This tells your computer to look on the Desktop for files.

4. **Run the script**: 
Type: 
   python3 geisel_grabber_v6.py

   Press Enter.

5. **Follow the prompts** 
   - Enter your Canvas URL (or just hit Enter for Dartmouth)
   - Chrome will open a new window - log in like you normally would. This window will be controlled by the GeiselGrabber software, so don't close it. Just leave it alone after logging into Canvas.
   - Back in the Terminal, choose to download from all courses or pick specific ones.
   - Wait while GeiselGrabber downloads everything. Just leave the Terminal window and Chrome window alone while they do their thing.

6. **Find your files**
When it's done, the downloaded files will be in a folder called `canvas_downloads` on your Desktop.

### For PC users:

1. **Install Python packages**
Open Command Prompt (press Windows key, type "cmd", press Enter) and paste this command:
   pip install selenium webdriver-manager requests python-dateutil

   Press Enter and wait for it to finish.

2. **Download the script**
Save the `geisel_grabber_v6.py` file directly to your Desktop.

3. **Navigate to Desktop**
In Command Prompt, type:
   cd %USERPROFILE%\Desktop

   Press Enter.

4. **Run the script**
Type:
   python geisel_grabber_v6.py

   Press Enter.

5. **Follow the prompts** 
   - Enter your Canvas URL (or just hit Enter for Dartmouth)
   - Chrome will open a new window - log in like you normally would. This window will be controlled by the GeiselGrabber software, so don't close it. Just leave it alone after logging into Canvas.
   - Back in the Terminal, choose to download from all courses or pick specific ones.
   - Wait while GeiselGrabber downloads everything. Just leave the Terminal window and Chrome window alone while they do their thing.

6. **Find your files**
When it's done, the downloaded files will be in a folder called `canvas_downloads` on your Desktop.
## What you get


Everything gets saved in a `canvas_downloads` folder, structured like this:

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
- **Rate limiting**: There are pauses and random delays built in to keep the Canvas servers happy, be good citizens, and not get blocked by anti-bot defenses
- **Video cataloging**: Makes an HTML page with Panopto/YouTube links for manual download.
- **File type issues**: The script tries to fix extensions and assign files the correct file types, but this is actually a hard problem to solve and it makes some mistakes. If you end up with files that are .bin files or are missing file types/extensions, these are probably .pdf or .pptx files. You should be able to manually change them to your best guess of the filetype suffixes, and then check if these files can open.

## Speed expectations

- Small course (50 files): ~5-10 minutes
- Medium course (200 files): ~15-30 minutes  
- Large course (500+ files): ~45-90 minutes

Way faster than clicking through everything manually, but it takes some time. You will have to leave your computer online and awake the whole time.

## If something breaks

### Mac users:

**Can't install packages?**
python3 -m pip install --upgrade pip
python3 -m pip install selenium webdriver-manager requests python-dateutil

**"python: command not found"?**
Use `python3` instead of `python` everywhere.

**Permission errors?**
Try:
pip3 install --user selenium webdriver-manager requests python-dateutil


**Chrome issues?** 
- Update Chrome: Go to Chrome menu → About Google Chrome
- Make sure Chrome is in your Applications folder

**"Certificate verify failed" error?**
Run this in Terminal:

/Applications/Python\ 3.*/Install\ Certificates.command
(Replace * with your Python version, like 3.11 or 3.12)

### PC users:

**Can't install packages?**

python -m pip install --upgrade pip
python -m pip install selenium webdriver-manager requests python-dateutil


**Chrome issues?**
Update Chrome: Go to Settings → About Chrome

**Login problems?**
Make sure you can normally access Canvas in a regular browser first.

## Important notes
- GeiselGrabber will only download things you already have access to
- Respects your school's policies. You're responsible for following them. I couldn't find any rules that prohibit automated downloaders.
- The GeiselGrabber Chrome window closes automatically when done

## Configuration
The script creates a `download_config.ini` file where you can tweak delays and other settings if needed. Default settings should work fine for most people.

## Technical stuff
Uses Selenium for browser automation, requests for actual downloading, and some file header analysis to fix extensions. Works on Windows, Mac, and Linux.

The script creates manifest files to track what's been downloaded, so you can safely interrupt and resume. It's pretty robust about handling Canvas's sometimes inconsistent file serving.
