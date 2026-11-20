#!/usr/bin/env python3
"""PROG - editor e ambiente de programação em terminal."""
import curses
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

APP_NAME = "PROG"

LANGUAGES = [
    ("Python", "python3", ["python3", "--version"], ".py"),
    ("Bash", "bash", ["bash", "--version"], ".sh"),
    ("C", "gcc", ["gcc", "--version"], ".c"),
    ("C++", "g++", ["g++", "--version"], ".cpp"),
    ("Rust", "rustc", ["rustc", "--version"], ".rs"),
    ("JavaScript", "node", ["node", "--version"], ".js"),
    ("Assembly", "nasm", ["nasm", "-v"], ".asm"),
    ("Perl", "perl", ["perl", "-e", "print $^V"], ".pl"),
    ("Lua", "lua", ["lua", "-v"], ".lua"),
    ("Ruby", "ruby", ["ruby", "--version"], ".rb"),
    ("Java", "javac", ["javac", "-version"], ".java"),
]
EXT_LANG = {".py":"Python", ".sh":"Bash", ".c":"C", ".h":"C", ".cpp":"C++", ".cc":"C++", ".cxx":"C++", ".rs":"Rust", ".js":"JavaScript", ".asm":"Assembly", ".s":"Assembly", ".pl":"Perl", ".lua":"Lua", ".rb":"Ruby", ".java":"Java"}


def available_languages():
    found = []
    for name, executable, version_cmd, ext in LANGUAGES:
        if name == "Assembly":
            ok = shutil.which("nasm") and shutil.which("ld")
        elif name == "Java":
            ok = shutil.which("javac") and shutil.which("java")
        else:
            ok = shutil.which(executable)
        if not ok:
            continue
        try:
            p = subprocess.run(version_cmd, capture_output=True, text=True, timeout=3)
            version = (p.stdout or p.stderr).strip().splitlines()[0]
            for prefix in ("Python ", "GNU bash, versão ", "GNU bash, version ", "gcc (", "g++ (", "rustc ", "v", "This is perl "):
                if version.startswith(prefix) and name in ("Python", "Bash", "C", "C++", "Rust", "JavaScript", "Perl"):
                    if name == "Python": version = version.replace("Python ", "", 1)
                    elif name == "Rust": version = version.replace("rustc ", "", 1)
                    elif name == "JavaScript": version = version.lstrip("v")
                    elif name == "Perl": version = version.replace("This is perl ", "", 1).split()[0]
                    elif name in ("C", "C++"):
                        import re
                        m = re.search(r"\(([^)]+)\)", version)
                        version = m.group(1) if m else version
                    break
            found.append({"name": name, "exe": executable, "version": version, "ext": ext})
        except Exception:
            found.append({"name": name, "exe": executable, "version": "instalado", "ext": ext})
    return found


