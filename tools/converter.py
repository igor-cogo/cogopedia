"""Converte verbetes DOCX da Cogopedia em páginas Markdown para o MkDocs.
Uso: python3 converter.py <pasta_docx> <pasta_destino>
- remove o cabeçalho "COGOPEDIA · RASCUNHO..." e tudo a partir de "ANEXO EDITORIAL"
- transforma a primeira tabela (ficha) em infobox
- desce os títulos um nível (o nome do verbete vira o título H1)
"""
import sys, re, json, subprocess, unicodedata, pathlib

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def inline(s):
    s = s.strip().replace("\\.", ".").replace("\\'", "'").replace('\\"', '"')
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s

def cells(line):
    return [c for c in line.strip().strip("|").split("|")]

LINKS = {"Família Jê": "index.md", "Tronco Macro-Jê": "../index.md"}

def convert(docx, outdir):
    md = subprocess.run(["pandoc", str(docx), "-t", "gfm", "--wrap=none"],
                        capture_output=True, text=True, check=True).stdout
    md = re.split(r"\n\*\*ANEXO EDITORIAL", md)[0]
    lines = md.split("\n")
    if lines and lines[0].startswith("COGOPEDIA"):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    title = lines.pop(0).strip()
    body = "\n".join(lines)
    body = re.sub(r"^(#+) ", lambda m: "#" + m.group(1) + " ", body, flags=re.M)

    # ficha -> infobox
    m = re.search(r"((?:^\|.*\|\s*\n)+)", body, flags=re.M)
    ficha = {}
    if m:
        rows = [l for l in m.group(1).strip().split("\n")
                if not re.match(r"^\|\s*-", l) and "".join(cells(l)).strip()]
        html = ['<table class="infobox">', f'<caption>{inline(cells(rows[0])[0])}</caption>']
        for r in rows[1:]:
            c = cells(r)
            if len(c) >= 2:
                k, v = inline(c[0]), inline("|".join(c[1:]))
                ficha[re.sub(r"<.*?>", "", k)] = re.sub(r"<.*?>", "", v)
                html.append(f"<tr><th>{k}</th><td>{v}</td></tr>")
        html.append("</table>")
        body = body[:m.start()] + body[m.end():]
        # infobox logo após o subtítulo, para flutuar ao lado da introdução
        partes = body.split("\n\n", 1)
        body = partes[0] + "\n\n" + "\n".join(html) + "\n\n" + (partes[1] if len(partes) > 1 else "")

    # Ver também -> links
    for nome, alvo in LINKS.items():
        body = re.sub(rf"^-\s+{re.escape(nome)}[ \t]*$", f"- [{nome}]({alvo})", body, flags=re.M)
    body = re.sub(r"^-\s+((?:Povo|Guia de Estudos)[^\[\n]*?)[ \t]*$", r"- \1 *(em preparação)*", body, flags=re.M)

    code = re.match(r"(\w+?)_", docx.name).group(1)
    page = f"---\ntitle: {title}\n---\n\n# {title}\n\n" + body.strip() + "\n"
    name = slug(title)
    (outdir / f"{name}.md").write_text(page, encoding="utf-8")
    return {"codigo": code, "nome": title, "arquivo": f"{name}.md",
            "falantes": ficha.get("Falantes (Atlas)", ""), "onde": ficha.get("Onde é falada", "")}

if __name__ == "__main__":
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    idx = [convert(f, out) for f in sorted(src.glob("*.docx"))]
    print(json.dumps(idx, ensure_ascii=False, indent=1))
