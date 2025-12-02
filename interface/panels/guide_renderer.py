import os


def generate_full_html(body_content, config):
    """
    Génère la page HTML en chargeant le CSS depuis un fichier externe.
    """

    # Chemin vers le fichier CSS
    # On suppose que le fichier est dans interface/assets/style.css par rapport à la racine du projet
    # Il est plus robuste d'utiliser un chemin relatif basé sur l'emplacement de ce fichier
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # On remonte d'un niveau (interface/panels -> interface) puis on va dans assets
    css_path = os.path.join(current_dir, "assets", "style.css")
    css_content = ""

    if os.path.exists(css_path):
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
        except Exception as e:
            print(f"Erreur lecture CSS: {e}")
            # Fallback minimaliste
            css_content = """
            body { 
                background-color: #1a1a1a; 
                color: #c0c0c0; 
                font-family: 'Segoe UI', sans-serif;
                margin: 0; padding: 20px;
            }
            """
    else:
        print(f"Fichier CSS introuvable: {css_path}")
        css_content = "body { background-color: #1a1a1a; color: white; }"

    # Injection des variables de config Python dans le CSS (taille police, etc.)
    # On ajoute un bloc <style> supplémentaire pour surcharger/compléter avec la config dynamique
    dynamic_css = f"""
    <style>
        {css_content}

        body {{
            font-size: {config['font_size']}px;
        }}
        .img-large {{
            width: {config['img_large_width']}px;
        }}
    </style>
    """

    script = """
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script>
        var backend;
        new QWebChannel(qt.webChannelTransport, function (channel) {
            backend = channel.objects.pyBridge;
        });

        function onLinkClick(link) { 
            if (backend) {
                backend.handleLink(link);
            } else {
                console.log("Backend not connected for link: " + link);
            }
        }

        function onCheckboxClick(cbId, checked) { 
            if (backend) {
                backend.handleLink('CB:' + cbId + ':' + checked);
            }
        }
    </script>
    """

    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{dynamic_css}{script}</head><body>{body_content}</body></html>"