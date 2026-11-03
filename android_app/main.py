import builtins
import queue
import sys
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

import mix_v3


class MobileIO:
    def __init__(self, app):
        self.app = app
        self.answers = queue.Queue()

    def input(self, prompt=""):
        self.app.add_log(prompt, "prompt")
        return self.answers.get()

    def submit(self, value):
        self.answers.put(value)


class LogWriter:
    def __init__(self, app, stream):
        self.app = app
        self.stream = stream

    def write(self, text):
        if text:
            self.app.add_log(text, "output")
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return False


class HekayaApp(App):
    title = "Hekaya Mix Manager"

    def build(self):
        Window.softinput_mode = "below_target"
        self.io = MobileIO(self)
        self.worker = None
        self.original_input = builtins.input
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        header = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        header.add_widget(Label(text="[b]Hekaya Mix Manager[/b]", markup=True, font_size=dp(20), halign="left"))
        self.state = Label(text="جاهز", size_hint_x=0.35, color=(0.2, 0.8, 0.45, 1))
        header.add_widget(self.state)
        root.add_widget(header)

        form = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        form.bind(minimum_height=form.setter("height"))
        self.login_mode = Spinner(text="الإيميل وكلمة المرور", values=("الإيميل وكلمة المرور", "JWT و Cookie"), size_hint_y=None, height=dp(42))
        form.add_widget(self.login_mode)
        self.owner_email = self.field("إيميل الأونر", password=False, form=form)
        self.owner_password = self.field("باسورد الأونر", password=True, form=form)
        self.owner_jwt = self.field("Owner JWT Token", password=True, form=form, disabled=True)
        self.owner_cookie = self.field("Owner Cookie", password=True, form=form, disabled=True)
        self.owner_number = self.field("رقم الأونر عند استخدام Token", form=form, disabled=True)
        self.member_email = self.field("إيميل الفرد", form=form)
        self.member_password = self.field("باسورد الفرد", password=True, form=form)
        self.target = self.field("الرصيد المستهدف للميكسات", form=form, input_filter="int")
        root.add_widget(form)
        self.login_mode.bind(text=self.toggle_login_fields)

        controls = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self.start_btn = Button(text="بدء التشغيل")
        self.pause_btn = Button(text="إيقاف مؤقت", disabled=True)
        self.resume_btn = Button(text="استئناف", disabled=True)
        self.start_btn.bind(on_release=self.start_run)
        self.pause_btn.bind(on_release=self.pause_run)
        self.resume_btn.bind(on_release=self.resume_run)
        controls.add_widget(self.start_btn)
        controls.add_widget(self.pause_btn)
        controls.add_widget(self.resume_btn)
        root.add_widget(controls)

        self.extra_input = TextInput(hint_text="إدخال إضافي عند طلب اختيار رقم أو متابعة", multiline=False, size_hint_y=None, height=dp(42))
        self.submit_btn = Button(text="إرسال الإدخال", size_hint_y=None, height=dp(42), disabled=True)
        self.submit_btn.bind(on_release=self.submit_extra)
        root.add_widget(self.extra_input)
        root.add_widget(self.submit_btn)

        scroll = ScrollView()
        self.log = Label(text="", markup=True, size_hint_y=None, halign="right", valign="top", text_size=(None, None))
        self.log.bind(texture_size=self.log_texture)
        scroll.add_widget(self.log)
        root.add_widget(scroll)
        self.scroll = scroll
        return root

    def field(self, hint, password=False, form=None, disabled=False, input_filter=None):
        w = TextInput(hint_text=hint, password=password, multiline=False, size_hint_y=None, height=dp(40), disabled=disabled, input_filter=input_filter)
        if form is not None:
            form.add_widget(w)
        return w

    def toggle_login_fields(self, *_):
        token = self.login_mode.text == "JWT و Cookie"
        for w in (self.owner_email, self.owner_password):
            w.disabled = token
        for w in (self.owner_jwt, self.owner_cookie, self.owner_number):
            w.disabled = not token

    def log_texture(self, *_):
        self.log.text_size = (self.log.parent.width - dp(16), None)

    def add_log(self, text, kind="output"):
        def update(_dt):
            clean = str(text).replace("\x1b", "")
            if not clean.strip():
                return
            prefix = "[b]›[/b] " if kind == "prompt" else ""
            self.log.text += prefix + clean
            if not clean.endswith("\n"):
                self.log.text += "\n"
            self.scroll.scroll_y = 0
        Clock.schedule_once(update, 0)

    def values(self):
        if self.login_mode.text == "JWT و Cookie":
            return ["2", self.owner_jwt.text.strip(), self.owner_cookie.text.strip(), self.owner_number.text.strip(), self.member_email.text.strip(), self.member_password.text, self.target.text.strip()]
        return ["1", self.owner_email.text.strip(), self.owner_password.text, self.member_email.text.strip(), self.member_password.text, self.target.text.strip()]

    def start_run(self, *_):
        if self.worker and self.worker.is_alive():
            return
        values = self.values()
        if self.login_mode.text == "JWT و Cookie":
            if not all(values[1:]):
                return self.add_log("يرجى إكمال بيانات JWT وCookie ورقم الأونر والفرد والهدف.", "prompt")
        elif not all(values[1:]):
            return self.add_log("يرجى إكمال بيانات الأونر والفرد والهدف.", "prompt")
        self.start_btn.disabled = True
        self.pause_btn.disabled = False
        self.resume_btn.disabled = True
        self.submit_btn.disabled = True
        self.state.text = "قيد التشغيل"
        self.worker = threading.Thread(target=self.run_script, args=(values,), daemon=True)
        self.worker.start()

    def run_script(self, values):
        try:
            builtins.input = self.io.input
            sys.stdout = LogWriter(self, self.original_stdout)
            sys.stderr = LogWriter(self, self.original_stderr)
            for value in values:
                self.io.submit(value)
            mix_v3.main()
        except Exception as exc:
            self.add_log(f"خطأ: {type(exc).__name__}: {exc}", "prompt")
        finally:
            builtins.input = self.original_input
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            Clock.schedule_once(self.finished, 0)

    def finished(self, *_):
        self.state.text = "انتهى"
        self.start_btn.disabled = False
        self.pause_btn.disabled = True
        self.resume_btn.disabled = True
        self.submit_btn.disabled = True

    def submit_extra(self, *_):
        value = self.extra_input.text.strip()
        if value:
            self.io.submit(value)
            self.extra_input.text = ""
            self.submit_btn.disabled = True

    def pause_run(self, *_):
        mix_v3.pause_controller.request_pause()
        self.pause_btn.disabled = True
        self.resume_btn.disabled = False
        self.state.text = "متوقف مؤقتًا"

    def resume_run(self, *_):
        mix_v3.pause_controller.request_resume()
        self.pause_btn.disabled = False
        self.resume_btn.disabled = True
        self.state.text = "قيد التشغيل"

    def on_stop(self):
        builtins.input = self.original_input
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


if __name__ == "__main__":
    HekayaApp().run()
