def generate_full_html(body_content, config):
    """
    Génère la page HTML complète avec le CSS (Tooltips, styles Dofus) et le JS.
    """
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');

        body {{
            background-color: #1a1a1a;
            color: #c0c0c0;
            font-family: 'Segoe UI', sans-serif;
            font-size: {config['font_size']}px;
            margin: 20px;
            line-height: 1.5;
            padding-bottom: 50px;
        }}

        a {{ color: #4da6ff; text-decoration: none; cursor: pointer; }}
        a:hover {{ text-decoration: underline; }}

        /* --- STYLES TAGS --- */
        span[class*="tag-quest"] {{ color: #ff76d7; font-weight: bold; }}
        span[class*="tag-item"] {{ color: #ffcc00; font-weight: bold; }}
        span[class*="tag-monster"] {{ color: #ff5e5e; font-weight: bold; }}
        span[class*="tag-dungeon"] {{ color: #00ff00; font-weight: bold; }}
        span[style*="color: rgb(98, 172, 255)"] {{ color: #4da6ff !important; font-weight: bold; font-size: 1.1em; }}

        /* IMAGES */
        span[class*="tag-quest"] img {{ width: 18px; vertical-align: text-bottom; margin-right: 4px; }}
        span[class*="tag-item"] img {{ width: 24px; vertical-align: middle; margin-right: 4px; }}
        span[class*="tag-monster"] img {{ width: 32px; vertical-align: middle; margin-right: 4px; }}
        img {{ vertical-align: middle; width: 20px; height: auto; }} 

        .img-large {{ 
            display: block; margin: 15px auto; max-width: 100%; 
            width: {config['img_large_width']}px; 
            border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }}

        /* LISTES & CHECKBOXES */
        ul {{ list-style-type: none; padding-left: 0; margin-top: 10px; }}
        li {{ margin-bottom: 6px; display: flex; align-items: center; }}

        .checkbox-row {{ display: flex; justify-content: flex-start; align-items: center; }}
        input[type="checkbox"] {{ width: 16px; height: 16px; cursor: pointer; margin-right: 12px; margin-top: 0; }}
        .cb-text {{ flex: 1; }}

        /* BLOCS DE QUÊTE */
        .quest-block {{
            background-color: #202025; border: 1px solid #333;
            border-radius: 6px; margin: 10px 0; padding: 10px; position: relative;
        }}

        /* --- TOOLTIPS (FIXED TOP-RIGHT) --- */
        [data-tooltip] {{ position: relative; cursor: help; border-bottom: 1px dotted rgba(77, 166, 255, 0.4); }}

        [data-tooltip]:hover::after {{
            content: "📜 " attr(data-tooltip);
            position: fixed; top: 15px; right: 15px;
            background: #252535; color: #ffffff;
            font-family: 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600;
            border-radius: 12px; border: 1px solid #4da6ff;
            padding: 8px 12px; white-space: nowrap; z-index: 9999;
            box-shadow: 0 5px 15px rgba(0,0,0,0.6);
            opacity: 0; visibility: hidden; transition: opacity 0.2s; pointer-events: none;
        }}

        [data-tooltip]:hover::after {{ opacity: 1; visibility: visible; }}
        [data-tooltip]::before {{ display: none; }}

        .guide-step {{ color: #b19cd9; font-weight: bold; }}
    </style>
    """

    script = """
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script>
        var backend;
        new QWebChannel(qt.webChannelTransport, function (channel) {
            backend = channel.objects.pyBridge;
        });
        function onLinkClick(link) { if (backend) backend.handleLink(link); }
        function onCheckboxClick(cbId, checked) { if (backend) backend.handleLink('CB:' + cbId + ':' + checked); }
    </script>
    """

    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{css}{script}</head><body>{body_content}</body></html>"