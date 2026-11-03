import base64
import importlib
import json
import os
import sys
import time
import uuid
import threading
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def install_module(module_name, import_name=None):
    import subprocess
    import_name = import_name or module_name.split("==")[0].replace("-", "_")
    try:
        return importlib.import_module(import_name)
    except ImportError:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", module_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            return importlib.import_module(import_name)
        except Exception:
            return None


install_module("requests")
install_module("colorama")
install_module("arabic-reshaper", "arabic_reshaper")
install_module("python-bidi==0.4.2", "bidi")

import requests
from colorama import init, Fore, Style

init(autoreset=True)

try:
    import arabic_reshaper
    _reshaper = arabic_reshaper.ArabicReshaper(
        configuration={
            "delete_harakat": False,
            "support_ligatures": True,
        }
    )
except Exception:
    _reshaper = None

try:
    from bidi.algorithm import get_display as bidi_get_display
except Exception:
    import re
    def bidi_get_display(text):
        tokens = re.findall(r'[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+|[^\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]+', text)
        tokens.reverse()
        return ''.join(tokens)


def ar(text):
    if not text or not isinstance(text, str):
        return text
    if not any("\u0600" <= char <= "\u06FF" for char in text):
        return text
    try:
        reshaped = _reshaper.reshape(text) if _reshaper else text
        return bidi_get_display(reshaped)
    except Exception:
        return text


try:
    import keyboard
except Exception:
    keyboard = None

try:
    import msvcrt
except ImportError:
    msvcrt = None


CHECKPOINT_FILE = "mix_v3_progress.json"

class UI:
    _last_msg = ""
    _repeat_count = 0
    _in_progress = False

    @classmethod
    def print_banner(cls):
        print(Fore.CYAN + Style.BRIGHT + """
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║              ETISALAT HEKAYA AUTOMATIC MIX STACKER V3                 ║
  ║     [Dual-Session Keep-Alive • Smart Inviter • Auto-Child Loop]       ║
  ╚═══════════════════════════════════════════════════════════════════════╝
""" + Style.RESET_ALL)

    @classmethod
    def end_progress(cls):
        if cls._in_progress:
            sys.stdout.write("\n")
            sys.stdout.flush()
            cls._in_progress = False
            cls._last_msg = ""
            cls._repeat_count = 0

    @classmethod
    def progress(cls, msg):
        cls._in_progress = True
        shaped_msg = ar(msg)
        line = f"  ⏳ {shaped_msg}"
        sys.stdout.write(f"\r{' ' * 100}\r{Fore.YELLOW}{line}{Style.RESET_ALL}")
        sys.stdout.flush()

    @classmethod
    def log(cls, msg, color=Fore.WHITE, bright=False, prefix=""):
        cls.end_progress()
        raw_msg = f"{prefix} {msg}".strip()

        if raw_msg == cls._last_msg:
            cls._repeat_count += 1
            repeat_tag = ar(f"(تكرر {cls._repeat_count}x)")
            shaped_msg = ar(msg)
            sys.stdout.write(f"\r{' ' * 105}\r{color}{prefix} {shaped_msg} {Fore.YELLOW}{repeat_tag}{Style.RESET_ALL}")
            sys.stdout.flush()
            return

        if cls._repeat_count > 0:
            sys.stdout.write("\n")
            cls._repeat_count = 0

        cls._last_msg = raw_msg
        shaped_msg = ar(msg)
        full_line = f"{prefix} {shaped_msg}".strip()
        style = (Style.BRIGHT if bright else "") + color
        print(f"{style}{full_line}{Style.RESET_ALL}")

    @classmethod
    def success(cls, msg):
        cls.log(msg, color=Fore.GREEN, bright=True, prefix="[✓]")

    @classmethod
    def info(cls, msg):
        cls.log(msg, color=Fore.CYAN, prefix="[ℹ]")

    @classmethod
    def warn(cls, msg):
        cls.log(msg, color=Fore.YELLOW, bright=True, prefix="[!]")

    @classmethod
    def error(cls, msg):
        cls.log(msg, color=Fore.RED, bright=True, prefix="[✖]")

    @classmethod
    def clear_screen(cls):
        try:
            if os.name == "nt":
                os.system("cls")
            else:
                sys.stdout.write("\033[2J\033[H")
                sys.stdout.flush()
        except Exception:
            pass

    @classmethod
    def render_dashboard(cls, cycle_number, owner_number, member_number, current_plan, owner_mix, member_mix, target_mix):
        cls.end_progress()
        border = "═" * 65
        title = ar(f"لوحة متابعة ترحيل الميكسات | دورة نشطة #{cycle_number}")
        print(Fore.CYAN + Style.BRIGHT + "╔" + border + "╗")
        print("║  " + Fore.YELLOW + title.center(61) + Fore.CYAN + "  ║")
        print("╠" + border + "╣")
        t_owner = ar(f"المالك: {owner_number}")
        t_member = ar(f"الفرد: {member_number}")
        print("║  " + Fore.WHITE + t_owner + "   │   " + Fore.WHITE + t_member)
        t_plan = ar(f"الباقة الحالية: {current_plan}")
        print("║  " + Fore.WHITE + t_plan)
        t_target = ar(f"الهدف: {target_mix:,} ميكس")
        total_achieved = owner_mix + member_mix
        t_curr = ar(f"المحقق حتى الآن: {total_achieved:,} ميكس (أونر: {owner_mix:,} | فرد: {member_mix:,})")
        print("║  " + Fore.GREEN + t_target + "   │   " + Fore.MAGENTA + t_curr)
        print(Fore.CYAN + Style.BRIGHT + "╚" + border + "╝" + Style.RESET_ALL)

    @classmethod
    def section(cls, title):
        cls.end_progress()
        shaped_title = ar(title)
        print(f"\n{Fore.BLUE}{Style.BRIGHT}┌─── {shaped_title} " + "─" * max(2, 60 - len(title)) + f"{Style.RESET_ALL}")

    @classmethod
    def pause_alert(cls, title, details):
        cls.end_progress()
        border = "═" * 68
        shaped_title = ar(title)
        shaped_details = ar(details)
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}{border}")
        print(f"  {shaped_title}")
        print(f"  {Fore.LIGHTMAGENTA_EX}{shaped_details}")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}{border}{Style.RESET_ALL}\n")


class PauseController:
    def __init__(self):
        self.pause_requested = False
        self.is_paused = False
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._lock = threading.Lock()
        self._listener_running = True
        self._setup_hotkeys()
        self._start_terminal_key_watcher()

    def request_pause(self):
        with self._lock:
            if not self.pause_requested and not self.is_paused:
                self.pause_requested = True
                UI.pause_alert(
                    "⏸️ [أمر إيقاف مؤقت: Ctrl+P]",
                    "تم رصد الطلب! سيتوقف السكربت بأمان بعد اكتمال ريفييل كوتا الفرد وقبل التحويل إليه..."
                )

    def request_resume(self):
        with self._lock:
            if self.is_paused or self.pause_requested:
                self.pause_requested = False
                self.is_paused = False
                self._resume_event.set()
                UI.pause_alert(
                    "▶️ [أمر استئناف: Ctrl+R]",
                    "تم استلام أمر المتابعة بنجاح! جاري استئناف العمل فوراً..."
                )

    def check_and_wait(self, checkpoint_desc="نقطة الأمان", progress=None):
        if self.pause_requested:
            with self._lock:
                self.is_paused = True
                self._resume_event.clear()

            if progress:
                progress["phase"] = "paused"
                progress["pause_point"] = checkpoint_desc
                try:
                    save_progress(progress)
                except Exception:
                    pass

            UI.pause_alert(
                f"⏸️ [السكربت متوقف مؤقتاً بأمان عند: {checkpoint_desc}]",
                "الميكسات في أمان تام.\nاضغط [Ctrl + R] (في ويندوز) أو اضغط [Enter] للاستئناف فوراً..."
            )

            if not msvcrt:
                try:
                    input(f"{Fore.GREEN}{ar('اضغط Enter للاستئناف والمتابعة')} : {Style.RESET_ALL}")
                    self.request_resume()
                except Exception:
                    pass
            else:
                while not self._resume_event.is_set():
                    time.sleep(0.2)

    def _setup_hotkeys(self):
        if not keyboard:
            return
        try:
            keyboard.add_hotkey("ctrl+p", self.request_pause)
            keyboard.add_hotkey("ctrl+r", self.request_resume)
        except Exception:
            pass

    def _start_terminal_key_watcher(self):
        if msvcrt:
            def _watcher():
                while self._listener_running:
                    try:
                        if msvcrt.kbhit():
                            ch = msvcrt.getch()
                            if ch == b"\x10":
                                self.request_pause()
                            elif ch == b"\x12":
                                self.request_resume()
                            elif ch in (b"r", b"R") and self.is_paused:
                                self.request_resume()
                        time.sleep(0.05)
                    except Exception:
                        time.sleep(0.1)

            t = threading.Thread(target=_watcher, daemon=True)
            t.start()


pause_controller = PauseController()

