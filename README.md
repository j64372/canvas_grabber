# Canvas Course Downloader - README

## Overview
This tool helps students download their course materials from Canvas LMS using their legitimate login credentials. It automates the process of saving files, documents, and course content for offline access or archival purposes.

## Prerequisites

### Required Software
1. **Python 3.7 or higher**
   - Download from: https://www.python.org/downloads/
   - During installation, CHECK "Add Python to PATH"

2. **Google Chrome Browser**
   - Must be installed and up-to-date
   - Download from: https://www.google.com/chrome/

## Installation

1. Save the script as `canvas_grabber.py` in a folder of your choice
2. Open Command Prompt (Windows) or Terminal (Mac/Linux)
3. Navigate to the folder containing the script:
   ```
   cd path/to/your/folder
   ```
4. Install dependencies (if not already done):
   
   Windows:
   Install required libraries by running:
   ```
   pip install selenium webdriver-manager requests python-dateutil
   ```

   MacOS:
   Install required libraries by running:
   ```
   pip install selenium webdriver-manager requests python-dateutil
   # or pip3 if you have both Python 2 and 3
   ```

## Running the Script

### Basic Usage
1. Open Command Prompt/Terminal
2. Navigate to the script directory
3. Run:
   ```
   python canvas_grabber.py
   ```

### Step-by-Step Process
1. **Start the script** - It will open a Chrome browser window
2. **Enter Canvas URL** - Press Enter for Dartmouth or enter your institution's Canvas URL
3. **Login** - The script will navigate to the login page
   - Enter your username/email and password
   - Complete any 2FA/multi-factor authentication
   - Wait for the Canvas dashboard to load
   - Press Enter in the terminal once logged in
4. **Select courses** - Choose to download all courses or select specific ones
5. **Wait for completion** - The script will download all materials

### Important: Keep Browser Open
- The browser window will remain open after completion
- This maintains your session for subsequent runs
- Close manually when completely finished

## Features

### Smart Download Management
- **Duplicate Detection**: Automatically skips files already downloaded
- **Resume Capability**: Can stop and restart without losing progress
- **Download Verification**: Confirms files downloaded successfully
- **Unique Naming**: Prevents filename conflicts automatically

### Rate Limiting & Politeness
- Configurable delays between requests (see `download_config.ini`)
- Automatic backoff on errors
- Periodic breaks to avoid overloading servers

### Organization
- Creates separate folders for each course
- Maintains download manifest (`.download_manifest.json`) to track progress
- Generates summary report (`download_summary.json`)

## Configuration

After first run, edit `canvas_downloads/download_config.ini` to adjust:
- `min_delay`: Minimum seconds between requests (default: 3)
- `max_delay`: Maximum seconds between requests (default: 10)
- Break intervals and durations
- Download timeouts and retry attempts

## File Locations

```
canvas_downloads/
├── download_config.ini          # Configuration file
├── download_summary.json        # Summary of all downloads
├── Course_Name_1/
│   ├── .download_manifest.json  # Tracks downloaded files
│   ├── lecture1.pdf
│   ├── assignment.docx
│   └── ...
└── Course_Name_2/
    └── ...
```

## Troubleshooting

### ChromeDriver Issues (Windows)
If you see "Service chromedriver.exe unexpectedly exited":
1. Update Chrome to the latest version
2. Run the script as Administrator (right-click → Run as administrator)
3. Delete the `.wdm` folder in your user directory: `C:\Users\[username]\.wdm`
4. Temporarily disable antivirus software
5. The script will automatically retry 3 times

### Login Issues
- Some institutions use SSO/SAML authentication
- Complete all login steps including 2FA
- Wait for the Canvas dashboard to fully load before pressing Enter

### Download Failures
- Check the `.download_manifest.json` file for failed downloads
- The script will retry failed downloads up to 3 times
- Run the script again to retry any remaining failed downloads

### Rate Limiting
If Canvas blocks requests:
- Increase delays in `download_config.ini`
- Take longer breaks between courses
- Run the script during off-peak hours

## Important Notes

### Acceptable Use
- This tool is for downloading YOUR OWN course materials
- Use only with your legitimate student credentials
- Respect your institution's acceptable use policies
- Do not share downloaded materials inappropriately

### Performance Tips
- First run will take longest (downloading all files)
- Subsequent runs only download new/updated files
- Can safely interrupt (Ctrl+C) and resume later
- Consider running overnight for large courses

### Limitations
- Cannot download certain dynamic content
- Video content from external platforms (Panopto, Zoom) requires manual download
- Some embedded content may not be accessible

## Support

### Before Running
1. Ensure Chrome is updated
2. Check you can manually log into Canvas
3. Verify you have proper permissions for course content

### Common Issues
- **"No courses found"**: Check if courses are visible on Canvas dashboard
- **Files not downloading**: Verify download folder permissions
- **Script hangs**: Canvas may be slow; wait or restart

### Getting Help
When reporting issues, include:
- Your operating system (Windows/Mac/Linux)
- Python version (`python --version`)
- Chrome version (Help → About Google Chrome)
- Error messages from the terminal
- Contents of `download_config.ini`

## Privacy & Security

- Your credentials are never stored by the script
- Downloads stay local on your computer
- The browser session is isolated to the script
- Close the browser window to end the session

## Version Information
- Script Version: Enhanced Edition with duplicate detection
- Compatible with: Canvas LMS (most versions)
- Tested on: Windows 10/11, macOS, Ubuntu Linux

---

Remember: This tool is provided to help students preserve their educational materials. Always respect copyright, your institution's policies, and your instructors' intellectual property rights.
