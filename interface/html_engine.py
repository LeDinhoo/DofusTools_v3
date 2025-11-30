import tkinter as tk
from tkinter import scrolledtext
import re
import os
import threading
import urllib.request
import time
from html.parser import HTMLParser
from .controls import CustomCheckbox


class HTMLRenderParser(HTMLParser):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.tags_stack = []
        self.current_color = None
        self.current_context = None
        self.current_link_id = None
        self.is_bold = False
        self.in_list_item = False
        self.in_image_span = False
        self.ignored_tags = {'input', 'label', 'meta', 'script', 'style', 'link', 'head', 'title'}
        self.img_sizes = {"large": 350, "small": 300, "monster": 36, "item": 24, "quest": 18, "default": 18}
        self.type_icons = {"dungeon": "💀", "quest": "📜", "item": "🎒", "monster": "👹", "npc": "👤", "job": "🔨"}

    def _clean_data(self, text):
        replacements = {
            # Suppression complète des émojis chiffres pour éviter les artefacts "1.", "2." collés au texte
            "1️⃣": "", "2️⃣": "", "3️⃣": "", "4️⃣": "", "5️⃣": "",
            "6️⃣": "", "7️⃣": "", "8️⃣": "", "9️⃣": "", "0️⃣": "",
            "🔟": "", "⚠️": "/!\\", "👉": "->", "👈": "<-",
            "🌽": "", "🥩": "", "☎️": "", "📖": ""
        }
        for k, v in replacements.items(): text = text.replace(k, v)
        return text

    def handle_starttag(self, tag, attrs):
        if tag in self.ignored_tags: return
        self.tags_stack.append(tag)
        attrs_dict = dict(attrs)

        style = attrs_dict.get('style', '')
        if 'color' in style:
            color_match = re.search(r'color:\s*([^;"]+)', style)
            if color_match:
                col = color_match.group(1).strip()
                rgb_match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', col)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups())
                    col = f'#{r:02x}{g:02x}{b:02x}'
                self.current_color = col

        classes = attrs_dict.get('class', '').split()
        if 'tag-quest' in classes:
            self.current_color = '#ff66cc'; self.current_context = 'quest'
        elif 'tag-dungeon' in classes:
            self.current_color = '#00ff00'; self.current_context = 'dungeon'
        elif 'tag-item' in classes:
            self.current_color = '#cd853f'; self.current_context = 'item'
        elif 'tag-monster' in classes:
            self.current_color = '#ff4444'; self.current_context = 'monster'
        elif 'guide-step' in classes:
            self.current_color = '#b19cd9'
            gid = attrs_dict.get('guideid')
            step_num = attrs_dict.get('stepnumber')
            if gid == "0" and step_num:
                self.current_link_id = f"STEP:{step_num}"
            elif gid and gid != "0":
                self.current_link_id = f"GUIDE:{gid}"

        image_url_span = attrs_dict.get('imageurl')
        src_img = attrs_dict.get('src')
        data_type = attrs_dict.get('type')

        if tag == 'span' and image_url_span:
            type_check = data_type if data_type else self.current_context
            target_h = self.img_sizes.get(type_check, self.img_sizes["default"])
            self.text_widget.add_async_image(image_url_span, target_height=target_h)
            self.in_image_span = True
        elif tag == 'img':
            if src_img and not self.in_image_span:
                if 'img-large' in classes:
                    self.text_widget.insert("end", "\n")
                    self.text_widget.add_async_image(src_img, fit_width=True)
                    self.text_widget.insert("end", "\n")
                elif 'img-small' in classes:
                    self.text_widget.insert("end", "\n")
                    self.text_widget.add_async_image(src_img, target_height=self.img_sizes["small"])
                    self.text_widget.insert("end", "\n")
                else:
                    target_h = self.img_sizes.get(self.current_context, self.img_sizes["default"])
                    self.text_widget.add_async_image(src_img, target_height=target_h)
        elif tag == 'span' and data_type and not image_url_span:
            emoji = self.type_icons.get(data_type, "")
            if emoji: self.text_widget.insert("end", f"{emoji} ")

        if tag in ['b', 'strong']: self.is_bold = True
        if tag == 'li':
            self.in_list_item = True
            self.text_widget.insert("end", "\n  ")
            self.text_widget.add_checkbox()
            self.text_widget.insert("end", " ")
        if tag == 'br': self.text_widget.insert("end", "\n")

    def handle_endtag(self, tag):
        if tag in self.ignored_tags: return
        if self.tags_stack:
            if tag in self.tags_stack:
                while self.tags_stack and self.tags_stack[-1] != tag: self.tags_stack.pop()
                if self.tags_stack: self.tags_stack.pop()

        if tag in ['b', 'strong']: self.is_bold = False
        if tag in ['p', 'div']:
            if not self.in_list_item: self.text_widget.insert("end", "\n")
            self.current_color = None;
            self.current_context = None
        if tag == 'li': self.in_list_item = False; self.text_widget.insert("end", "\n")
        if tag == 'span': self.current_color = None; self.current_context = None; self.current_link_id = None; self.in_image_span = False

    def handle_data(self, data):
        if not data.strip() and not self.tags_stack: return
        clean_text = self._clean_data(data)
        if not clean_text: return

        tags = []
        if self.is_bold: tags.append("bold")
        if self.current_color:
            color_tag = f"color_{self.current_color}"
            self.text_widget.tag_config(color_tag, foreground=self.current_color)
            tags.append(color_tag)
        if any(t.startswith('h') for t in self.tags_stack): tags.append("header")

        if self.current_link_id:
            link_tag = f"LINK_{self.current_link_id}_{os.urandom(4).hex()}"
            tags.append(link_tag)
            self.text_widget.tag_bind(link_tag, "<Enter>", lambda e: self.text_widget.config(cursor="hand2"))
            self.text_widget.tag_bind(link_tag, "<Leave>", lambda e: self.text_widget.config(cursor=""))
            if self.text_widget.on_link_click:
                self.text_widget.tag_bind(link_tag, "<Button-1>",
                                          lambda e, lid=self.current_link_id: self.text_widget.on_link_click(lid))

        self.text_widget.insert("end", clean_text, tuple(tags))