class AccountSession:
    """
    جلسة مخصصة ومنعزلة لكل حساب (أونر أو فرد)، تدعم:
    - Connection Pooling واستمرارية الاتصال TCP Keep-Alive
    - التوثيق التلقائي عبر Bearer JWT
    - استرجاع وحفظ الكوكيز
    - التجديد الآلي عند انتهاء الصلاحية 401
    """
    def __init__(self, name="Account"):
        self.name = name
        self.session = requests.Session()
        self.dial = None
        self.chosen_dial = None
        self.jwt = None
        self.cookies = None
        self.xauth = None
        self._init_default_headers()

    def _init_default_headers(self):
        self.session.headers.update({
            'Host': "mab.etisalat.com.eg:11003",
            'User-Agent': "okhttp/5.0.0-alpha.11",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'applicationVersion': "2",
            'applicationName': "MAB",
            'APP-BuildNumber': "10752",
            'APP-Version': "37.1.1",
            'OS-Type': "Android",
            'OS-Version': "15",
            'APP-STORE': "GOOGLE",
            'C-Type': "4G",
            'Is-Corporate': "false",
        })

    def update_auth(self, dial, jwt, cookies, xauth=None):
        self.dial = normalize_phone_number(dial)
        self.jwt = jwt
        self.cookies = cookies
        if xauth:
            self.xauth = xauth

        # تحديث ترويسة الجلسة المعزولة
        if self.jwt:
            self.session.headers['auth'] = "Bearer " + self.jwt
        if self.cookies:
            self.session.headers['Cookie'] = self.cookies

    def refresh_if_needed(self):
        if self.xauth:
            UI.warn(f"جاري تجديد جلسة {self.name} تلقائياً عبر السيرفر...")
            res = login_with_plan(self.xauth, session=self.session)
            self.update_auth(res["dial"], res["jwt"], res["cookies"], self.xauth)
            # إذا كان المستخدم قد اختار خطاً معيناً يختلف عن الخط الافتراضي المسترجع
            if self.chosen_dial and self.chosen_dial != res["dial"]:
                try:
                    switch_account_dial(self, self.chosen_dial)
                except Exception as sw_err:
                    UI.warn(f"تعذر استعادة التوكن المخصص للخط {self.chosen_dial} أثناء التجديد: {sw_err}")
            UI.success(f"تم تجديد جلسة {self.name} بنجاح!")
            return True
        return False

def new_checkpoint_path():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    filename = f"mix_v3_progress_{uuid.uuid4().hex[:8]}.json"
    return os.path.join(script_directory, filename)


def save_progress(progress):
    temporary_file = CHECKPOINT_FILE + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as checkpoint:
        json.dump(progress, checkpoint, indent=2, ensure_ascii=False)
        checkpoint.flush()
        os.fsync(checkpoint.fileno())
    os.replace(temporary_file, CHECKPOINT_FILE)


def normalize_phone_number(number):
    if not number:
        return ""
    value = str(number).strip()
    if value.startswith("+20"):
        value = value[3:]
    elif value.startswith("0020"):
        value = value[4:]
    if not value.isdigit():
        raise ValueError(f"رقم الهاتف يجب أن يحتوي على أرقام فقط: {number}")
    if len(value) == 11 and value.startswith("0"):
        value = value[1:]
    if len(value) != 10 or not value.startswith(("10", "11", "12", "15")):
        raise ValueError(f"يرجى إدخال رقم محمول مصري صحيح: {number}")
    return value