def choose_file(stdscr, save=False, current=None, lang=None):
    if not shutil.which("zenity"):
        return None
    curses.def_prog_mode()
    curses.endwin()
    try:
        cmd = ["zenity", "--file-selection", "--title=Salvar arquivo" if save else "--title=Abrir arquivo"]
        if save:
            cmd += ["--save", "--confirm-overwrite"]
            if current:
                cmd += [f"--filename={current}"]
            elif lang:
                ext = next((x[3] for x in LANGUAGES if x[0] == lang), ".txt")
                cmd += [f"--filename=programa{ext}"]
        else:
            cmd += ["--file-filter=Todos os arquivos | *"]
            if lang:
                ext = next((x[3] for x in LANGUAGES if x[0] == lang), None)
                if ext:
                    cmd += [f"--file-filter={lang} | *{ext}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    finally:
        curses.reset_prog_mode()
        stdscr.refresh()


class Editor:
    def __init__(self, stdscr, language, languages, filename=None, lines=None):
        self.scr = stdscr
        self.language = language
        self.languages = languages
        self.filename = filename
        self.lines = lines[:] if lines else [""]
        self.y = self.x = self.scroll = 0
        self.status = "F2 executar | F4 ajuda | F5 sair"
        self.dirty = False

    def draw(self):
        self.scr.erase()
        h, w = self.scr.getmaxyx()
        lang_info = next((l for l in self.languages if l["name"] == self.language), None)
        version = lang_info["version"] if lang_info else ""
        name = self.filename or "Sem título"
        title = f" PROG | {self.language} {version} | {name} "
        self.scr.addnstr(0, 0, title, max(0, w-1), curses.A_REVERSE)
        view_h = max(1, h-2)
        if self.y < self.scroll: self.scroll = self.y
        if self.y >= self.scroll + view_h: self.scroll = self.y-view_h+1
        for row in range(view_h):
            idx = self.scroll + row
            if idx >= len(self.lines): break
            lineno = f"{idx+1:4} "
            self.scr.addnstr(row+1, 0, lineno, 5, curses.A_DIM)
            self.scr.addnstr(row+1, 5, self.lines[idx], max(0, w-6))
        status = self.status + ("  [alterado]" if self.dirty else "")
        self.scr.addnstr(h-1, 0, status.ljust(max(0,w-1)), max(0,w-1), curses.A_REVERSE)
        cx = min(w-1, 5 + self.x)
        cy = min(h-2, max(1, self.y-self.scroll+1))
        self.scr.move(cy, cx)
        self.scr.refresh()

    def prompt(self, message):
        h, w = self.scr.getmaxyx()
        curses.echo()
        curses.curs_set(1)
        self.scr.move(h-1, 0); self.scr.clrtoeol()
        self.scr.addnstr(h-1, 0, message, w-1)
        self.scr.refresh()
        value = self.scr.getstr(h-1, min(len(message), w-1), max(1,w-len(message)-2)).decode("utf-8", "replace")
        curses.noecho()
        return value

    def save(self):
        path = choose_file(self.scr, save=True, current=self.filename, lang=self.language)
        if not path: return
        try:
            Path(path).write_text("\n".join(self.lines) + "\n", encoding="utf-8")
            self.filename = path
            self.dirty = False
            self.status = f"Salvo: {path}"
            ext_lang = EXT_LANG.get(Path(path).suffix.lower())
            if ext_lang: self.language = ext_lang
        except Exception as e:
            self.status = f"Falha ao salvar: {e}"

    def open(self):
        path = choose_file(self.scr, save=False, lang=self.language)
        if not path: return
        try:
            content = Path(path).read_text(encoding="utf-8")
            self.lines = content.splitlines() or [""]
            self.filename = path
            self.y = self.x = self.scroll = 0
            self.dirty = False
            self.language = EXT_LANG.get(Path(path).suffix.lower(), self.language)
            self.status = f"Aberto: {path}"
        except Exception as e:
            self.status = f"Falha ao abrir: {e}"

    def new(self):
        if self.dirty:
            ans = self.prompt("Descartar alterações? (s/N): ").lower()
            if ans != "s": return
        self.lines = [""]; self.filename = None; self.y = self.x = self.scroll = 0; self.dirty = False
        self.status = "Novo arquivo"

    def help(self):
        self.scr.erase(); h,w = self.scr.getmaxyx()
        entries = ["AJUDA DO PROG", "", "Setas: mover o cursor", "Home / End: início / fim da linha", "Ctrl+setas: pular palavras", "Enter: nova linha", "Backspace / Delete: apagar", "Ctrl+S: salvar (janela gráfica)", "Ctrl+O: abrir (janela gráfica)", "Ctrl+N: novo arquivo", "F2: executar o programa", "F3: limpar o editor", "F4: mostrar esta ajuda", "F5: sair do editor", "", "Pressione qualquer tecla para voltar."]
        for i, line in enumerate(entries[:h-1]): self.scr.addnstr(i, 1, line, w-2)
        self.scr.getch()

    def run(self):
        if not self.filename:
            self.status = "Salve o arquivo antes de executar (Ctrl+S)."; return
        if self.dirty:
            self.status = "Salve as alterações antes de executar (Ctrl+S)."; return
        try:
            output = execute(self.language, self.filename)
            show_output(self.scr, output)
            self.status = "Execução finalizada."
        except Exception as e:
            show_output(self.scr, f"Erro ao executar: {e}")
            self.status = "Erro durante a execução. Consulte a saída."

    def loop(self):
        curses.curs_set(1)
        curses.raw()
        while True:
            self.draw()
            key = self.scr.getch()
            line = self.lines[self.y]
            if key == curses.KEY_UP: self.y = max(0,self.y-1); self.x = min(self.x,len(self.lines[self.y]))
            elif key == curses.KEY_DOWN: self.y = min(len(self.lines)-1,self.y+1); self.x = min(self.x,len(self.lines[self.y]))
            elif key == curses.KEY_LEFT:
                if self.x: self.x -= 1
                elif self.y: self.y -= 1; self.x = len(self.lines[self.y])
            elif key == curses.KEY_RIGHT:
                if self.x < len(line): self.x += 1
                elif self.y < len(self.lines)-1: self.y += 1; self.x = 0
            elif key in (curses.KEY_HOME, 1): self.x = 0
            elif key in (curses.KEY_END, 5): self.x = len(line)
            elif key == 23: # Ctrl+W: palavra anterior
                while self.x and line[self.x-1].isspace(): self.x -= 1
                while self.x and not line[self.x-1].isspace(): self.x -= 1
            elif key == 6: # Ctrl+F: palavra seguinte
                while self.x < len(line) and not line[self.x].isspace(): self.x += 1
                while self.x < len(line) and line[self.x].isspace(): self.x += 1
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if self.x: self.lines[self.y] = line[:self.x-1]+line[self.x:]; self.x -= 1; self.dirty=True
                elif self.y: prev=len(self.lines[self.y-1]); self.lines[self.y-1]+=line; del self.lines[self.y]; self.y-=1; self.x=prev; self.dirty=True
            elif key == curses.KEY_DC:
                if self.x < len(line): self.lines[self.y]=line[:self.x]+line[self.x+1:]; self.dirty=True
                elif self.y < len(self.lines)-1: self.lines[self.y]+=self.lines[self.y+1]; del self.lines[self.y+1]; self.dirty=True
            elif key in (10,13, curses.KEY_ENTER):
                self.lines[self.y:self.y+1] = [line[:self.x], line[self.x:]]; self.y+=1; self.x=0; self.dirty=True
            elif key == 19: self.save()
            elif key == 15: self.open()
            elif key == 14: self.new()
            elif key == curses.KEY_F2: self.run()
            elif key == curses.KEY_F3: self.lines=[""]; self.y=self.x=self.scroll=0; self.dirty=True
            elif key == curses.KEY_F4: self.help()
            elif key == curses.KEY_F5:
                if self.dirty:
                    ans=self.prompt("Sair sem salvar? (s/N): ").lower()
                    if ans != "s": continue
                break
            elif key == 3: # Ctrl+C
                self.status = "Ctrl+C: use F5 para sair do editor."
            elif 32 <= key <= 126 or key >= 160:
                ch = chr(key)
                self.lines[self.y] = line[:self.x]+ch+line[self.x:]; self.x+=1; self.dirty=True
        curses.noraw()


def execute(language, filename):
    path = Path(filename).resolve()
    cwd = str(path.parent)
    with tempfile.TemporaryDirectory(prefix="prog-") as tmp:
        tmp = Path(tmp)
        if language == "Python": cmd=["python3", str(path)]
        elif language == "Bash": cmd=["bash", str(path)]
        elif language == "JavaScript": cmd=["node", str(path)]
        elif language == "Perl": cmd=["perl", str(path)]
        elif language == "Lua": cmd=["lua", str(path)]
        elif language == "Ruby": cmd=["ruby", str(path)]
        elif language == "C":
            exe=tmp/"programa"; c=subprocess.run(["gcc",str(path),"-o",str(exe),"-Wall"],capture_output=True,text=True,cwd=cwd)
            if c.returncode: return c.stdout+c.stderr
            cmd=[str(exe)]
        elif language == "C++":
            exe=tmp/"programa"; c=subprocess.run(["g++",str(path),"-o",str(exe),"-Wall"],capture_output=True,text=True,cwd=cwd)
            if c.returncode: return c.stdout+c.stderr
            cmd=[str(exe)]
        elif language == "Rust":
            exe=tmp/"programa"; c=subprocess.run(["rustc",str(path),"-o",str(exe)],capture_output=True,text=True,cwd=cwd)
            if c.returncode: return c.stdout+c.stderr
            cmd=[str(exe)]
        elif language == "Java":
            c=subprocess.run(["javac","-d",str(tmp),str(path)],capture_output=True,text=True,cwd=cwd)
            if c.returncode: return c.stdout+c.stderr
            cmd=["java","-cp",str(tmp),path.stem]
        elif language == "Assembly":
            obj=tmp/"programa.o"; exe=tmp/"programa"
            c=subprocess.run(["nasm","-f","elf64",str(path),"-o",str(obj)],capture_output=True,text=True,cwd=cwd)
            if c.returncode: return c.stdout+c.stderr
            c=subprocess.run(["ld",str(obj),"-o",str(exe)],capture_output=True,text=True,cwd=cwd)
            if c.returncode: return c.stdout+c.stderr
            cmd=[str(exe)]
        else: return f"Linguagem não suportada: {language}"
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,cwd=cwd,timeout=None)
            return p.stdout + p.stderr + (f"\nCódigo de saída: {p.returncode}" if p.returncode else "")
        except KeyboardInterrupt:
            return "Execução interrompida."