class RichTextDisplay(scrolledtext.ScrolledText):
    def __init__(self, master, on_link_click=None, **kwargs):
        # On force les couleurs par défaut pour le thème sombre
        super().__init__(master, bg="#1a1a1a", fg="#c0c0c0", insertbackground="white",
                         bd=0, padx=15, pady=15, font=("Segoe UI", 11), wrap="word", **kwargs)

        # Scrollbar native visible par défaut

        self.on_link_click = on_link_click
        self.tag_config("bold", font=("Segoe UI", 11, "bold"))
        self.tag_config("header", font=("Segoe UI", 14, "bold"), foreground="#ffffff")
        self.images_refs = []
        self.checkboxes = []
        self.state = 'disabled'

    def set_html(self, html_content):
        self.config(state='normal')
        self.delete(1.0, tk.END)
        self.images_refs.clear()
        self.checkboxes.clear()
        if not html_content:
            self.config(state='disabled')
            return
        parser = HTMLRenderParser(self)
        try:
            parser.feed(html_content)
        except Exception as e:
            self.insert(tk.END, f"Erreur rendu : {e}\n")
        self.config(state='disabled')

    def add_checkbox(self):
        cb = CustomCheckbox(self, size=14, bg_color="#1a1a1a")
        self.window_create("end", window=cb, align="center")
        self.checkboxes.append(cb)

    def add_async_image(self, url, target_height=24, fit_width=False):
        if not url: return
        filename = re.sub(r'[<>:"/\\|?*]', '_', url.split('/')[-1])
        if len(filename) > 50: filename = filename[-50:]
        cache_dir = "assets"
        cache_path = os.path.join(cache_dir, filename)
        mark_name = f"img_{len(self.images_refs)}_{time.time()}"
        self.mark_set(mark_name, "insert")
        self.mark_gravity(mark_name, tk.LEFT)

        def _fetch():
            if not os.path.exists(cache_dir): os.makedirs(cache_dir, exist_ok=True)
            try:
                data = None
                if os.path.exists(cache_path):
                    with open(cache_path, "rb") as f:
                        data = f.read()
                else:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as u:
                        data = u.read()
                        if data:
                            with open(cache_path, "wb") as f: f.write(data)
                if data: self.after(0, lambda: self._show_image(mark_name, data, target_height, fit_width))
            except Exception as e:
                print(f"Erreur image {url}: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_image(self, mark_name, data, target_height, fit_width=False):
        try:
            photo = tk.PhotoImage(data=data)
            if fit_width:
                current_w = self.winfo_width()
                if current_w < 100: current_w = 480
                target_w = current_w - 50
                img_w = photo.width()
                if img_w > target_w:
                    factor = int(img_w / target_w) + 1
                    if factor > 1: photo = photo.subsample(factor, factor)
            else:
                h = photo.height()
                if h > target_height:
                    factor = int(h / target_height)
                    if factor > 1: photo = photo.subsample(factor, factor)
            self.images_refs.append(photo)
            was_disabled = (self['state'] == 'disabled')
            if was_disabled: self.config(state='normal')
            self.image_create(mark_name, image=photo)
            self.insert(mark_name, " ")
            if was_disabled: self.config(state='disabled')
        except Exception as e:
            print(f"Erreur affichage image: {e}")