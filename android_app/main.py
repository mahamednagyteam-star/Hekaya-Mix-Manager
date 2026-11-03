import builtins
import queue
import sys
import threading
import webbrowser

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

import mix_v3


BG = (0.035, 0.055, 0.065, 1)
PANEL = (0.075, 0.105, 0.115, 1)
PANEL_ALT = (0.09, 0.13, 0.14, 1)
GREEN = (0.12, 0.72, 0.48, 1)
GREEN_DARK = (0.07, 0.43, 0.31, 1)
TEXT = (0.92, 0.96, 0.94, 1)
MUTED = (0.57, 0.68, 0.66, 1)
RED = (0.85, 0.30, 0.28, 1)


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
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"
        self.io = MobileIO(self)
        self.worker = None
        self.original_input = builtins.input
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        root = BoxLayout(orientation="vertical", padding=[dp(14), dp(12)], spacing=dp(10))
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(66), spacing=dp(10))
        brand = BoxLayout(orientation="vertical", spacing=dp(1))
        brand.add_widget(Label(
            text="[b]HEKAYA[/b] [color=35D69A]MIX[/color]",
            markup=True, font_size=dp(22), color=TEXT, halign="left",
            valign="middle", size_hint_y=0.65,
        ))
        brand.add_widget(Label(
            text="إدارة ومتابعة الباقة في مكان واحد",
            font_size=dp(11), color=MUTED, halign="left",
            valign="top", size_hint_y=0.35,
        ))
        header.add_widget(brand)
        self.state = Label(
            text="● جاهز", color=GREEN, font_size=dp(12),
            size_hint_x=None, width=dp(105), halign="right",
        )
        header.add_widget(self.state)
        root.add_widget(header)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_type=["bars", "content"])
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=[0, 0, 0, dp(8)])
        body.bind(minimum_height=body.setter("height"))

        intro = self.panel(orientation="vertical", padding=dp(14), spacing=dp(5))
        intro.add_widget(Label(
            text="[b]مرحباً بك 👋[/b]", markup=True, color=TEXT,
            font_size=dp(18), halign="right", size_hint_y=None, height=dp(28),
        ))
        intro.add_widget(Label(
            text="أدخل بيانات الحساب ثم ابدأ جلسة الإدارة. يمكنك متابعة الرسائل والحالة من سجل التشغيل.",
            color=MUTED, font_size=dp(12), halign="right",
            valign="middle", size_hint_y=None, height=dp(42),
            text_size=(Window.width - dp(64), None),
        ))
        body.add_widget(intro)

        form_card = self.panel(orientation="vertical", padding=dp(13), spacing=dp(8))
        form_card.add_widget(self.section_title("بيانات الحساب"))
        self.login_mode = Spinner(
            text="الإيميل وكلمة المرور",
            values=("الإيميل وكلمة المرور", "JWT و Cookie"),
            size_hint_y=None, height=dp(46),
            background_normal="", background_color=PANEL_ALT,
            color=TEXT, font_size=dp(13),
        )
        form_card.add_widget(self.login_mode)
        self.owner_email = self.field("إيميل الأونر", form=form_card)
        self.owner_password = self.field("كلمة مرور الأونر", password=True, form=form_card)
        self.owner_jwt = self.field("Owner JWT Token", password=True, form=form_card, disabled=True)
        self.owner_cookie = self.field("Owner Cookie", password=True, form=form_card, disabled=True)
        self.owner_number = self.field("رقم الأونر عند استخدام Token", form=form_card, disabled=True)
        form_card.add_widget(self.section_title("بيانات الفرد والهدف"))
        self.member_email = self.field("إيميل الفرد", form=form_card)
        self.member_password = self.field("كلمة مرور الفرد", password=True, form=form_card)
        self.target = self.field("الرصيد المستهدف للميكسات", form=form_card, input_filter="int")
        body.add_widget(form_card)
        self.login_mode.bind(text=self.toggle_login_fields)

        actions = self.panel(orientation="vertical", padding=dp(13), spacing=dp(8))
        actions.add_widget(self.section_title("التحكم في الجلسة"))
        controls = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(7))
        self.start_btn = self.action_button("بدء التشغيل", GREEN_DARK)
        self.pause_btn = self.action_button("إيقاف مؤقت", PANEL_ALT, disabled=True)
        self.resume_btn = self.action_button("استئناف", PANEL_ALT, disabled=True)
        self.start_btn.bind(on_release=self.start_run)
        self.pause_btn.bind(on_release=self.pause_run)
        self.resume_btn.bind(on_release=self.resume_run)
        controls.add_widget(self.start_btn)
        controls.add_widget(self.pause_btn)
        controls.add_widget(self.resume_btn)
        actions.add_widget(controls)

        self.extra_input = self.field("إدخال إضافي عند ظهور طلب...", form=None)
        self.submit_btn = self.action_button("إرسال الإدخال", GREEN_DARK, disabled=True)
        self.submit_btn.size_hint_y = None
        self.submit_btn.height = dp(44)
        self.submit_btn.bind(on_release=self.submit_extra)
        actions.add_widget(self.extra_input)
        actions.add_widget(self.submit_btn)
        body.add_widget(actions)

        log_card = self.panel(orientation="vertical", padding=dp(12), spacing=dp(7))
        log_head = BoxLayout(size_hint_y=None, height=dp(28))
        log_head.add_widget(self.section_title("سجل التشغيل"))
        log_head.add_widget(Label(text="LIVE", color=GREEN, font_size=dp(10), halign="right"))
        log_card.add_widget(log_head)
        log_scroll = ScrollView(size_hint_y=None, height=dp(190), do_scroll_x=False)
        self.log = Label(
            text="[color=71847F]لا توجد رسائل بعد...[/color]", markup=True,
            size_hint_y=None, halign="right", valign="top",
        )
        self.log.bind(texture_size=self.log_texture)
        log_scroll.add_widget(self.log)
        log_card.add_widget(log_scroll)
        self.scroll = log_scroll
        body.add_widget(log_card)

        links = Label(
            text="[ref=developer][color=35D69A]المطور: @Mando_js[/color][/ref]    •    [ref=channel][color=35D69A]قناة الأدوات[/color][/ref]",
            markup=True, size_hint_y=None, height=dp(32), font_size=dp(11), halign="center",
        )
        links.bind(on_ref_press=self.open_link)
        body.add_widget(links)
        scroll.add_widget(body)
        root.add_widget(scroll)
        return root

    def panel(self, **kwargs):
        box = BoxLayout(**kwargs)
        with box.canvas.before:
            Color(*PANEL)
            box._panel_bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(13)])
        box.bind(pos=self._update_panel, size=self._update_panel)
        return box

    def _update_panel(self, widget, *_):
        widget._panel_bg.pos = widget.pos
        widget._panel_bg.size = widget.size

    def section_title(self, title):
        return Label(
            text=f"[b]{title}[/b]", markup=True, color=TEXT,
            font_size=dp(14), halign="right", valign="middle",
            size_hint_y=None, height=dp(28),
        )

    def field(self, hint, password=False, form=None, disabled=False, input_filter=None):
        widget = TextInput(
            hint_text=hint, password=password, multiline=False,
            size_hint_y=None, height=dp(45), disabled=disabled,
            input_filter=input_filter, padding=[dp(12), dp(12)],
            background_normal="", background_active="",
            background_color=PANEL_ALT if not disabled else (0.06, 0.08, 0.09, 1),
            foreground_color=TEXT, hint_text_color=MUTED,
            cursor_color=GREEN, selection_color=GREEN_DARK,
            font_size=dp(13),
        )
        if form is not None:
            form.add_widget(widget)
        return widget

    def action_button(self, title, color, disabled=False):
        return Button(
            text=title, disabled=disabled, background_normal="",
            background_down="", background_color=color,
            color=TEXT, font_size=dp(12), bold=True,
        )

    def open_link(self, _label, ref):
        urls = {
            "developer": "https://t.me/Mando_js",
            "channel": "https://t.me/PyToolsArab",
        }
        webbrowser.open(urls[ref])

    def toggle_login_fields(self, *_):
        token = self.login_mode.text == "JWT و Cookie"
        for widget in (self.owner_email, self.owner_password):
            widget.disabled = token
        for widget in (self.owner_jwt, self.owner_cookie, self.owner_number):
            widget.disabled = not token

    def log_texture(self, *_):
        if self.log.parent:
            self.log.text_size = (self.log.parent.width - dp(12), None)

    def add_log(self, text, kind="output"):
        def update(_dt):
            clean = str(text).replace("\x1b", "")
            if not clean.strip():
                return
            if self.log.text.startswith("[color=71847F]"):
                self.log.text = ""
            if kind == "prompt":
                line = f"[color=35D69A]› {clean}[/color]"
            else:
                line = f"[color=CBD8D3]{clean}[/color]"
            self.log.text += line
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
        self.state.text = "● قيد التشغيل"
        self.state.color = GREEN
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
        self.state.text = "● انتهى"
        self.state.color = MUTED
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
        self.state.text = "● متوقف مؤقتاً"
        self.state.color = (0.95, 0.68, 0.25, 1)

    def resume_run(self, *_):
        mix_v3.pause_controller.request_resume()
        self.pause_btn.disabled = False
        self.resume_btn.disabled = True
        self.state.text = "● قيد التشغيل"
        self.state.color = GREEN

    def on_stop(self):
        builtins.input = self.original_input
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


if __name__ == "__main__":
    HekayaApp().run()