def show_output(stdscr, output):
    stdscr.erase(); h,w=stdscr.getmaxyx()
    lines=(output or "(Nenhuma saída)").splitlines()
    top=0
    while True:
        stdscr.erase(); stdscr.addnstr(0,0," SAÍDA DO PROGRAMA — pressione Q para voltar ",w-1,curses.A_REVERSE)
        for i,line in enumerate(lines[top:top+h-2]): stdscr.addnstr(i+1,0,line,w-1)
        stdscr.refresh(); key=stdscr.getch()
        if key in (ord('q'),ord('Q'),27,10,13): break
        if key==curses.KEY_DOWN: top=min(max(0,len(lines)-h+2),top+1)
        elif key==curses.KEY_UP: top=max(0,top-1)
        elif key==curses.KEY_NPAGE: top=min(max(0,len(lines)-h+2),top+h-2)
        elif key==curses.KEY_PPAGE: top=max(0,top-h+2)


def choose_language(stdscr, langs):
    idx=0
    while True:
        stdscr.erase(); h,w=stdscr.getmaxyx()
        title=" PROG — ambiente de programação "
        stdscr.addnstr(1,max(0,(w-len(title))//2),title,w-1,curses.A_BOLD)
        stdscr.addnstr(3,2,"Escolha uma linguagem (setas e Enter):",w-4)
        if not langs:
            stdscr.addnstr(5,2,"Nenhuma linguagem compatível foi detectada.",w-4)
            stdscr.addnstr(7,2,"Instale Python 3 e tente novamente.",w-4)
        else:
            for i,lang in enumerate(langs):
                text=f"[{i+1}] {lang['name']:<12} {lang['version']}"
                stdscr.addnstr(5+i,3,text,w-6,curses.A_REVERSE if i==idx else curses.A_NORMAL)
        stdscr.addnstr(h-2,2,"Q: sair",w-4,curses.A_DIM); stdscr.refresh()
        key=stdscr.getch()
        if key in (ord('q'),ord('Q'),27): return None
        if langs and key in (curses.KEY_UP,): idx=(idx-1)%len(langs)
        elif langs and key==curses.KEY_DOWN: idx=(idx+1)%len(langs)
        elif langs and key in (10,13,curses.KEY_ENTER): return langs[idx]["name"]
        elif langs and ord('1') <= key <= ord('9'):
            n=key-ord('1')
            if n<len(langs): return langs[n]["name"]


def main(stdscr):
    curses.curs_set(0)
    langs=available_languages()
    while True:
        language=choose_language(stdscr,langs)
        if language is None: return
        Editor(stdscr,language,langs).loop()

if __name__ == "__main__":
    try: curses.wrapper(main)
    except KeyboardInterrupt: pass
