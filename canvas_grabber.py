#!/usr/bin/env python3
"""
Canvas Course Material Downloader
A tool for students to archive their course materials from Canvas LMS
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time, os, re, json, platform, logging, random, requests, hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
from dateutil.parser import parse as parse_date
import configparser

class DownloadConfig:
    """Configurable settings for download behavior"""
    def __init__(self, config_file=None):
        self.min_delay = 3  # Minimum seconds between requests
        self.max_delay = 10  # Maximum seconds between requests
        self.break_interval = (20, 30)  # Take break every N requests (min, max)
        self.break_duration = (30, 90)  # Break duration in seconds (min, max)
        self.course_break_duration = (60, 180)  # Break between courses (min, max)
        self.max_retries = 3
        self.download_timeout = 60  # Seconds to wait for download completion
        self.check_interval = 2  # How often to check for download completion
        self.max_session_pages = 50  # Maximum session/lecture pages to scan per course
        self.max_subpage_depth = 3  # How deep to scan subpages
        
        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)
    
    def load_from_file(self, config_file):
        """Load configuration from INI file"""
        config = configparser.ConfigParser()
        config.read(config_file)
        
        if 'delays' in config:
            self.min_delay = config.getint('delays', 'min_delay', fallback=self.min_delay)
            self.max_delay = config.getint('delays', 'max_delay', fallback=self.max_delay)
        
        if 'breaks' in config:
            self.break_interval = (
                config.getint('breaks', 'interval_min', fallback=self.break_interval[0]),
                config.getint('breaks', 'interval_max', fallback=self.break_interval[1])
            )
            self.break_duration = (
                config.getint('breaks', 'duration_min', fallback=self.break_duration[0]),
                config.getint('breaks', 'duration_max', fallback=self.break_duration[1])
            )
        
        if 'scanning' in config:
            self.max_session_pages = config.getint('scanning', 'max_session_pages', fallback=self.max_session_pages)
            self.max_subpage_depth = config.getint('scanning', 'max_subpage_depth', fallback=self.max_subpage_depth)
    
    def save_to_file(self, config_file):
        """Save current configuration to INI file"""
        config = configparser.ConfigParser()
        config['delays'] = {
            'min_delay': str(self.min_delay),
            'max_delay': str(self.max_delay)
        }
        config['breaks'] = {
            'interval_min': str(self.break_interval[0]),
            'interval_max': str(self.break_interval[1]),
            'duration_min': str(self.break_duration[0]),
            'duration_max': str(self.break_duration[1])
        }
        config['downloads'] = {
            'max_retries': str(self.max_retries),
            'download_timeout': str(self.download_timeout),
            'check_interval': str(self.check_interval)
        }
        config['scanning'] = {
            'max_session_pages': str(self.max_session_pages),
            'max_subpage_depth': str(self.max_subpage_depth)
        }
        
        with open(config_file, 'w') as f:
            config.write(f)

class DownloadTracker:
    """Track downloaded files to avoid duplicates"""
    def __init__(self, course_folder):
        self.course_folder = Path(course_folder)
        self.manifest_file = self.course_folder / ".download_manifest.json"
        self.manifest = self.load_manifest()
        self.session_downloads = []  # Track downloads in this session
    
    def load_manifest(self):
        """Load existing download manifest"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return self.create_empty_manifest()
        return self.create_empty_manifest()
    
    def create_empty_manifest(self):
        """Create empty manifest structure"""
        return {
            'last_updated': None,
            'files': {},
            'failed_files': {},
            'course_content': {},
            'special_content': {}  # For Panopto, discussion posts, etc.
        }
    
    def save_manifest(self):
        """Save manifest to disk"""
        self.manifest['last_updated'] = datetime.now().isoformat()
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def is_downloaded(self, file_id, file_info=None):
        """Check if file has been successfully downloaded"""
        # Check by file ID
        if str(file_id) in self.manifest['files']:
            file_record = self.manifest['files'][str(file_id)]
            filepath = Path(self.course_folder / file_record['filename'])
            
            # Verify file still exists and has content
            if filepath.exists() and filepath.stat().st_size > 0:
                # Check if file info has changed (with proper datetime parsing)
                if file_info and 'modified' in file_info:
                    try:
                        modified_dt = parse_date(file_info['modified'])
                        downloaded_dt = parse_date(file_record.get('downloaded_at', ''))
                        if modified_dt > downloaded_dt:
                            return False  # File has been updated, re-download
                    except Exception:
                        # If parsing fails, treat as unchanged
                        pass
                return True
            else:
                # File was tracked but doesn't exist, remove from manifest
                del self.manifest['files'][str(file_id)]
                return False
        
        return False
    
    def mark_downloaded(self, file_id, filename, metadata=None):
        """Mark file as successfully downloaded"""
        self.manifest['files'][str(file_id)] = {
            'filename': filename,
            'downloaded_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.session_downloads.append(filename)
        self.save_manifest()
    
    def mark_special_content(self, content_type, content_data):
        """Track special content like Panopto videos, discussions, etc."""
        if content_type not in self.manifest['special_content']:
            self.manifest['special_content'][content_type] = []
        
        self.manifest['special_content'][content_type].append({
            'data': content_data,
            'found_at': datetime.now().isoformat()
        })
        self.save_manifest()
    
    def mark_failed(self, file_id, filename, error_msg):
        """Track failed downloads"""
        self.manifest['failed_files'][str(file_id)] = {
            'filename': filename,
            'last_attempt': datetime.now().isoformat(),
            'error': str(error_msg),
            'attempts': self.manifest['failed_files'].get(str(file_id), {}).get('attempts', 0) + 1
        }
        self.save_manifest()
    
    def should_retry_failed(self, file_id, max_attempts=3):
        """Check if we should retry a previously failed download"""
        if str(file_id) in self.manifest['failed_files']:
            attempts = self.manifest['failed_files'][str(file_id)].get('attempts', 0)
            return attempts < max_attempts
        return True
    
    def get_stats(self):
        """Get download statistics"""
        return {
            'total_downloaded': len(self.manifest['files']),
            'session_downloads': len(self.session_downloads),
            'failed_files': len(self.manifest['failed_files']),
            'special_content': {k: len(v) for k, v in self.manifest.get('special_content', {}).items()},
            'last_updated': self.manifest.get('last_updated', 'Never')
        }

class RateLimiter:
    """Rate limiting with configurable delays"""
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.request_count = 0
        self.last_request_time = 0
        self.consecutive_errors = 0
        self.backoff_multiplier = 1.0
        self.next_break_interval = random.randint(*self.config.break_interval)
    
    def get_delay(self):
        """Calculate delay with current backoff"""
        base_delay = random.uniform(self.config.min_delay, self.config.max_delay)
        return base_delay * self.backoff_multiplier
    
    def wait(self):
        """Wait with appropriate delay"""
        self.request_count += 1
        
        # Take periodic breaks
        if self.request_count % self.next_break_interval == 0:
            break_time = random.uniform(*self.config.break_duration)
            print(f"   Taking a break ({break_time:.0f}s) after {self.request_count} requests...")
            time.sleep(break_time)
            # Reset backoff after break and pick next break interval
            self.backoff_multiplier = max(1.0, self.backoff_multiplier * 0.5)
            self.next_break_interval = random.randint(*self.config.break_interval)
        
        # Regular delay
        delay = self.get_delay()
        time_since_last = time.time() - self.last_request_time
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def report_error(self):
        """Report an error and increase backoff"""
        self.consecutive_errors += 1
        self.backoff_multiplier = min(self.backoff_multiplier * 1.5, 10.0)
        
        if self.consecutive_errors >= 3:
            # Take a longer break after multiple errors
            recovery_time = random.uniform(60, 120)
            print(f"   Multiple errors detected. Recovery break: {recovery_time:.0f}s...")
            time.sleep(recovery_time)
            self.consecutive_errors = 0
    
    def report_success(self):
        """Report successful request and potentially reduce backoff"""
        self.consecutive_errors = 0
        if random.random() < 0.1:  # 10% chance to reduce
            self.backoff_multiplier = max(self.backoff_multiplier * 0.9, 1.0)

class FileNameManager:
    """Handle file naming with collision prevention"""
    def __init__(self, course_folder):
        self.course_folder = Path(course_folder)
        self.name_cache = {}
        self.used_names = set()
        self._scan_existing_files()
    
    def _scan_existing_files(self):
        """Scan folder for existing files to avoid collisions"""
        if self.course_folder.exists():
            for file in self.course_folder.rglob('*'):
                if file.is_file():
                    self.used_names.add(file.name)
    
    def get_unique_filename(self, original_name, file_id=None):
        """Generate unique filename, avoiding collisions"""
        # Sanitize the original name
        safe_name = FileNameManager.sanitize_filename(original_name)
        
        # If we've seen this file_id before, return the cached name
        if file_id and file_id in self.name_cache:
            return self.name_cache[file_id]
        
        # Extract name and extension
        if '.' in safe_name:
            base_name, extension = safe_name.rsplit('.', 1)
            extension = '.' + extension
        else:
            base_name = safe_name
            extension = ''
        
        # Find unique name
        final_name = safe_name
        counter = 1
        
        while final_name in self.used_names:
            # Add hash for file_id if available, otherwise use counter
            if file_id:
                # Use first 6 chars of hash for brevity
                hash_suffix = hashlib.md5(str(file_id).encode()).hexdigest()[:6]
                final_name = f"{base_name}_{hash_suffix}{extension}"
            else:
                final_name = f"{base_name}_{counter}{extension}"
            counter += 1
            
            # Prevent infinite loop
            if counter > 100:
                # Use timestamp as last resort
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                final_name = f"{base_name}_{timestamp}{extension}"
                break
        
        # Cache and track the name
        self.used_names.add(final_name)
        if file_id:
            self.name_cache[file_id] = final_name
        
        return final_name
    
    def sanitize_filename(filename):
        """Sanitize filename for filesystem"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*\n\r\t'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove multiple underscores
        while '__' in filename:
            filename = filename.replace('__', '_')
        
        # Limit length (leave room for potential suffixes)
        max_length = 200  # Most filesystems support 255
        if len(filename) > max_length:
            # Preserve extension if present
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                filename = name[:max_length - len(ext) - 1] + '.' + ext
            else:
                filename = filename[:max_length]
        
        return filename.strip('_').strip() or 'unnamed_file'

class CanvasDownloader:
    def __init__(self, canvas_url, download_folder="canvas_downloads", config_file=None):
        self.canvas_url = canvas_url.rstrip('/')
        self.download_folder = Path(download_folder)
        self.download_folder.mkdir(exist_ok=True)
        self.driver = None
        self.wait = None
        
        # Initialize configuration
        self.config = DownloadConfig(config_file)
        
        # Initialize components
        self.rate_limiter = RateLimiter(self.config)
        
        # Save default config if no config file exists
        config_path = self.download_folder / "download_config.ini"
        if not config_path.exists():
            self.config.save_to_file(config_path)
            print(f"Created configuration file: {config_path}")
        
    def setup_driver(self):
        chrome_options = Options()
        
        # Browser configuration options
        browser_args = [
            "--log-level=3", "--silent", "--disable-logging", "--disable-gpu", 
            "--disable-software-rasterizer", "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions", "--no-first-run", "--disable-default-apps",
            "--disable-popup-blocking", "--disable-infobars", "--disable-notifications",
            "--disable-save-password-bubble"
        ]
        
        for arg in browser_args:
            chrome_options.add_argument(arg)
            
        # User agent configuration
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        chrome_options.add_argument(f"--user-agent={user_agent}")
        chrome_options.add_argument("--window-size=1920,1080")
        
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("detach", True)
        
        if platform.system() == "Windows":
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-gpu-sandbox")
        elif platform.system() == "Darwin":
            chrome_options.add_argument("--no-sandbox")
        
        download_path = str(self.download_folder.absolute())
        if platform.system() == "Windows":
            download_path = download_path.replace('/', '\\')
        
        prefs = {
            "download.default_directory": download_path,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.notifications": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        logging.getLogger('WDM').setLevel(logging.NOTSET)
        os.environ['WDM_LOG'] = "false"
        
        # Driver initialization with multiple fallback methods
        driver_initialized = False
        
        # Method 1: Try with webdriver-manager (but don't clear cache every time)
        if not driver_initialized:
            try:
                print("  Initializing Chrome driver...")
                driver_path = ChromeDriverManager().install()
                
                if platform.system() == "Windows":
                    driver_path = driver_path.replace('/', '\\')
                
                service = Service(driver_path)
                if platform.system() == "Windows":
                    service.creation_flags = 0
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                driver_initialized = True
                print(f"  Chrome driver initialized successfully")
                
            except Exception as e:
                print(f"  Auto-download method failed: {str(e)[:100]}")
        
        # Method 2: Try without specifying driver path
        if not driver_initialized:
            try:
                print("  Attempting Chrome driver from PATH...")
                self.driver = webdriver.Chrome(options=chrome_options)
                driver_initialized = True
                print(f"  Chrome driver initialized from PATH")
            except Exception as e:
                print(f"  PATH method failed: {str(e)[:50]}")
        
        # Method 3: Look for manually placed chromedriver
        if not driver_initialized:
            try:
                print("  Looking for manually placed chromedriver...")
                
                possible_paths = [
                    Path.cwd() / "chromedriver.exe",
                    Path.cwd() / "chromedriver",
                    Path.home() / "Downloads" / "chromedriver.exe",
                ]
                
                for driver_path in possible_paths:
                    if driver_path.exists():
                        print(f"  Found chromedriver at: {driver_path}")
                        service = Service(str(driver_path))
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        driver_initialized = True
                        print(f"  Chrome driver initialized from manual placement")
                        break
                    
            except Exception as e:
                print(f"  Manual placement method failed: {str(e)[:50]}")
        
        if not driver_initialized:
            print(f"\nFailed to initialize Chrome driver")
            print("\nTROUBLESHOOTING:")
            print("1. Update Chrome: chrome://settings/help")
            print("2. Download matching ChromeDriver:")
            print("   https://googlechromelabs.github.io/chrome-for-testing/")
            print("3. Extract chromedriver.exe to script folder")
            print("4. Run script again")
            
            raise Exception("Chrome driver initialization failed.")
        
        self.wait = WebDriverWait(self.driver, 10)
        
        print(f"Downloads will be saved to: {self.download_folder.absolute()}")
        print("Browser will remain open to maintain Canvas session")
    
    def _session_from_driver(self):
        """Create a requests.Session() populated with cookies from Selenium driver."""
        s = requests.Session()
        for c in self.driver.get_cookies():
            s.cookies.set(c['name'], c['value'], domain=c.get('domain'))
        # Set headers
        s.headers.update({
            'Referer': self.canvas_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        })
        return s
    
    def download_with_requests(self, url, dest_path, max_retries=3, timeout=60):
        """Stream-download the URL using requests and Selenium cookies; write to dest_path."""
        session = self._session_from_driver()
        
        for attempt in range(max_retries):
            try:
                self.rate_limiter.wait()
                
                with session.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
                    r.raise_for_status()
                    
                    # Try to get filename from content-disposition header
                    cd = r.headers.get('content-disposition', '')
                    if 'filename=' in cd:
                        # Extract filename
                        fname_match = re.findall(r'filename\*?=(?:UTF-8\'\')?["\']?([^;\r\n"\' ]+)', cd)
                        if fname_match:
                            # Use server-suggested filename but sanitize it
                            suggested_name = FileNameManager.sanitize_filename(fname_match[0])
                            dest_path = Path(dest_path).parent / suggested_name
                    
                    # Write file
                    with open(dest_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                
                self.rate_limiter.report_success()
                return str(dest_path)
                
            except Exception as e:
                self.rate_limiter.report_error()
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise
    
    def navigate_with_rate_limit(self, url, context="page"):
        """Navigate to URL with rate limiting"""
        print(f"   Navigating to {context}...")
        self.rate_limiter.wait()
        
        try:
            self.driver.get(url)
            self.wait_for_content_load()
            self.rate_limiter.report_success()
            return True
        except Exception as e:
            print(f"   Navigation failed: {e}")
            self.rate_limiter.report_error()
            return False

    def login(self):
        print("Navigating to Canvas login...")
        try:
            print("Opening Canvas main page...")
            self.navigate_with_rate_limit(self.canvas_url, "Canvas main page")
            
            if self.is_logged_in():
                print("Already logged in from previous session!")
                return True
            
            login_found = False
            try:
                login_selectors = ["a[href*='login']", "button[class*='login']", ".login-btn",
                                 "#login", "a[class*='Log']", "a[href*='saml']", "a[href*='sso']"]
                for selector in login_selectors:
                    login_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if login_elements:
                        print(f"Found login element, clicking...")
                        time.sleep(random.uniform(0.5, 1.5))
                        login_elements[0].click()
                        time.sleep(random.uniform(2, 4))
                        login_found = True
                        break
            except Exception as e:
                print(f"Error finding login button: {e}")
            
            if not login_found:
                print("No login button found, trying direct login URLs...")
                fallback_urls = [f"{self.canvas_url}/login", f"{self.canvas_url}/login/canvas", 
                               f"{self.canvas_url}/login/saml", f"{self.canvas_url}/auth/saml"]
                for url in fallback_urls:
                    try:
                        print(f"Trying: {url}")
                        self.navigate_with_rate_limit(url, "login page")
                        if "login" in self.driver.page_source.lower():
                            print("Found login page!")
                            break
                    except Exception:
                        continue
            
            print("\n" + "="*70)
            print("MANUAL LOGIN REQUIRED")
            print("="*70)
            print("Canvas should now be loaded in the browser window.")
            print("\nPlease complete login:")
            print("1. Click 'Login' or your institution's login button")
            print("2. Enter your username/student ID and password") 
            print("3. Complete any 2FA/multi-factor authentication")
            print("4. Wait for Canvas dashboard to load")
            print("5. Verify you can see your courses")
            print("\nThen return here and press Enter to continue...")
            print("="*70)
            
            input("Press Enter when you've successfully logged in: ")
            
            if self.is_logged_in():
                print("Login successful!")
                return True
            else:
                print("Login verification inconclusive, but continuing...")
                return True
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def is_logged_in(self):
        try:
            current_url = self.driver.current_url.lower()
            if any(indicator in current_url for indicator in ['dashboard', 'courses', 'profile']):
                return True
            page_source = self.driver.page_source.lower()
            logged_in_indicators = ['dashboard', 'my courses', 'course list', 'logout', 'profile menu']
            login_indicators = ['sign in', 'log in', 'username', 'password', 'netid login']
            has_logged_in_content = any(indicator in page_source for indicator in logged_in_indicators)
            has_login_content = any(indicator in page_source for indicator in login_indicators)
            return has_logged_in_content and not has_login_content
        except Exception:
            return False
    
    def wait_for_content_load(self, timeout=10):
        try:
            self.wait.until(EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, ".loading-indicator, .spinner, .ui-loading")))
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#content, .course-content, main")))
        except TimeoutException:
            pass
            
    def get_courses(self):
        print("Fetching course list...")
        self.navigate_with_rate_limit(f"{self.canvas_url}/courses", "courses list")
        courses = []
        
        try:
            # Try standard course list
            course_elements = self.driver.find_elements(By.CSS_SELECTOR, ".course-list-table-row")
            for element in course_elements:
                try:
                    link = element.find_element(By.CSS_SELECTOR, "a")
                    course_name = link.text.strip()
                    course_url = link.get_attribute("href")
                    if course_name and course_url:
                        courses.append({"name": course_name, "url": course_url})
                except Exception:
                    continue
            
            # Also check dashboard cards
            if not courses:
                print("Checking dashboard for courses...")
                self.navigate_with_rate_limit(f"{self.canvas_url}/", "dashboard")
                course_elements = self.driver.find_elements(By.CSS_SELECTOR, ".ic-DashboardCard__link")
                for element in course_elements:
                    course_name = element.get_attribute("aria-label")
                    course_url = element.get_attribute("href")
                    if course_name and course_url:
                        courses.append({"name": course_name, "url": course_url})
                        
        except NoSuchElementException:
            print("Could not find courses using standard methods")
        
        print(f"Found {len(courses)} courses")
        return courses
    
    def extract_file_ids_from_content(self, course_url, tracker: DownloadTracker, course_folder):
        print(f"  Scanning course content for files...")
        file_info = {}
        
        # Check for special content first
        self.check_special_content(course_url, tracker, course_folder)
        
        print(f"    Scanning course home page...")
        self.navigate_with_rate_limit(course_url, "course home")
        
        # Scan all major sections
        sections = [
            ("/files", "Files"),
            ("/modules", "Modules"), 
            ("/assignments", "Assignments"),
            ("/pages", "Pages"),
            ("/announcements", "Announcements"),
            ("/assignments/syllabus", "Syllabus"),
            ("/discussion_topics", "Discussions"),
            ("/quizzes", "Quizzes")
        ]
        
        for section_path, section_name in sections:
            section_url = f"{course_url}{section_path}"
            print(f"    Scanning {section_name}...")
            try:
                self.navigate_with_rate_limit(section_url, f"{section_name} section")
                
                if "login" in self.driver.current_url.lower():
                    print(f"      Section not accessible")
                    continue
                
                page_source = self.driver.page_source
                section_files = self.extract_file_ids_and_links_from_html(page_source, section_path)
                
                # Filter out already downloaded files
                new_files = {}
                skipped_count = 0
                for file_id, info in section_files.items():
                    if not tracker.is_downloaded(file_id, info):
                        new_files[file_id] = info
                    else:
                        skipped_count += 1
                
                if new_files:
                    print(f"      Found {len(new_files)} new files ({skipped_count} already downloaded)")
                    file_info.update(new_files)
                elif skipped_count > 0:
                    print(f"      All {skipped_count} files already downloaded")
                
                # Deep scan for pages and modules
                if section_path in ["/pages", "/modules"]:
                    subpage_files = self.scan_section_deeply(course_url, section_path, tracker, depth=0)
                    if subpage_files:
                        file_info.update(subpage_files)
                    
            except Exception as e:
                print(f"      Error scanning {section_name}: {e}")
                continue
            
            # Brief break between sections
            time.sleep(random.uniform(2, 5))
        
        valuable_files = self.filter_valuable_files(file_info)
        print(f"  Total new files found: {len(valuable_files)}")
        return valuable_files
    
    def scan_section_deeply(self, course_url, section_path, tracker, depth=0):
        """Recursively scan sections for embedded content"""
        if depth >= self.config.max_subpage_depth:
            return {}
        
        file_info = {}
        
        try:
            # Find all links in current section
            links = self.driver.find_elements(By.TAG_NAME, "a")
            subpage_links = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    if href and text and course_url in href:
                        # Check if it's a content page (not a file)
                        if not any(ext in href.lower() for ext in ['.pdf', '.ppt', '.doc', '.xls', '.zip', '/files/']):
                            if section_path in href:  # Stay within section
                                subpage_links.append({'url': href, 'title': text})
                except Exception:
                    continue
            
            if subpage_links:
                print(f"        Found {len(subpage_links)} subpages to scan (depth {depth+1})...")
                current_url = self.driver.current_url
                
                # Limit number of subpages to scan
                random.shuffle(subpage_links)
                limited_subpages = subpage_links[:min(20, len(subpage_links))]
                
                for subpage in limited_subpages:
                    try:
                        print(f"          Scanning: {subpage['title'][:50]}...")
                        self.navigate_with_rate_limit(subpage['url'], f"subpage")
                        
                        if "login" not in self.driver.current_url.lower():
                            page_source = self.driver.page_source
                            subpage_files = self.extract_file_ids_and_links_from_html(
                                page_source, f"{section_path}_sub"
                            )
                            
                            # Filter already downloaded
                            new_files = {k: v for k, v in subpage_files.items() 
                                       if not tracker.is_downloaded(k, v)}
                            
                            if new_files:
                                print(f"            Found {len(new_files)} new files")
                                file_info.update(new_files)
                            
                            # Recursively scan deeper
                            deeper_files = self.scan_section_deeply(
                                course_url, section_path, tracker, depth+1
                            )
                            if deeper_files:
                                file_info.update(deeper_files)
                    except Exception:
                        continue
                
                # Return to original section
                self.navigate_with_rate_limit(current_url, "return to section")
                
        except Exception as e:
            print(f"        Error in deep scan: {e}")
        
        return file_info
    
    def check_special_content(self, course_url, tracker: DownloadTracker, course_folder):
        """Check for special content like Panopto videos, Zoom recordings, etc."""
        try:
            # Navigate to course home
            self.navigate_with_rate_limit(course_url, "course home")
            
            # Look for Panopto videos
            panopto_links = []
            video_links = []
            
            # Find all links that might be videos
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    
                    if 'panopto' in href.lower() or 'panopto' in text.lower():
                        panopto_links.append({'url': href, 'title': text})
                    elif any(vid in href.lower() for vid in ['zoom', 'video', 'recording', 'lecture capture']):
                        video_links.append({'url': href, 'title': text})
                except Exception:
                    continue
            
            if panopto_links:
                print(f"    Found {len(panopto_links)} Panopto video links")
                
                # Save Panopto links to HTML file in the correct course folder
                panopto_file = course_folder / "panopto_videos.html"
                panopto_file.parent.mkdir(exist_ok=True)
                
                html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Panopto Videos - Course Content</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; }
        h1 { color: #333; }
        .video-link { display: block; padding: 10px; margin: 10px 0; background: #f0f0f0; 
                     text-decoration: none; color: #0066cc; border-radius: 5px; }
        .video-link:hover { background: #e0e0e0; }
        .note { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Panopto Video Resources</h1>
    <div class="note">
        <strong>Note:</strong> Panopto videos require manual download. 
        Click each link below, then use the download option within the Panopto player.
    </div>
    <h2>Available Videos:</h2>
"""
                for video in panopto_links:
                    html_content += f'    <a href="{video["url"]}" class="video-link" target="_blank">{video["title"]}</a>\n'
                
                html_content += """
</body>
</html>"""
                
                with open(panopto_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"      Saved Panopto links to {panopto_file.name}")
                
                # Track in manifest
                for video in panopto_links:
                    tracker.mark_special_content('panopto_video', video)
            
            if video_links:
                print(f"    Found {len(video_links)} other video/recording links")
                for video in video_links:
                    tracker.mark_special_content('video_resource', video)
                    
        except Exception as e:
            print(f"    Error checking special content: {e}")
    
    def extract_file_ids_and_links_from_html(self, html_content, section=""):
        file_info = {}
        
        # Canvas file patterns
        canvas_pattern = r'/courses/\d+/files/(\d+)'
        file_id_matches = re.findall(canvas_pattern, html_content)
        download_pattern = r'files/(\d+)/download'
        download_matches = re.findall(download_pattern, html_content)
        all_file_ids = set(file_id_matches + download_matches)
        
        for file_id in all_file_ids:
            filename = self.extract_filename_for_id(html_content, file_id)
            file_info[file_id] = {
                "filename": filename,
                "file_id": file_id,
                "source": section or "unknown"
            }
        
        # Direct file links (support both single and double quotes)
        direct_link_pattern = r'''href=['"]([^'"\s>]+\.(?:pdf|doc|docx|ppt|pptx|xls|xlsx|zip|txt|mp4|mp3|jpg|png|csv|json|xml))['"]'''
        direct_links = re.findall(direct_link_pattern, html_content, re.IGNORECASE)
        
        for link in direct_links:
            if '/files/' in link:
                continue
            filename = link.split('/')[-1].split('?')[0]
            file_info[link] = {
                "filename": filename,
                "direct_url": link,
                "source": section or "unknown"
            }
        
        return file_info
    
    def extract_filename_for_id(self, html_content, file_id):
        patterns = [
            rf'<a[^>]*files/{file_id}[^>]*>([^<]+)</a>',
            rf'<a[^>]*files/{file_id}[^>]*title="([^"]+)"',
            rf'<a[^>]*files/{file_id}[^>]*aria-label="([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                filename = re.sub(r'^(Download\s+|View\s+|Open\s+)', '', filename, flags=re.IGNORECASE)
                if filename and '.' in filename:
                    return filename
        
        # Default fallback without assuming extension
        return f"canvas_file_{file_id}"
    
    def download_files_by_id(self, course_url, file_info, course_name, tracker):
        course_id_match = re.search(r'/courses/(\d+)', course_url)
        course_id = course_id_match.group(1) if course_id_match else None
        
        course_folder = self.download_folder / course_name
        course_folder.mkdir(exist_ok=True)
        
        # Initialize name manager
        name_manager = FileNameManager(course_folder)
        
        downloaded_files = []
        failed_downloads = []
        skipped_existing = 0
        
        # Show initial statistics
        stats = tracker.get_stats()
        if stats['total_downloaded'] > 0:
            print(f"    Previously downloaded: {stats['total_downloaded']} files")
        
        file_items = list(file_info.items())
        total_to_download = len(file_items)
        
        for i, (key, info) in enumerate(file_items, 1):
            try:
                # Check if already downloaded
                if tracker.is_downloaded(key, info):
                    skipped_existing += 1
                    continue
                
                # Check if we should retry failed downloads
                if not tracker.should_retry_failed(key, self.config.max_retries):
                    print(f"    ({i}/{total_to_download}) Skipping (max retries): {info.get('filename', key)}")
                    continue
                
                # Get original filename and ensure it's not None or empty
                original_filename = info.get('filename', '')
                if not original_filename:
                    original_filename = f'file_{key}'
                
                unique_filename = name_manager.get_unique_filename(original_filename, key)
                
                if 'direct_url' in info:
                    download_url = info['direct_url']
                    if download_url.startswith('/'):
                        download_url = f"{self.canvas_url}{download_url}"
                    elif not download_url.startswith('http'):
                        download_url = f"{course_url}/{download_url}"
                    print(f"    ({i}/{total_to_download}) Downloading: {unique_filename}")
                elif 'file_id' in info and course_id:
                    file_id = info['file_id']
                    download_url = f"{self.canvas_url}/courses/{course_id}/files/{file_id}/download"
                    print(f"    ({i}/{total_to_download}) Downloading: {unique_filename}")
                else:
                    print(f"    ({i}/{total_to_download}) Skipping: {unique_filename} (no valid URL)")
                    continue
                
                # Download with requests (controlled filename)
                dest_path = course_folder / unique_filename
                try:
                    downloaded_path = self.download_with_requests(download_url, str(dest_path))
                    actual_filename = Path(downloaded_path).name
                    tracker.mark_downloaded(key, actual_filename, {'url': download_url})
                    downloaded_files.append(actual_filename)
                    print("      Successfully downloaded")
                except Exception as e:
                    tracker.mark_failed(key, unique_filename, str(e))
                    failed_downloads.append(unique_filename)
                    print(f"      Download failed: {e}")
                    
            except Exception as e:
                print(f"      Failed: {e}")
                # Use a safe filename for error tracking
                safe_filename = info.get('filename', f'file_{key}') if info else f'file_{key}'
                tracker.mark_failed(key, safe_filename, str(e))
                failed_downloads.append(safe_filename)
                continue
        
        # Final statistics
        print(f"  Downloaded {len(downloaded_files)} new files")
        if skipped_existing > 0:
            print(f"  Skipped {skipped_existing} existing files")
        if failed_downloads:
            print(f"  Failed: {len(failed_downloads)} files")
        
        # Update and display tracker stats
        final_stats = tracker.get_stats()
        print(f"  Total in course: {final_stats['total_downloaded']} files")
        
        return downloaded_files
    
    def filter_valuable_files(self, file_info):
        valuable_files = {}
        skipped_files = []
        
        for file_id, info in file_info.items():
            filename = info.get('filename', '')
            # Fixed: use direct_url instead of non-existent full_url
            file_url = info.get('direct_url', '')
            context = info.get('source', '')
            
            if self.is_valuable_file(filename, file_url, context):
                valuable_files[file_id] = info
            else:
                skipped_files.append(filename)
        
        if skipped_files:
            print(f"    Filtered out {len(skipped_files)} system files")
            
        return valuable_files
    
    def is_valuable_file(self, filename, file_url="", context=""):
        filename_lower = filename.lower()
        
        # Educational file extensions
        valuable_extensions = [
            '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
            '.txt', '.rtf', '.odt', '.odp', '.ods', '.zip', '.rar', '.7z',
            '.mp4', '.avi', '.mov', '.wmv', '.mp3', '.wav', '.m4a',
            '.epub', '.mobi', '.csv', '.json', '.xml', '.html', '.htm'
        ]
        
        has_valuable_ext = any(filename_lower.endswith(ext) for ext in valuable_extensions)
        if has_valuable_ext:
            return True
        
        # Check images
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg']
        is_image = any(filename_lower.endswith(ext) for ext in image_extensions)
        
        if is_image:
            # Educational image indicators
            educational_indicators = [
                'diagram', 'chart', 'graph', 'figure', 'illustration', 'model',
                'slide', 'presentation', 'handout', 'worksheet', 'exam', 'quiz'
            ]
            
            for indicator in educational_indicators:
                if indicator in filename_lower or indicator in context.lower():
                    return True
            
            # Skip UI elements
            ui_patterns = ['icon_', 'btn_', 'button_', 'arrow_', 'logo_', 'banner_']
            for pattern in ui_patterns:
                if pattern in filename_lower:
                    return False
        
        # Default to keeping files without clear extension
        return True
    
    def download_course_files(self, course):
        # Handle missing or None course names
        course_name = course.get("name", "unnamed_course")
        if not course_name:
            course_name = "unnamed_course"
        course_name = FileNameManager.sanitize_filename(course_name)
        course_folder = self.download_folder / course_name
        course_folder.mkdir(exist_ok=True)
        
        # Initialize tracker for this course (only once)
        tracker = DownloadTracker(course_folder)
        
        print(f"\nProcessing course: {course.get('name', 'Unnamed Course')}")
        
        file_info = self.extract_file_ids_from_content(course["url"], tracker, course_folder)
        
        total_items = len(file_info)
        
        if total_items == 0:
            stats = tracker.get_stats()
            if stats['total_downloaded'] > 0:
                print(f"  All files already downloaded ({stats['total_downloaded']} files)")
            else:
                print(f"  No files found in {course.get('name', 'this course')}")
            return []
        
        print(f"  Found {len(file_info)} new files to download")
        
        # Pass tracker to download function (don't create new one)
        downloaded_files = self.download_files_by_id(course["url"], file_info, course_name, tracker)
        
        if downloaded_files is None:
            downloaded_files = []
            
        return downloaded_files
    
    def download_all_courses(self, selected_courses=None):
        courses = self.get_courses()
        
        if not courses:
            print("No courses found!")
            return
            
        if selected_courses:
            courses = [c for c in courses if c["name"] in selected_courses]
            
        print(f"\nStarting download for {len(courses)} courses...")
        
        summary = {"total_courses": len(courses), "courses": {}}
        
        for course_idx, course in enumerate(courses, 1):
            print(f"\n{'='*50}")
            print(f"Course {course_idx}/{len(courses)}: {course.get('name', 'Unnamed Course')}")
            
            # Take breaks between courses
            if course_idx > 1:
                inter_course_delay = random.uniform(*self.config.course_break_duration)
                print(f"Taking break between courses: {inter_course_delay:.0f}s")
                time.sleep(inter_course_delay)
            
            # Handle missing or None course names
            course_name = course.get("name", "unnamed_course")
            if not course_name:
                course_name = "unnamed_course"
            course_name = FileNameManager.sanitize_filename(course_name)
            course_folder = self.download_folder / course_name
            course_folder.mkdir(exist_ok=True)
            print(f"Course folder: {course_folder}")
            
            files_downloaded = []
            files_from_course = self.download_course_files(course)
            files_downloaded.extend(files_from_course)
            
            summary["courses"][course.get("name", "Unnamed Course")] = {
                "files_count": len(files_downloaded),
                "files": files_downloaded,
                "course_folder": str(course_folder)
            }
            
            print(f"Completed {course.get('name', 'Unnamed Course')}: {len(files_downloaded)} new items")
            
        summary_file = self.download_folder / "download_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print(f"\n{'='*50}")
        print("DOWNLOAD COMPLETE")
        print(f"Summary saved to: {summary_file}")
        print(f"All courses saved to: {self.download_folder.absolute()}")
        print(f"Statistics:")
        print(f"  Total requests: {self.rate_limiter.request_count}")
        print(f"  Current backoff: {self.rate_limiter.backoff_multiplier:.1f}x")

def main():
    print("=" * 60)
    print("CANVAS COURSE MATERIAL DOWNLOADER")
    print("=" * 60)
    print("A tool to help students archive their course materials")
    print("Default: Dartmouth College Canvas")
    print("")
    
    canvas_url = input("Press Enter for Dartmouth Canvas, or enter your Canvas URL: ").strip()
    if not canvas_url:
        canvas_url = "https://canvas.dartmouth.edu"
        print("Using: Dartmouth College Canvas")
    else:
        print(f"Using: {canvas_url}")
    print("")
    
    downloader = CanvasDownloader(canvas_url)
    
    try:
        downloader.setup_driver()
        print("Starting login process...")
        downloader.login()
        
        print("\n" + "=" * 60)
        print("COURSE SELECTION")
        print("=" * 60)
        print("Choose your download option:")
        print("")
        print("1. Download from ALL courses")
        print("2. Select specific courses")
        print("")
        
        while True:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice in ["1", "2"]:
                break
            print("Please enter 1 or 2")
        
        print(f"\nStarting download process...")
        
        if choice == "2":
            courses = downloader.get_courses()
            if not courses:
                print("No courses found!")
                return
                
            print(f"\nFound {len(courses)} available courses:")
            print("-" * 40)
            for i, course in enumerate(courses, 1):
                print(f"{i:2d}. {course['name']}")
            print("-" * 40)
            
            selected_indices = input("\nEnter course numbers to download (comma-separated, e.g., 1,3,5): ").strip()
            selected_courses = []
            
            for idx in selected_indices.split(','):
                try:
                    course_idx = int(idx.strip()) - 1
                    if 0 <= course_idx < len(courses):
                        selected_courses.append(courses[course_idx]["name"])
                except Exception:
                    pass
                    
            if selected_courses:
                print(f"\nSelected {len(selected_courses)} courses for download")
                downloader.download_all_courses(selected_courses)
            else:
                print("No valid courses selected!")
        else:
            downloader.download_all_courses()
            
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user")
    except Exception as e:
        print(f"\nError occurred: {e}")
        print("Try running the script again or check your internet connection")
    finally:
        print("\n" + "=" * 60)
        print("IMPORTANT: Browser window kept open")
        print("=" * 60)
        print("The browser will remain open to maintain your Canvas session.")
        print("You can run this script again without logging in.")
        print("Already downloaded files will be automatically skipped.")
        print("Close the browser manually when completely finished.")
        print("=" * 60)

if __name__ == "__main__":
    main()