def get_login_claims(jwt_str):
    if not jwt_str or "." not in jwt_str:
        return {}
    parts = jwt_str.split(".")
    if len(parts) < 2:
        return {}
    token_payload = parts[1]
    token_payload += "=" * (-len(token_payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(token_payload).decode("utf-8"))
    except Exception:
        return {}


def validate_action_response(response):
    response.raise_for_status()
    xml_text = response.text
    idx = xml_text.find("<?xml")
    if idx != -1:
        xml_text = xml_text[idx:]
    root = ET.fromstring(xml_text)
    status = root.findtext(".//status")
    if status != "true":
        err_msg = root.findtext(".//errorMessage") or root.findtext(".//message") or response.text
        raise RuntimeError(f"الخدمة لم تؤكد نجاح العملية: {err_msg}")

def execute_with_auto_refresh(account_session, request_func, max_attempts=5):
    """
    تنفيذ أي طلب HTTP مع التعامل الفوري مع أخطاء 401 Unauthorized أو 403 Forbidden
    وتجديد التوكن تلقائياً وإعادة المحاولة في نفس اللحظة بدون أي توقف.
    """
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            resp = request_func()
            return resp
        except requests.exceptions.HTTPError as http_err:
            status_code = getattr(http_err.response, 'status_code', None)
            if status_code in (401, 403):
                UI.warn(f"تم رصد انتهاء/حظر الجلسة ({status_code}) لـ {account_session.name}. تجديد التوكن فوراً...")
                refreshed = account_session.refresh_if_needed()
                if refreshed:
                    continue
            raise http_err
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as net_err:
            UI.warn(f"تعثر الاتصال بالسيرفر ({net_err.__class__.__name__}). إعادة المحاولة فوراً...")
            time.sleep(0.5)
            continue
        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "403" in err_str or "unauthorized" in err_str or "forbidden" in err_str:
                UI.warn(f"تم رصد خطأ جلسة (401/403) في الاستجابة لـ {account_session.name}. تجديد التوكن فوراً...")
                if account_session.refresh_if_needed():
                    continue
            raise e
    raise RuntimeError(f"فشل الطلب لـ {account_session.name} بعد {max_attempts} محاولات تجديد.")


def keep_retrying(action_name, action, progress=None, account_session=None, max_attempts=None, delay=1):
    attempt = 0
    while max_attempts is None or attempt < max_attempts:
        attempt += 1
        try:
            result = action()
            if progress and "last_error" in progress:
                progress.pop("last_error", None)
            return result
        except Exception as error:
            error_str = f"{type(error).__name__}: {error}"
            if progress:
                progress.update(
                    phase="retrying",
                    retry_action=action_name,
                    last_error=error_str,
                )
                try:
                    save_progress(progress)
                except Exception:
                    pass

            is_auth_error = False
            response = getattr(error, "response", None)
            if response is not None and response.status_code in (401, 403):
                is_auth_error = True
            elif "401" in error_str or "403" in error_str or "unauthorized" in error_str.lower() or "forbidden" in error_str.lower():
                is_auth_error = True

            if is_auth_error and account_session is not None and account_session.xauth:
                try:
                    if account_session.refresh_if_needed():
                        continue
                except Exception as login_err:
                    UI.warn(f"تعذر تجديد الجلسة مؤقتاً: {login_err}")

            # إعادة المحاولة فوراً مع تأخير بسيط جداً
            UI.warn(f"تعثر {action_name} (محاولة {attempt}): {error}. إعادة المحاولة فوراً...")
            time.sleep(delay)

    raise RuntimeError(f"فشلت العملية {action_name} بعد {max_attempts} محاولة.")

def login_with_plan(xauth, session=None):
    s = session or requests.Session()
    headers = {
        'applicationVersion': '2',
        'applicationName': 'MAB',
        'Accept': 'text/xml',
        'Authorization': xauth,
        'Language': 'en',
        'APP-BuildNumber': '10699',
        'APP-Version': '34.3.0',
        'OS-Type': 'Android',
        'OS-Version': '15',
        'APP-STORE': 'GOOGLE',
        'C-Type': 'WIFI',
        'Is-Corporate': 'false',
        'Content-Type': 'text/xml; charset=UTF-8',
        'Host': 'mab.etisalat.com.eg:11003',
        'Connection': 'Keep-Alive',
        'User-Agent': 'okhttp/5.0.0-alpha.11',
    }
    data = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><loginRequest><deviceId>0db086a9bf08b0b9</deviceId><firstLoginAttempt>true</firstLoginAttempt><modelType>SM-A366B</modelType><osVersion>15</osVersion><platform>Android</platform><udid>0db086a9bf08b0b9</udid></loginRequest>"

    log = s.post(
        'https://mab.etisalat.com.eg:11003/Saytar/rest/authentication/loginWithPlan',
        headers=headers,
        data=data,
        timeout=20,
    )
    if log.status_code == 200:
        xml_text = log.text
        idx = xml_text.find("<?xml")
        if idx != -1:
            xml_text = xml_text[idx:]
        root = ET.fromstring(xml_text)
        dial_elem = root.find('.//dial')
        dial = normalize_phone_number(dial_elem.text if dial_elem is not None else "")
        st = log.headers.get("Set-Cookie", "")
        ck = st.split(";")[0] if st else ""
        br = log.headers.get("auth", "")
        return {
            "dial": dial,
            "cookies": ck,
            "jwt": br,
            "xauth": xauth
        }
    log.raise_for_status()


def get_account_numbers(account_session):
    """
    جلب الأرقام المربوطة بالحساب من خلال بيانات التوكن أو عبر API الـ profile
    """
    claims = get_login_claims(account_session.jwt)
    user_claims = claims.get("User", claims.get("user", {}))
    linked_accounts = user_claims.get("linkedCustomerAccountList", {})
    numbers = []

    # 1. فحص الحسابات المرتبطة من التوكن أولاً
    if linked_accounts and isinstance(linked_accounts, dict):
        for raw_d in linked_accounts.keys():
            try:
                norm_d = normalize_phone_number(raw_d)
                if norm_d not in numbers:
                    numbers.append(norm_d)
            except Exception:
                pass

    # 2. في حال لم نجد أرقام كافية أو للتأكيد، نطلب من profile API
    if len(numbers) <= 1:
        try:
            billing_id = claims.get("billingprofileId") or claims.get("billingProfileId") or ""
            acc_num = user_claims.get("billingCustomerCode") or claims.get("customerCode") or ""
            req_xml = f"<getCustomerProfileV4Request><nativeToken/><firstLoginAttempt>true</firstLoginAttempt><serviceClass/><thirdPartyType>firebase</thirdPartyType><versionNum>37.3.0</versionNum><billingProfileId>{billing_id}</billingProfileId><language>1</language><accountNumber>{acc_num}</accountNumber><deviceId>e2849ea5db429c36</deviceId><platform>Android</platform><versionCode>10755</versionCode><deviceModelType>SM-T505N</deviceModelType><osVersion>12</osVersion><notificationToken/></getCustomerProfileV4Request>"
            url = "https://mab.etisalat.com.eg:11003/Saytar/rest/account/profile"
            headers = {'Content-Type': 'text/xml', 'Accept': 'text/xml', 'Language': 'ar'}
            resp = execute_with_auto_refresh(
                account_session,
                lambda: account_session.session.get(url, params={'req': req_xml}, headers=headers, timeout=15)
            )
            xml_text = resp.text
            idx = xml_text.find("<?xml")
            if idx != -1:
                xml_text = xml_text[idx:]
            root = ET.fromstring(xml_text)
            for sub in root.findall(".//subscriberNumber"):
                if sub.text:
                    try:
                        n = normalize_phone_number(sub.text)
                        if n not in numbers:
                            numbers.append(n)
                    except Exception:
                        pass
        except Exception:
            pass

    # التأكد من وجود الرقم الحالي على الأقل
    if account_session.dial and account_session.dial not in numbers:
        numbers.insert(0, account_session.dial)

    return numbers


def switch_account_dial(account_session, target_dial):
    """
    تبديل الحساب إلى الرقم المختار وتحديث الـ JWT Token والكوكيز الخاصة بالجلسة
    باستخدام ريكويست getGenericConsumptionsV2 مثل تطبيق My Etisalat الرسمي تماماً.
    """
    target_dial = normalize_phone_number(target_dial)
    if not target_dial:
        return

    # التحقق مما إذا كان الرقم الحالي هو نفسه الرقم المختار في التوكن
    claims = get_login_claims(account_session.jwt)
    current_selected = normalize_phone_number(claims.get("selectedDial", ""))
    user_claims = claims.get("User", claims.get("user", {}))

    # استخراج shortCode المناسب للرقم المختار
    short_code = ""
    dial_rp_map = user_claims.get("dialRpMap", claims.get("dialRpMap", {}))
    short_code = dial_rp_map.get(target_dial) or dial_rp_map.get("0" + target_dial) or ""
    if not short_code or short_code == "NA":
        linked_accounts = user_claims.get("linkedCustomerAccountList", {})
        acc_info = linked_accounts.get(target_dial) or linked_accounts.get("0" + target_dial) or {}
        short_code = acc_info.get("shdes") or ""

    # إذا كان التوكن الحالي بالفعل يحمل هذا الرقم ولا نحتاج لتبديل
    if current_selected == target_dial and account_session.dial == target_dial:
        return

    UI.info(f"جاري تبديل جلسة {account_session.name} إلى الخط {target_dial} وتحديث التوكن...")

    request_root = ET.Element("dialAndLanguageRequest")
    ET.SubElement(request_root, "segmentId")
    ET.SubElement(request_root, "subscriberNumber").text = target_dial
    ET.SubElement(request_root, "language").text = "1"
    if short_code:
        ET.SubElement(request_root, "shortCode").text = short_code

    params = {"requestParam": ET.tostring(request_root, encoding="unicode")}
    headers = {'Content-Type': 'text/xml', 'Accept': 'text/xml', 'Language': 'ar'}

    try:
        # إرسال طلب التبديل مباشرة وتحديث التوكن بدون الدخول في loop لا نهائي
        resp = account_session.session.get(
            'https://mab.etisalat.com.eg:11003/Saytar/rest/servicemanagement/getGenericConsumptionsV2',
            params=params,
            headers=headers,
            timeout=15
        )
        
        # إذا انتهى التوكن الأساسي (401/403) نحاول تسجيل دخول أولي مرة واحدة فقط
        if resp.status_code in (401, 403) and account_session.xauth:
            UI.warn(f"توكن {account_session.name} الأساسي يحتاج تجديد أثناء التبديل...")
            login_res = login_with_plan(account_session.xauth, session=account_session.session)
            account_session.update_auth(login_res["dial"], login_res["jwt"], login_res["cookies"], account_session.xauth)
            resp = account_session.session.get(
                'https://mab.etisalat.com.eg:11003/Saytar/rest/servicemanagement/getGenericConsumptionsV2',
                params=params,
                headers=headers,
                timeout=15
            )

        resp.raise_for_status()

        # التقاط التوكن الجديد الصادر من السيرفر عند التبديل
        new_auth = resp.headers.get("auth")
        if new_auth:
            new_auth = new_auth.replace("Bearer ", "").strip()
            account_session.jwt = new_auth
            account_session.session.headers['auth'] = "Bearer " + new_auth

        # التقاط وتحديث أي كوكيز جديدة
        set_cookie = resp.headers.get("Set-Cookie")
        if set_cookie:
            ck = set_cookie.split(";")[0].strip()
            if ck:
                account_session.cookies = ck
                account_session.session.headers['Cookie'] = ck

        account_session.dial = target_dial
        account_session.chosen_dial = target_dial
        UI.success(f"تم اعتماد الخط {target_dial} وتحديث الـ JWT Token بنجاح.")
    except Exception as e:
        UI.warn(f"تنبيه: تعذر إكمال تبديل التوكن عبر السيرفر للخط {target_dial}: {e}")
        account_session.dial = target_dial
        account_session.chosen_dial = target_dial


def select_account_number(account_session):
    """
    إذا كان الحساب يحتوي على رقم واحد يكمل به تلقائياً،
    وإذا كان يحتوي على أكثر من رقم يعرض قائمة ليختار المستخدم الرقم المطلوب
    ثم يقوم بتبديل التوكن مباشرة للرقم المختار.
    """
    numbers = get_account_numbers(account_session)
    if not numbers:
        return account_session.dial

    if len(numbers) == 1:
        chosen_number = numbers[0]
        account_session.dial = chosen_number
        switch_account_dial(account_session, chosen_number)
        return chosen_number

    # أكثر من رقم: عرض الخيارات للمستخدم
    print(f"\n{Fore.YELLOW}{ar(f'تم العثور على {len(numbers)} أرقام مربوطة بحساب {account_session.name}:')}{Style.RESET_ALL}")
    for idx, num in enumerate(numbers, start=1):
        print(f"  {Fore.CYAN}{idx}.{Style.RESET_ALL} {Fore.WHITE}{num}{Style.RESET_ALL}")

    while True:
        choice = input(f"{Fore.GREEN}{ar('اختر رقم الخط المطلوب (أدخل الرقم)')} : {Style.RESET_ALL}").strip()
        if choice.isdigit():
            c_idx = int(choice) - 1
            if 0 <= c_idx < len(numbers):
                chosen_number = numbers[c_idx]
                account_session.dial = chosen_number
                UI.success(f"تم اختيار الخط: {chosen_number}")
                switch_account_dial(account_session, chosen_number)
                return chosen_number
        UI.warn("اختيار غير صالح، يرجى إدخال رقم من القائمة.")


def get_owner_plan_mixes(account_session):
    """
    استعلام ميكسات الباقة الحالية للأونر عبر getGenericConsumptionsV2
    بدون الحاجة لوجود أفراد بالعائلة
    """
    num = account_session.dial
    claims = get_login_claims(account_session.jwt)
    user_claims = claims.get("User", claims.get("user", {}))
    dial_rp_map = user_claims.get("dialRpMap", claims.get("dialRpMap", {}))
    short_code = dial_rp_map.get(num) or dial_rp_map.get("0" + num)
    if not short_code or short_code == "NA":
        selected_dial = claims.get("selectedDial")
        selected_short_code = claims.get("selectedDialShortCode")
        if selected_dial and normalize_phone_number(selected_dial) == num:
            short_code = selected_short_code
    if not short_code or short_code == "NA":
        linked_accounts = user_claims.get("linkedCustomerAccountList", {})
        account_details = linked_accounts.get(num) or linked_accounts.get("0" + num) or {}
        short_code = account_details.get("shdes")
    if not short_code or short_code == "NA":
        short_code = "XRPM7"

    request_root = ET.Element("dialAndLanguageRequest")
    ET.SubElement(request_root, "segmentId").text = "XRP"
    ET.SubElement(request_root, "subscriberNumber").text = num
    ET.SubElement(request_root, "language").text = "1"
    ET.SubElement(request_root, "shortCode").text = short_code
    params = {"requestParam": ET.tostring(request_root, encoding="unicode")}
    headers = {'Content-Type': 'text/xml', 'Accept': 'text/xml', 'Language': 'ar'}

    resp = execute_with_auto_refresh(
        account_session,
        lambda: account_session.session.get(
            'https://mab.etisalat.com.eg:11003/Saytar/rest/servicemanagement/getGenericConsumptionsV2',
            params=params,
            headers=headers,
            timeout=15
        )
    )
    validate_action_response(resp)
    xml_text = resp.text
    idx = xml_text.find("<?xml")
    if idx != -1:
        xml_text = xml_text[idx:]
    root = ET.fromstring(xml_text)

    # استخراج الميكسات من consumptionMeterType == xrp_units أو hekaya_units أو remainingOmsName
    total_remaining_mixes = 0
    found_any = False
    for c in root.findall(".//consumption"):
        meter_type = c.findtext("consumptionMeterType") or ""
        oms_name = c.findtext("remainingOmsName") or ""
        rem_val = c.findtext("remainingValue")
        if rem_val is not None:
            try:
                val = int(rem_val)
                if "xrp" in meter_type.lower() or "hekaya" in meter_type.lower() or "unit" in meter_type.lower() or "GENERAL_UNIT" in oms_name:
                    total_remaining_mixes = max(total_remaining_mixes, val)
                    found_any = True
            except Exception:
                pass

    if not found_any:
        # فحص بديل عبر البحث عن أي remainingValue في عناصر الاستهلاك الأساسية
        for c in root.findall(".//ratePlanConsumption//consumption"):
            rem_val = c.findtext("remainingValue")
            if rem_val is not None:
                try:
                    val = int(rem_val)
                    total_remaining_mixes = max(total_remaining_mixes, val)
                except Exception:
                    pass

    return total_remaining_mixes


def get_current_plan_name(account_session):
    num = account_session.dial
    claims = get_login_claims(account_session.jwt)
    user_claims = claims.get("User", claims.get("user", {}))
    dial_rp_map = user_claims.get("dialRpMap", claims.get("dialRpMap", {}))
    short_code = dial_rp_map.get(num) or dial_rp_map.get("0" + num)
    if not short_code or short_code == "NA":
        selected_dial = claims.get("selectedDial")
        selected_short_code = claims.get("selectedDialShortCode")
        if selected_dial and normalize_phone_number(selected_dial) == num:
            short_code = selected_short_code
    if not short_code or short_code == "NA":
        linked_accounts = user_claims.get("linkedCustomerAccountList", {})
        account_details = linked_accounts.get(num) or linked_accounts.get("0" + num) or {}
        short_code = account_details.get("shdes")
    if not short_code or short_code == "NA":
        short_code = "AKDBN"

    request_root = ET.Element("dialAndLanguageRequest")
    ET.SubElement(request_root, "segmentId").text = "XRP"
    ET.SubElement(request_root, "subscriberNumber").text = num
    ET.SubElement(request_root, "language").text = "2"
    ET.SubElement(request_root, "shortCode").text = short_code
    params = {"requestParam": ET.tostring(request_root, encoding="unicode")}

    headers = {'Content-Type': 'text/xml', 'Accept': 'text/xml', 'Language': 'en'}
    resp = execute_with_auto_refresh(
        account_session,
        lambda: account_session.session.get(
            'https://mab.etisalat.com.eg:11003/Saytar/rest/servicemanagement/getGenericConsumptionsV2',
            params=params,
            headers=headers,
            timeout=15
        )
    )
    validate_action_response(resp)
    xml_text = resp.text
    idx = xml_text.find("<?xml")
    if idx != -1:
        xml_text = xml_text[idx:]
    root = ET.fromstring(xml_text)

    if root.findtext("status") != "true":
        raise RuntimeError("فشل استرجاع بيانات استهلاك الباقة")
    product_id = root.findtext("./ratePlanConsumption/productId") or root.findtext(".//productId")
    if not product_id:
        raise ValueError("الاستجابة لم تتضمن productId للباقة الحالية")
    return product_id


def get_family_quotas(account_session, current_plan, member_number=None):
    num = account_session.dial
    url = "https://mab.etisalat.com.eg:11003/Saytar/rest/emerald/transferInquiry"
    params = {
        'req': f"<transferInquiryRequest><productId>{current_plan}</productId><subscriberNumber>{num}</subscriberNumber><language>2</language></transferInquiryRequest>"
    }
    headers = {'Content-Type': 'text/xml', 'Accept': 'text/xml', 'Language': 'en'}
    resp = execute_with_auto_refresh(
        account_session,
        lambda: account_session.session.get(url, params=params, headers=headers, timeout=15)
    )
    validate_action_response(resp)
    xml_text = resp.text
    idx = xml_text.find("<?xml")
    if idx != -1:
        xml_text = xml_text[idx:]
    root = ET.fromstring(xml_text)

    assigned_units = {}
    for item in root.findall(".//assigned"):
        dial_elem = item.find("dial")
        val_elem = item.find("value")
        if dial_elem is not None and dial_elem.text and val_elem is not None and val_elem.text:
            try:
                norm_d = normalize_phone_number(dial_elem.text)
                assigned_units[norm_d] = int(val_elem.text)
            except Exception:
                assigned_units[dial_elem.text.strip()] = int(val_elem.text)

    owner_mix = assigned_units.get(num, 0)
    other_members = [d for d in assigned_units.keys() if d != num]

    member_mix = 0
    if member_number:
        norm_member = normalize_phone_number(member_number)
        member_mix = assigned_units.get(norm_member, 0)
    elif other_members:
        member_mix = assigned_units.get(other_members[0], 0)

    return {
        "owner": owner_mix,
        "member": member_mix,
        "assigned": assigned_units,
        "other_members": other_members
    }


def change_plan(account_session, plan_type):
    num = account_session.dial

    if plan_type == "HARLEY":
        url = "https://mab.etisalat.com.eg:11003/Saytar/rest/harleyPreset/migrate"
        payload = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><submitOrderRequest><msisdn>{num}</msisdn><operation>MIGRATE</operation><parameters><parameter><name>MI_QUOTA</name><value>300</value></parameter><parameter><name>UNIT_QUOTA</name><value>60</value></parameter><parameter><name>VALIDITY</name><value>7</value></parameter><parameter><name>PRICE</name><value>10.5</value></parameter><parameter><name>OFFER_ID</name><value>17537</value></parameter></parameters><productName>HARLEY_MINI_BUNDLE</productName></submitOrderRequest>"""
    else:
        url = "https://mab.etisalat.com.eg:11003/Saytar/rest/HekayaPartial/migrate"
        if plan_type in ["180", "Hekaya_XRP_MIX_Parent_6"]:
            payload = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><migrateRequest><addonName></addonName><oMSRatePlan>true</oMSRatePlan><operation>FULL_MIGRATE</operation><productName>Hekaya_XRP_MIX_Parent_6</productName><ratePlanID>951</ratePlanID><subscriberNumber>{num}</subscriberNumber></migrateRequest>"
        elif plan_type in ["270", "Hekaya_XRP_MIX_Parent_7"]:
            payload = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><migrateRequest><addonName></addonName><oMSRatePlan>true</oMSRatePlan><operation>FULL_MIGRATE</operation><productName>Hekaya_XRP_MIX_Parent_7</productName><ratePlanID></ratePlanID><subscriberNumber>{num}</subscriberNumber></migrateRequest>"
        elif plan_type in ["14", "MINION"]:
            payload = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><migrateRequest><addonName></addonName><oMSRatePlan>true</oMSRatePlan><productName>MINION</productName><ratePlanID>1010</ratePlanID><subscriberNumber>{num}</subscriberNumber></migrateRequest>"
        else:
            raise ValueError(f"خطة غير معروفة: {plan_type}")

    headers = {'Content-Type': 'text/xml; charset=UTF-8', 'Accept': 'text/xml', 'Language': 'ar'}
    resp = execute_with_auto_refresh(
        account_session,
        lambda: account_session.session.post(url, data=payload, headers=headers, timeout=20)
    )
    validate_action_response(resp)


def transfer_mixat(account_session, sender_number, receiver_number, current_plan, amount):
    num = account_session.dial
    norm_sender = normalize_phone_number(sender_number)
    norm_receiver = normalize_phone_number(receiver_number)
    url = "https://mab.etisalat.com.eg:11003/Saytar/rest/services/newTransfer/v2"
    payload = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><newFamilyTransferRequest><distribute>false</distribute><msisdn>{num}</msisdn><productName>{current_plan}</productName><quota>{amount}</quota><receiverMsisdn>{norm_receiver}</receiverMsisdn><senderMsisdn>{norm_sender}</senderMsisdn><type>UNITS</type></newFamilyTransferRequest>"

    headers = {'Content-Type': 'text/xml; charset=UTF-8', 'Accept': 'text/xml', 'Language': 'ar'}
    resp = execute_with_auto_refresh(
        account_session,
        lambda: account_session.session.post(url, data=payload, headers=headers, timeout=20)
    )
    validate_action_response(resp)


def add_member(owner_session, member_number, current_plan="Hekaya_XRP_MIX_Parent_7"):
    num = owner_session.dial
    norm_member = normalize_phone_number(member_number)
    url = "https://mab.etisalat.com.eg:11003/Saytar/rest/services/addChild"
    payload = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><addChildRequest><childNumber>{norm_member}</childNumber><childPercentage>0.25</childPercentage><productId>{current_plan}</productId><subscriberNumber>{num}</subscriberNumber></addChildRequest>"

    headers = {'Content-Type': 'text/xml; charset=UTF-8', 'Accept': 'text/xml', 'Language': 'en'}
    resp = execute_with_auto_refresh(
        owner_session,
        lambda: owner_session.session.post(url, data=payload, headers=headers, timeout=20)
    )
    validate_action_response(resp)


def remove_member(owner_session, member_number, current_plan):
    num = owner_session.dial
    norm_member = normalize_phone_number(member_number)
    url = "https://mab.etisalat.com.eg:11003/Saytar/rest/ee_new/removeChild"
    data = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><removeChildSubmitOrder><childMsisdn>{norm_member}</childMsisdn><parentMsisdn>{num}</parentMsisdn><productName>{current_plan}</productName></removeChildSubmitOrder>"

    headers = {'Content-Type': 'text/xml; charset=UTF-8', 'Accept': 'text/xml', 'Language': 'ar'}
    resp = execute_with_auto_refresh(
        owner_session,
        lambda: owner_session.session.post(url, data=data, headers=headers, timeout=20)
    )
    validate_action_response(resp)
    return resp.text

def get_pending_requests(member_session):
    child_num = member_session.dial
    xml_req = f"<dialAndLanguageRequest><language>2</language><subscriberNumber>{child_num}</subscriberNumber></dialAndLanguageRequest>"
    url = "https://mab.etisalat.com.eg:11003/Saytar/rest/falcon/addchildRequestInquiry"
    params = {'req': xml_req}
    headers = {'Accept': 'text/xml', 'Language': 'ar'}
    resp = execute_with_auto_refresh(
        member_session,
        lambda: member_session.session.get(url, params=params, headers=headers, timeout=15)
    )

    xml_text = resp.text
    idx = xml_text.find("<?xml")
    if idx != -1:
        xml_text = xml_text[idx:]
    root = ET.fromstring(xml_text)

    items = []
    for item_elem in root.findall('.//childRequestItem'):
        sender_elem = item_elem.find('senderDial')
        accepted_elem = item_elem.find('accepted')
        sender = normalize_phone_number(sender_elem.text if sender_elem is not None and sender_elem.text else "")
        accepted = accepted_elem.text if accepted_elem is not None and accepted_elem.text else "false"
        items.append({
            "senderDial": sender,
            "accepted": accepted.strip().lower() == "true"
        })
    return items


def confirm_add_child(member_session, raw_sender_dial):
    child_num = member_session.dial
    parent_num_clean = normalize_phone_number(raw_sender_dial)
    url = "https://mab.etisalat.com.eg:11003/Saytar/rest/falcon/confirmAddChild"

    payload = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<submitOrderRequest>
    <msisdn>{child_num}</msisdn>
    <parameters>
        <parameter>
            <name>PARENT_MSISDN</name>
            <value>{parent_num_clean}</value>
        </parameter>
    </parameters>
</submitOrderRequest>"""

    headers = {'Content-Type': 'text/xml; charset=UTF-8', 'Accept': 'text/xml', 'Language': 'ar'}
    resp = execute_with_auto_refresh(
        member_session,
        lambda: member_session.session.post(url, data=payload, headers=headers, timeout=20)
    )
    validate_action_response(resp)

def force_transfer_all_member_to_owner(owner_session, member_number, current_plan_value):
    try:
        quotas = keep_retrying(
            "فحص رصيد الفرد للتحويل الإجباري",
            lambda: get_family_quotas(owner_session, current_plan_value, member_number),
            account_session=owner_session
        )
        member_quota = quotas["member"]
        if member_quota > 0:
            UI.info(f"تحويل إجباري لتنشيط السيستم: ميكسات الفرد للأونر ({member_quota:,})")
            transfer_with_balance_check(
                owner_session, member_number, owner_session.dial, member_quota, current_plan_value, member_number
            )
    except Exception as e:
        UI.warn(f"تنبيه أثناء التحويل الإجباري من الفرد للأونر: {e}")


def force_transfer_all_owner_to_member(owner_session, member_number, current_plan_value):
    try:
        quotas = keep_retrying(
            "فحص رصيد الأونر للتحويل الإجباري",
            lambda: get_family_quotas(owner_session, current_plan_value, member_number),
            account_session=owner_session
        )
        owner_quota = quotas["owner"]
        if owner_quota > 0:
            UI.info(f"تحويل إجباري لتنشيط السيستم: ميكسات الأونر للفرد ({owner_quota:,})")
            transfer_with_balance_check(
                owner_session, owner_session.dial, member_number, owner_quota, current_plan_value, member_number
            )
    except Exception as e:
        UI.warn(f"تنبيه أثناء التحويل الإجباري من الأونر للفرد: {e}")


def change_plan_until_applied(account_session, plan_type, expected_plan, wait_seconds=120, member_number=None):
    """
    تحويل النظام وإعادة المحاولة حتى يظهر النظام الجديد فعلياً على الخط
    (تكرار إرسال ريكويست التحويل كل 120 ثانية إذا لم يتغير النظام).
    في حال تأخر تطبيق النظام بعد 120 ثانية وكان الفرد مضافاً بالعائلة،
    يتم تنفيذ تحويل استثنائي إجباري رايح جاي لتنشيط سيستم اتصالات.
    """
    attempt = 0
    while True:
        attempt += 1
        UI.info(f"إرسال طلب التحويل إلى {expected_plan} (محاولة {attempt})...")
        request_sent = False
        try:
            change_plan(account_session, plan_type)
            request_sent = True
        except Exception as e:
            UI.warn(f"ملاحظة عند إرسال طلب تحويل الباقة: {e}. إعادة إرسال الطلب فوراً...")
            time.sleep(1)
            continue

        observed_plan = None
        for check_idx in range(1, wait_seconds + 1):
            try:
                observed_plan = get_current_plan_name(account_session)
                is_matched = False
                if expected_plan == "MINION" and "MINION" in observed_plan:
                    is_matched = True
                elif expected_plan == "HARLEY_MINI_BUNDLE" and ("HARLEY" in observed_plan or "ميني" in observed_plan):
                    is_matched = True
                elif observed_plan == expected_plan:
                    is_matched = True

                if is_matched:
                    UI.end_progress()
                    UI.success(f"تم تطبيق النظام {expected_plan} بنجاح بعد {check_idx} ثانية.")
                    return observed_plan
            except Exception:
                pass

            UI.progress(f"فحص تطبيق النظام {expected_plan} (الآن: {observed_plan}) [{check_idx}/{wait_seconds} ث]...")
            time.sleep(1)

        UI.end_progress()
        UI.warn(f"النظام لم يتغير بعد {wait_seconds} ثانية (لا يزال {observed_plan})؛")
        
        # تنشيط السيستم بالتحويل الإجباري رايح جاي إذا كان التحويل على الأونر ومعه فرد بالعائلة
        if member_number and observed_plan:
            UI.info("جاري تنشيط السيستم بتحويل ميكسات استثنائي رايح جاي...")
            force_transfer_all_member_to_owner(account_session, member_number, observed_plan)
            force_transfer_all_owner_to_member(account_session, member_number, observed_plan)

        UI.info("إعادة إرسال طلب تحويل الباقة فوراً...")

def balances_reflect_transfer(owner_before, member_before, owner_after, member_after, sender_is_owner):
    if sender_is_owner:
        return owner_after < owner_before and member_after > member_before
    return member_after < member_before and owner_after > owner_before


def transfer_with_balance_check(sender_session, sender_number, receiver_number, amount, current_plan, member_number, inquiry_plan=None):
    """
    تحويل الميكسات والتأكد القاطع من انعكاس الرصيد بالسيرفر:
    - محاولة التحويل بالمبلغ المطلوب.
    - فحص السيرفر كل ثانية لمدة 5 ثوانٍ، وإذا لم ينعكس يكرر حتى 3 دورات (إجمالي 15 ثانية).
    - إذا رجع السيرفر بأن الرصيد غير كافي، أو بعد انتهاء الـ 15 ثانية،
      يقوم بقراءة الرصيد الفعلي المتوفر حالياً وإرسال ما هو موجود فعلياً دون أن يعلق.
    """
    owner_number = normalize_phone_number(sender_session.dial)
    member_normalized = normalize_phone_number(member_number)
    sender_number = normalize_phone_number(sender_number)
    receiver_number = normalize_phone_number(receiver_number)
    sender_is_owner = (sender_number == owner_number)
    check_plan = inquiry_plan or current_plan

    while True:
        # قراءة الرصيد الفعلي المتوفر في حساب الراسل الآن
        quotas_before = keep_retrying(
            "قراءة الرصيد قبل التحويل",
            lambda: get_family_quotas(sender_session, check_plan, member_normalized),
            account_session=sender_session
        )
        owner_before = quotas_before["owner"]
        member_before = quotas_before["member"]
        sender_before = owner_before if sender_is_owner else member_before

        # إذا كان الراسل مصفراً بالفعل (0 ميكس)، تنتهي العملية بنجاح تام
        if sender_before <= 0:
            return quotas_before

        transfer_amount = min(amount, sender_before)

        # تنفيذ 3 محاولات (كل محاولة 5 ثوانٍ = إجمالي 15 ثانية كحد أقصى للنسبة)
        transfer_confirmed = False
        for round_idx in range(1, 4):
            # إرسال طلب التحويل بالمبلغ المطلوب
            try:
                transfer_mixat(sender_session, sender_number, receiver_number, current_plan, transfer_amount)
            except Exception as err:
                err_text = str(err).lower()
                # إذا رد السيرفر بأن الرصيد غير كافي أو أن الكوتا لا تسمح
                if "quota" in err_text or "balance" in err_text or "insufficient" in err_text or "not enough" in err_text or "رصيد" in str(err):
                    UI.warn(f"السيرفر يفيد بعدم كفاية الرصيد المطلوب ({transfer_amount:,})؛ إعادة قراءة الرصيد الفعلي فوراً...")
                    break
                UI.warn(f"ملاحظة عند إرسال طلب التحويل (جولة {round_idx}/3): {err}")

            # فحص انعكاس الرصيد كل ثانية لمدة 5 ثوانٍ
            for sec in range(1, 6):
                total_elapsed = ((round_idx - 1) * 5) + sec
                UI.progress(f"التحقق من انعكاس الرصيد بالسيرفر [{total_elapsed}/15 ث]...")
                time.sleep(1)

                quotas_after = keep_retrying(
                    f"فحص الرصيد بعد التحويل [{total_elapsed}/15 ث]",
                    lambda: get_family_quotas(sender_session, check_plan, member_normalized),
                    account_session=sender_session
                )
                owner_after = quotas_after["owner"]
                member_after = quotas_after["member"]

                if balances_reflect_transfer(owner_before, member_before, owner_after, member_after, sender_is_owner):
                    UI.end_progress()
                    UI.success(f"تم تأكيد التحويل بنجاح! الأونر: ({owner_before:,} ➔ {owner_after:,}) | الفرد: ({member_before:,} ➔ {member_after:,})")
                    transfer_confirmed = True

                    sender_remaining = owner_after if sender_is_owner else member_after
                    if sender_remaining == 0:
                        return quotas_after
                    break

            if transfer_confirmed:
                break

            if round_idx < 3:
                UI.end_progress()
                UI.warn(f"لم ينعكس الرصيد بعد {round_idx * 5} ثوانٍ؛ إعادة إرسال طلب التحويل (محاولة {round_idx + 1}/3)...")

        if not transfer_confirmed:
            UI.end_progress()
            UI.warn("انتهت مهلة الـ 15 ثانية دون تأكيد النسبة السابقة؛ إعادة قراءة الرصيد الحقيقي المتبقي وإرسال المتوفر فعلياً...")


def wait_for_plan_applied(account_session, target_plan, max_seconds=90):
    for i in range(1, max_seconds + 1):
        try:
            curr = get_current_plan_name(account_session)
            if curr == target_plan or (target_plan == "MINION" and "MINION" in curr):
                return True
            UI.progress(f"في انتظار تطبيق باقة {target_plan} (الآن: {curr}) [{i}/{max_seconds} ث]...")
        except Exception:
            pass
        time.sleep(1)
    return False


def wait_for_child_quota_and_fast_pull(member_session, owner_number, timeout_seconds=120):
    """
    فحص فائق السرعة عبر حساب الفرد نفسه (Member Session) لرصد ظهور ميكسات الفرد (15,400)
    وتحويلها للأونر، ومطابقة ملف الـ HAR تماماً:
    1. الفحص المتكرر لـ transferInquiry عبر حساب الفرد على باقة Hekaya_XRP_MIX_Child_1.
    2. الانتظار حتى تظهر ميكسات كل من الأونر والفرد معاً في الريسبونس (الظهور الكامل للربط).
    3. إرسال أمر newTransfer/v2 بحساب الفرد لسحب الـ 15,400 ميكس إلى الأونر.
    4. فحص transferInquiry بحساب الفرد حتى التأكد التام من تصفير الفرد (0 ميكس).
    """
    owner_dial = normalize_phone_number(owner_number)
    member_dial = normalize_phone_number(member_session.dial)
    deadline = time.monotonic() + timeout_seconds

    inquiry_url = "https://mab.etisalat.com.eg:11003/Saytar/rest/emerald/transferInquiry"
    inquiry_params = {
        'req': f"<transferInquiryRequest><productId>Hekaya_XRP_MIX_Child_1</productId><subscriberNumber>{member_dial}</subscriberNumber><language>1</language></transferInquiryRequest>"
    }
    inquiry_headers = {'Content-Type': 'text/xml', 'Accept': 'text/xml', 'Language': 'ar'}

    UI.info("جاري الفحص السريع عبر حساب الفرد لربط العائلة وظهور الميكسات (15,400 ميكس)...")

    member_mix_to_transfer = 0

    while time.monotonic() < deadline:
        try:
            resp = execute_with_auto_refresh(
                member_session,
                lambda: member_session.session.get(inquiry_url, params=inquiry_params, headers=inquiry_headers, timeout=10)
            )
            xml_text = resp.text
            idx = xml_text.find("<?xml")
            if idx != -1:
                xml_text = xml_text[idx:]
            root = ET.fromstring(xml_text)

            assigned_map = {}
            for item in root.findall(".//assigned"):
                d_elem = item.find("dial")
                v_elem = item.find("value")
                if d_elem is not None and d_elem.text and v_elem is not None and v_elem.text:
                    try:
                        assigned_map[normalize_phone_number(d_elem.text)] = int(v_elem.text)
                    except Exception:
                        pass

            # الشرط الذهبي من ملف الـ HAR:
            # يجب أن تظهر أرقام كل من الأونر والفرد معاً في الاستجابة ويكون رصيد الفرد > 0
            if member_dial in assigned_map and owner_dial in assigned_map:
                m_val = assigned_map[member_dial]
                if m_val > 0:
                    member_mix_to_transfer = m_val
                    UI.end_progress()
                    UI.success(f"ظهر ربط العائلة الكامل برصيد الفرد: {m_val:,} ميكس (الأونر: {assigned_map[owner_dial]:,} ميكس)!")
                    break
        except Exception:
            pass

        UI.progress("في انتظار اكتمال ربط الفرد وظهور كوتا الطرفين...")
        time.sleep(0.5)

    if member_mix_to_transfer <= 0:
        UI.end_progress()
        UI.warn("انتهت مهلة انتظار ظهور ميكسات الفرد المشتركة (120 ثانية).")
        return False

    # إرسال أمر التحويل عبر حساب الفرد (مثل الـ HAR تماماً)
    transfer_url = "https://mab.etisalat.com.eg:11003/Saytar/rest/services/newTransfer/v2"
    transfer_payload = f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><newFamilyTransferRequest><distribute>false</distribute><msisdn>{member_dial}</msisdn><productName>Hekaya_XRP_MIX_Child_1</productName><quota>{member_mix_to_transfer}</quota><receiverMsisdn>{owner_dial}</receiverMsisdn><senderMsisdn>{member_dial}</senderMsisdn><type>UNITS</type></newFamilyTransferRequest>"
    transfer_headers = {'Content-Type': 'text/xml; charset=UTF-8', 'Accept': 'text/xml', 'Language': 'ar'}

    UI.info(f"جاري إرسال تحويل الـ {member_mix_to_transfer:,} ميكس من حساب الفرد إلى الأونر...")
    transfer_sent = False
    for t_attempt in range(1, 4):
        try:
            t_resp = execute_with_auto_refresh(
                member_session,
                lambda: member_session.session.post(transfer_url, data=transfer_payload, headers=transfer_headers, timeout=15)
            )
            validate_action_response(t_resp)
            UI.success("تم إرسال أمر التحويل بنجاح من حساب الفرد!")
            transfer_sent = True
            break
        except Exception as e:
            UI.warn(f"تعثر إرسال أمر التحويل (محاولة {t_attempt}/3): {e}")
            time.sleep(1)

    if not transfer_sent:
        UI.warn("فشل إرسال طلب التحويل من حساب الفرد بعد 3 محاولات.")
        return False

    # فحص التأكيد عبر حساب الفرد حتى تصبح ميكساته 0
    UI.info("جاري التحقق من حساب الفرد حتى التأكد من تصفير رصيده (0 ميكس)...")
    confirm_deadline = time.monotonic() + 30
    while time.monotonic() < confirm_deadline:
        try:
            c_resp = execute_with_auto_refresh(
                member_session,
                lambda: member_session.session.get(inquiry_url, params=inquiry_params, headers=inquiry_headers, timeout=10)
            )
            xml_text = c_resp.text
            idx = xml_text.find("<?xml")
            if idx != -1:
                xml_text = xml_text[idx:]
            c_root = ET.fromstring(xml_text)
            c_assigned = {}
            for item in c_root.findall(".//assigned"):
                d_elem = item.find("dial")
                v_elem = item.find("value")
                if d_elem is not None and d_elem.text and v_elem is not None and v_elem.text:
                    try:
                        c_assigned[normalize_phone_number(d_elem.text)] = int(v_elem.text)
                    except Exception:
                        pass

            if member_dial in c_assigned:
                rem_m = c_assigned[member_dial]
                if rem_m == 0:
                    UI.end_progress()
                    owner_now = c_assigned.get(owner_dial, "N/A")
                    UI.success(f"تم تأكيد تصفير رصيد الفرد بنجاح (0 ميكس) وانتقال الميكسات للأونر ({owner_now})!")
                    return True
                else:
                    UI.progress(f"في انتظار تصفير الفرد بالسيرفر (المتبقي حالياً: {rem_m:,})...")
        except Exception:
            pass
        time.sleep(1)

    UI.end_progress()
    UI.warn("تم التحويل ولكن انتهت مهلة التحقق من التصفير بحساب الفرد؛ المتابعة...")
    return True


def wait_for_member_refill(read_member_quota, timeout_seconds=300):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            member_quota = read_member_quota()
            if member_quota is not None and member_quota > 0:
                UI.end_progress()
                UI.success(f"اكتمل ريفييل كوتا الفرد بنجاح! الرصيد بعد الريفييل: {member_quota:,}")
                return member_quota
            UI.progress("في انتظار اكتمال ريفييل كوتا الفرد (الريفييل)...")
        except Exception:
            pass
        time.sleep(3)

    UI.end_progress()
    UI.warn("لم يمتلئ رصيد الفرد خلال 5 دقائق (لم يكتمل الريفييل).")
    return None


def wait_for_owner_quota_refresh(read_owner_quota, timeout_seconds=120):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            owner_quota = read_owner_quota()
            if owner_quota > 0:
                UI.end_progress()
                UI.success(f"تم نزول كوتا الباقة الجديدة للأونر بنجاح! (الرصيد: {owner_quota:,} ميكس)")
                return owner_quota
            UI.progress(f"في انتظار نزول كوتا الباقة الجديدة للأونر... (الرصيد: {owner_quota:,})")
        except Exception as e:
            UI.progress(f"فحص رصيد الأونر: {e}")
        time.sleep(0.5)

    UI.end_progress()
    UI.warn("انتهت مهلة انتظار كوتا الأونر؛ استكمال الفحص...")
    return 0


# ==============================================================================
# الخطوة الذكية لإضافة وربط الفرد بدورة الإنعاش
# ==============================================================================
def smart_add_and_link_member(owner_session, member_session, current_plan):
    owner_dial = owner_session.dial
    member_dial = member_session.dial

    UI.section("دورة إضافة وربط الفرد الذكية (مع الإنعاش التلقائي)")

    # 1. التأكد أن نظام الفرد الحالي هو "أهلاً أقوى كارت"
    UI.info("التحقق من نظام خط الفرد قبل البدء...")
    m_plan = get_current_plan_name(member_session)
    if "MINION" not in m_plan:
        UI.warn(f"نظام الفرد الحالي ({m_plan}) ليس أهلاً؛ التحويل إلى أهلاً أقوى كارت...")
        change_plan_until_applied(member_session, "14", "MINION", wait_seconds=60)
    UI.success("خط الفرد مستقر على نظام: أهلاً أقوى كارت.")

    # 2. إرسال طلب الإضافة ومتابعته
    invitation_received = False
    for refresh_round in range(1, 3):
        UI.info(f"دورة إرسال الدعوات - محاولة تنشيط #{refresh_round}")
        
        for attempt in range(1, 4):
            UI.info(f"إرسال طلب الإضافة للفرد (محاولة {attempt}/3)...")
            try:
                add_member(owner_session, member_dial, current_plan)
                UI.success("تم إرسال طلب الإضافة من حساب الأونر.")
            except Exception as e:
                UI.warn(f"ملاحظة عند إرسال الإضافة: {e}")

            UI.info("في انتظار وصول الدعوة لحساب الفرد (120 ثانية)...")
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                try:
                    pending = get_pending_requests(member_session)
                    for req in pending:
                        if req["senderDial"] == owner_dial:
                            UI.success("تم رصد وصول طلب الإضافة بنجاح في حساب الفرد!")
                            invitation_received = True
                            break
                except Exception:
                    pass
                if invitation_received:
                    break
                time.sleep(3)

            if invitation_received:
                break
            else:
                UI.warn(f"لم يصل الطلب خلال 120 ثانية (محاولة {attempt}/3).")

        if invitation_received:
            break

        # تنشيط حساب الفرد إذا لم تصل بعد 3 محاولات
        if refresh_round == 1:
            UI.warn("لم تصل الدعوة بعد 3 محاولات! تنشيط سيستم الفرد (270 ثم أهلاً)...")
            change_plan_until_applied(member_session, "270", "Hekaya_XRP_MIX_Parent_7", wait_seconds=60)
            time.sleep(2)
            change_plan_until_applied(member_session, "14", "MINION", wait_seconds=60)
            UI.success("تم تنشيط سيستم الفرد وإعادته لنظام أهلاً.")

    if not invitation_received:
        raise RuntimeError("تعذر توصيل طلب الإضافة للفرد بعد جميع محاولات الإنعاش والتنشيط!")

    # 3. تحويل نظام الفرد إلى حكاية 270 مع إعادة المحاولة
    UI.info("جاري تحويل نظام الفرد إلى حكاية 270...")
    change_plan_until_applied(member_session, "270", "Hekaya_XRP_MIX_Parent_7", wait_seconds=60)
    UI.success("تم تطبيق حكاية 270 على الفرد بنجاح.")

    # 4. تحويل نظام الفرد إلى حكاية إنترنت (HARLEY) مع إعادة المحاولة
    UI.info("جاري تحويل نظام الفرد إلى حكاية إنترنت (HARLEY)...")
    change_plan_until_applied(member_session, "HARLEY", "HARLEY_MINI_BUNDLE", wait_seconds=60)
    UI.success("تم تطبيق حكاية إنترنت على الفرد بنجاح.")

    # 5. قبول طلب الإضافة وتنبيه كود الهاتف اليدوي
    UI.info("جاري إرسال قبول الدعوة من حساب الفرد عبر السيرفر...")
    try:
        confirm_add_child(member_session, owner_dial)
        UI.success("تم إرسال أمر قبول الدعوة بنجاح.")
    except Exception as e:
        UI.warn(f"ملاحظة عند قبول الدعوة من السيرفر: {e}")

    UI.pause_alert(
        "📲 [مطلوب طلب كود القبول من شريحة الفرد]",
        f"يرجى الآن طلب الكود التالي من هاتف الفرد فوراً:\n\n      *319*1# \n\nالسكربت بانتظار تحول الخط تلقائياً إلى خط حكاية إضافي..."
    )

    # 6. انتظار تحول الفرد إلى خط حكاية إضافي
    UI.info("في انتظار تحول نظام الفرد إلى 'خط حكاية إضافي'...")
    child_confirmed = False
    for i in range(1, 120000000):
        try:
            curr = get_current_plan_name(member_session)
            if "Child" in curr or curr == "Hekaya_XRP_MIX_Child_1":
                child_confirmed = True
                UI.success(f"تم تأكيد انضمام الفرد رسمياً كنظام: {curr}")
                break
        except Exception:
            pass
        UI.progress(f"في انتظار اعتماد خط الفرد كإضافي [{i}/120000000 ث]...")
        time.sleep(1)

    if not child_confirmed:
        UI.warn("لم تظهر باقة الطفل عبر فحص النظام؛ جاري التحقق من الميكسات مباشرة...")

    # 7. سحب فائق السرعة للـ 15,400 ميكس فور ظهورها عبر حساب الفرد نفسه
    wait_for_child_quota_and_fast_pull(member_session, owner_dial, timeout_seconds=120)

    # 8. انتظار ريفييل الفرد بعد الربط
    UI.info("في انتظار ريفييل كوتا الفرد بعد الربط...")
    wait_for_member_refill(
        lambda: get_family_quotas(owner_session, current_plan, member_dial)["member"],
        timeout_seconds=300
    )


# ==============================================================================
# الدالة الرئيسية للتشغيل والتحكم في حلقة التكديس
# ==============================================================================
def main():
    global CHECKPOINT_FILE
    CHECKPOINT_FILE = new_checkpoint_path()
    UI.print_banner()
    UI.info(f"ملف متابعة الجلسة: {CHECKPOINT_FILE}")

    # تهيئة الـ 2 Sessions المعزولتين
    owner_session = AccountSession(name="المالك (Owner)")
    member_session = AccountSession(name="الفرد (Member)")

    progress = {
        "phase": "starting",
        "member_number": None,
        "target_mix": None,
        "current_plan": None,
        "current_mix": 0,
        "credentials": {
            "email": None,
            "password": None,
            "jwt": "",
            "cookie": "",
        },
        "dial": None,
        "pending_amount": 0,
    }
    save_progress(progress)

    try:
        # 1. إعداد حساب الأونر
        print(f"\n{Fore.YELLOW}{ar('اختر طريقة تسجيل دخول الأونر:')}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}1.{Style.RESET_ALL} {ar('الإيميل وكلمة المرور (تجديد تلقائي دائم للجلسة)')}")
        print(f"  {Fore.CYAN}2.{Style.RESET_ALL} {ar('الـ JWT Token والـ Cookie')}")
        login_mode = input(f"{Fore.GREEN}{ar('أدخل 1 أو 2')} : {Style.RESET_ALL}").strip()

        if login_mode == "1":
            owner_email = input(f"{Fore.WHITE}ENTER Owner Email : {Style.RESET_ALL}").strip()
            owner_password = input(f"{Fore.WHITE}ENTER Owner Password : {Style.RESET_ALL}").strip()
            code = owner_email + ":" + owner_password
            owner_xauth = "Basic " + base64.b64encode(code.encode("ascii")).decode("ascii")
            res_owner = keep_retrying("تسجيل دخول الأونر", lambda: login_with_plan(owner_xauth, session=owner_session.session), progress)
            owner_session.update_auth(res_owner["dial"], res_owner["jwt"], res_owner["cookies"], owner_xauth)
        else:
            jwt_token = input(f"{Fore.WHITE}Paste Owner JWT token: {Style.RESET_ALL}").strip()
            if jwt_token.lower().startswith("bearer "):
                jwt_token = jwt_token[7:].strip()
            cookie = input(f"{Fore.WHITE}Paste Owner Cookie value: {Style.RESET_ALL}").strip()
            if cookie.lower().startswith("cookie:"):
                cookie = cookie.split(":", 1)[1].strip()
            owner_num = normalize_phone_number(input(f"{Fore.WHITE}ENTER Owner Number : {Style.RESET_ALL}").strip())
            owner_session.update_auth(owner_num, jwt_token, cookie, xauth=None)
            owner_email = None
            owner_password = None

        # اختيار الخط المطلوب للأونر إذا كان الحساب يضم أكثر من رقم
        select_account_number(owner_session)

        progress["credentials"] = {
            "email": owner_email if login_mode == "1" else None,
            "password": owner_password if login_mode == "1" else None,
            "jwt": owner_session.jwt,
            "cookie": owner_session.cookies,
        }
        progress.update(phase="logged_in", dial=owner_session.dial)
        save_progress(progress)
        UI.success(f"تم اعتماد خط الأونر: {owner_session.dial}")

        # 2. إدخال حساب الفرد (إيميل وباسوورد فقط لتجديد التوكن التلقائي الدائم)
        print(f"\n{Fore.YELLOW}{ar('تسجيل دخول حساب الفرد (إيميل وكلمة مرور فقط):')}{Style.RESET_ALL}")
        m_email = input(f"{Fore.WHITE}ENTER Member Email : {Style.RESET_ALL}").strip()
        m_pass = input(f"{Fore.WHITE}ENTER Member Password : {Style.RESET_ALL}").strip()
        m_code = m_email + ":" + m_pass
        member_xauth = "Basic " + base64.b64encode(m_code.encode("ascii")).decode("ascii")
        res_mem = keep_retrying("تسجيل دخول الفرد", lambda: login_with_plan(member_xauth, session=member_session.session), progress)
        member_session.update_auth(res_mem["dial"], res_mem["jwt"], res_mem["cookies"], member_xauth)

        # اختيار الخط المطلوب للفرد إذا كان الحساب يضم أكثر من رقم
        select_account_number(member_session)
        member_number = member_session.dial
        UI.success(f"تم اعتماد خط الفرد: {member_number}")

        target_mix = int(input(f"\n{Fore.GREEN}{ar('أدخل الرصيد المستهدف للميكسات')} (Target Mix) : {Style.RESET_ALL}").strip())
        progress.update(target_mix=target_mix, member_number=member_number)
        save_progress(progress)

        def owner_retry(action_name, action):
            return keep_retrying(action_name, action, progress, account_session=owner_session)

        # 3. التحقق من باقة الأونر والتأكد من وجوده على حكاية
        UI.section("الخطوة 1: فحص وتثبيت باقة الأونر على حكاية")
        current_plan = owner_retry("قراءة باقة الأونر", lambda: get_current_plan_name(owner_session))
        if current_plan not in ["Hekaya_XRP_MIX_Parent_5", "Hekaya_XRP_MIX_Parent_6", "Hekaya_XRP_MIX_Parent_7"]:
            UI.warn(f"نظام الأونر الحالي ({current_plan}) ليس من عائلة حكاية. التحويل المؤقت عبر MINION...")
            current_plan = change_plan_until_applied(owner_session, "14", "MINION", wait_seconds=60)
            progress["phase"] = "migrating_to_270"
            save_progress(progress)
            current_plan = change_plan_until_applied(owner_session, "270", "Hekaya_XRP_MIX_Parent_7", wait_seconds=60)
            time.sleep(20)
        UI.success(f"الأونر مستقر على باقة حكاية: {current_plan}")

        # ----------------------------------------------------------------------
        # فحص كوتا الأونر على حكاية (التأكد من توفر 5,000 ميكس على الأقل للبدء)
        # ----------------------------------------------------------------------
        UI.info("جاري فحص رصيد ميكسات باقة الأونر للتأكد من إمكانية بدء العملية...")
        owner_initial_mixes = owner_retry("فحص ميكسات باقة الأونر", lambda: get_owner_plan_mixes(owner_session))
        UI.info(f"رصيد الميكسات الحالي في باقة الأونر: {owner_initial_mixes:,} ميكس")

        if owner_initial_mixes < 5000:
            UI.error(f"الميكسات لا تسمح بإكمال العملية! (الرصيد: {owner_initial_mixes:,} ميكس - المطلوب: 5,000 ميكس على الأقل).")
            progress["phase"] = "insufficient_mixes"
            save_progress(progress)
            sys.exit(1)
        UI.success(f"الرصيد كافي للبدء ({owner_initial_mixes:,} ميكس >= 5,000 ميكس).")

        # 4. فحص العائلة وإضافة الفرد إذا لم يكن مضافاً
        UI.section("الخطوة 2: فحص العائلة وإضافة الفرد")
        family_status = owner_retry("فحص العائلة", lambda: get_family_quotas(owner_session, current_plan, member_number))

        if member_number not in family_status["assigned"]:
            UI.warn("الفرد غير مضاف في العائلة حالياً. بدء الإضافة الذكية...")
            smart_add_and_link_member(owner_session, member_session, current_plan)
        else:
            UI.success(f"الفرد {member_number} موجود بالفعل في العائلة؛ المتابعة مباشرة.")

        # ======================================================================
        # حلقة ترحيل وتكديس الميكسات المحدثة
        # ======================================================================
        cycle_number = 0
        while True:
            cycle_number += 1

            quotas = owner_retry("قراءة الأرصدة الموحدة", lambda: get_family_quotas(owner_session, current_plan, member_number))
            owner_quota = quotas["owner"]
            member_quota = quotas["member"]
            accumulated_mix = owner_quota + member_quota

            progress.update(
                phase="cycle_start",
                current_plan=current_plan,
                current_mix=accumulated_mix,
                pending_amount=member_quota,
            )
            save_progress(progress)

            UI.clear_screen()
            UI.print_banner()
            UI.render_dashboard(
                cycle_number=cycle_number,
                owner_number=owner_session.dial,
                member_number=member_number,
                current_plan=current_plan,
                owner_mix=owner_quota,
                member_mix=member_quota,
                target_mix=target_mix
            )
            UI.section(f"دورة التكديس #{cycle_number} | أونر: {owner_quota:,} | فرد: {member_quota:,}")

            # ──────────────────────────────────────────────────────────────
            # 1. الأمان أولاً: التأكد القاطع من إيداع كامل رصيد الأونر عند الفرد وتصفير الأونر (0 ميكس)
            # ──────────────────────────────────────────────────────────────
            while owner_quota > 0:
                UI.info(f"تأمين الرصيد: جاري تحويل ميكسات الأونر ({owner_quota:,}) عند الفرد لتصفير الأونر قبل تبديل النظام...")
                post_deposit_q = transfer_with_balance_check(
                    owner_session, owner_session.dial, member_number, owner_quota, current_plan, member_number
                )
                owner_quota = post_deposit_q["owner"]
                member_quota = post_deposit_q["member"]
                if owner_quota > 0:
                    UI.warn(f"لا يزال متبقي لدى الأونر {owner_quota:,} ميكس! إعادة المحاولة حتى التصفير التام...")

            UI.success(f"تم تصفير الأونر بنجاح ({owner_quota:,} ميكس)، والرصيد مؤمن بالكامل عند الفرد ({member_quota:,} ميكس).")

            # ──────────────────────────────────────────────────────────────
            # 2. تبديل باقة الأونر (180 ↔ 270) لتنزيل كوتا جديدة
            # ──────────────────────────────────────────────────────────────
            if current_plan == "Hekaya_XRP_MIX_Parent_6":
                next_plan_code, next_plan_name = "270", "Hekaya_XRP_MIX_Parent_7"
            else:
                next_plan_code, next_plan_name = "180", "Hekaya_XRP_MIX_Parent_6"

            UI.info(f"جاري تبديل باقة الأونر إلى {next_plan_name} لتنزيل كوتا جديدة...")
            change_plan_until_applied(owner_session, next_plan_code, next_plan_name, wait_seconds=90, member_number=member_number)
            current_plan = next_plan_name

            # ──────────────────────────────────────────────────────────────
            # 3. انتظار نزول كوتا الباقة الجديدة للأونر
            # ──────────────────────────────────────────────────────────────
            UI.info("في انتظار نزول كوتا الباقة الجديدة للأونر...")
            wait_for_owner_quota_refresh(
                lambda: owner_retry("فحص كوتا الأونر", lambda: get_family_quotas(owner_session, current_plan, member_number)["owner"])
            )

            # ──────────────────────────────────────────────────────────────
            # 4. سحب ميكسات الفرد (الرصيد المخزن) فوراً إلى الأونر
            # ──────────────────────────────────────────────────────────────
            post_switch_q = owner_retry("فحص رصيد الفرد بعد التبديل", lambda: get_family_quotas(owner_session, current_plan, member_number))
            if post_switch_q["member"] > 0:
                UI.info(f"جاري سحب رصيد الفرد المخزن ({post_switch_q['member']:,} ميكس) إلى الأونر...")
                transfer_with_balance_check(owner_session, member_number, owner_session.dial, post_switch_q["member"], current_plan, member_number)

            # ──────────────────────────────────────────────────────────────
            # 5. انتظار ريفييل كوتا الفرد (0 ➔ Refill)
            # ──────────────────────────────────────────────────────────────
            UI.info("في انتظار اكتمال ريفييل كوتا الفرد...")
            refill_success_amount = wait_for_member_refill(
                lambda: keep_retrying(
                    "فحص ريفييل الفرد",
                    lambda: get_family_quotas(owner_session, current_plan, member_number)["member"],
                    progress, account_session=owner_session, max_attempts=1
                ),
                timeout_seconds=300
            )

            valid_refill_completed = (refill_success_amount is not None and refill_success_amount > 0)

            # ──────────────────────────────────────────────────────────────
            # 6. قراءة الرصيد الإجمالي الفعلي (أونر + ريفييل الفرد بدون سحب)
            # ──────────────────────────────────────────────────────────────
            tot_quotas = owner_retry("قراءة الأرصدة الإجمالية", lambda: get_family_quotas(owner_session, current_plan, member_number))
            owner_total = tot_quotas["owner"]
            member_total = tot_quotas["member"]
            total_mix_now = owner_total + member_total
            UI.info(f"الرصيد المحقق حالياً: {total_mix_now:,} ميكس (أونر: {owner_total:,} | ريفييل الفرد: {member_total:,})")

            # ──────────────────────────────────────────────────────────────
            # 7. فحص شرط إنهاء الهدف
            # ──────────────────────────────────────────────────────────────
            if total_mix_now >= target_mix:
                if valid_refill_completed:
                    UI.clear_screen()
                    UI.print_banner()
                    UI.pause_alert(
                        "🎯 [تم الوصول للهدف المطلوب مع ريفييل ناجح للفرد!]",
                        f"الرصيد الإجمالي: {total_mix_now:,} ميكس (الهدف: {target_mix:,}).\nسيتم الآن ترك الريفييل للفرد، وإخراجه من العائلة (لترتد الميكسات للأونر تلقائياً)، ثم تحويله لأهلاً..."
                    )

                    # إزالة الفرد والانتظار 60 ثانية لترتد الميكسات كلها للأونر تلقائياً
                    UI.info("جاري إزالة الفرد من العائلة (لترتد ميكسات الريفييل للأونر تلقائياً)...")
                    remove_member(owner_session, member_number, current_plan)
                    UI.info("الانتظار 60 ثانية لتأكيد خروج الفرد واستقرار الرصيد للأونر...")
                    time.sleep(60)

                    # تحويل نظام الفرد إلى أهلاً أقوى كارت (MINION)
                    UI.info("جاري تجديد جلسة الفرد وتأكيد اختياره للخط قبل تحويله لأهلاً...")
                    try:
                        member_session.refresh_if_needed()
                    except Exception as ref_err:
                        UI.warn(f"ملاحظة عند تجديد جلسة الفرد: {ref_err}")

                    UI.info("جاري تحويل نظام الفرد إلى أهلاً أقوى كارت (MINION)...")
                    try:
                        change_plan_until_applied(member_session, "14", "MINION", wait_seconds=60)
                        UI.success("تم تحويل نظام الفرد بنجاح إلى أهلاً أقوى كارت!")
                    except Exception as e:
                        UI.warn(f"تنبيه أثناء تحويل الفرد لأهلاً: {e}")

                    current_mix = total_mix_now
                    break
                else:
                    UI.warn(f"تم بلوغ التارجت ({total_mix_now:,} ميكس) ولكن الريفييل لم يكتمل في هذه الدورة! استمرار دورة إضافية لضمان الريفييل...")

            # ──────────────────────────────────────────────────────────────
            # 8. إذا لم نصل للتارجت: تحويل كامل ميكسات الأونر عند الفرد كخزنة والتحقق بالسيرفر
            # ──────────────────────────────────────────────────────────────
            if owner_total > 0:
                UI.info(f"جاري تحويل كامل ميكسات الأونر ({owner_total:,} ميكس) عند الفرد كخزنة وتأكيد انعكاس الرصيد...")
                transfer_with_balance_check(
                    sender_session=owner_session,
                    sender_number=owner_session.dial,
                    receiver_number=member_number,
                    amount=owner_total,
                    current_plan=current_plan,
                    member_number=member_number
                )

            pause_controller.check_and_wait("نهاية دورة التكديس", progress)

        # نهاية العملية
        final_1 = ar(f"الرصيد النهائي المحقق: {current_mix:,} ميكس")
        final_2 = ar(f"الباقة الحالية للأونر: {current_plan}")
        final_3 = ar("تم إخراج الفرد بنجاح، وتحويل نظامه إلى أهلاً أقوى كارت.")
        
        owner_display_email = owner_email if owner_email else "تسجيل عبر Token"
        owner_display_pass = owner_password if owner_password else "N/A"
        owner_display_dial = owner_session.dial or "N/A"

        print(Fore.GREEN + Style.BRIGHT + f"""
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║                 🎉 {ar("تم اكتمال العملية بنجاح تام!")}                    ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  {final_1}
  ║  {final_2}
  ║  {final_3}
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  📱 {ar("بيانات حساب الأونر (Owner Info):")}
  ║     - {ar("رقم الخط:")} {owner_display_dial}
  ║     - {ar("الإيميل:")} {owner_display_email}
  ║     - {ar("الباسورد:")} {owner_display_pass}
  ║     - {ar("إجمالي الميكسات الكلي:")} {current_mix:,} {ar("ميكس")}
  ║
  ║  📱 {ar("بيانات حساب الفرد (Member Info):")}
  ║     - {ar("رقم الخط:")} {member_number}
  ║     - {ar("الإيميل:")} {m_email}
  ║     - {ar("الباسورد:")} {m_pass}
  ╚═══════════════════════════════════════════════════════════════════════╝
""" + Style.RESET_ALL)

    except KeyboardInterrupt:
        UI.end_progress()
        progress["phase"] = "interrupted"
        save_progress(progress)
        UI.warn("تم إيقاف السكربت يدوياً.")
    except Exception as error:
        import traceback
        traceback.print_exc()
        progress["phase"] = "error"
        progress["error"] = f"{type(error).__name__}: {error}"
        save_progress(progress)
        UI.error(f"خطأ غير متوقع: {error}")


if __name__ == "__main__":
    main()
