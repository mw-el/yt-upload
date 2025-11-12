# Font-Rendering Fix für Ubuntu

Falls Schriften pixelig/unscharf aussehen, führe diese 2 Schritte aus:

## 1. Installiere Tk mit XFT-Support

```bash
conda activate yt-upload
conda install -c conda-forge "tk=8.6.13=xft*" -y
```

## 2. Setze Environment-Variable

```bash
conda env config vars set TTKBOOTSTRAP_FONT_MANAGER=tk -n yt-upload
conda deactivate
conda activate yt-upload
```

## 3. App neu starten

```bash
./start.sh
```

Fertig! Schriften sollten jetzt crisp und klar sein.

---

**Quelle:** Basiert auf docs/TKINTER_FONTS.md aus _AA_DICTATE
