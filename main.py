import tkinter as tk
from interface import AppLauncher

if __name__ == "__main__":
    root = tk.Tk()
    # On peut définir une icône globale ici si vous avez un .ico
    # root.iconbitmap("mon_icone.ico")

    app = AppLauncher(root)
    root.mainloop()