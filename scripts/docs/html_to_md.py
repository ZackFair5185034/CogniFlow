#!/usr/bin/env python3
"""
CogniFlow 设计文档 HTML → Markdown 转换器

设计原则:
- 只处理 docs/research/*.html 这套手写设计文档
- 提取 <body> 内的所有 <div class="doc-section"> 等内容块
- 转换 <h1-h6>, <p>, <table>, <pre>, <ul>/<ol>, <strong>, <em>, <code>
- 跳过 <head>/<style>/<script>/<title> 等装饰性内容
- 保留代码块原样, 不做转义
"""

import re
import sys
from pathlib import Path
from html.parser import HTMLParser


# 完全跳过的标签(整段不解析, 含其子节点)
SKIP_TAGS = {"head", "style", "script", "title", "nav", "header", "footer"}
# void elements - 出现就当自闭合处理, 不入栈
VOID_TAGS = {"meta", "link", "br", "hr", "img", "input"}


class DocHtmlToMarkdown(HTMLParser):
    """仅处理设计文档中实际用到的标签集合。"""

    HEADING_TAGS = {f"h{i}" for i in range(1, 7)}
    LIST_TAGS = {"ul", "ol"}
    BLOCK_TAGS = {"div", "section", "article", "main", "body", "html"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        # skip 标签栈
        self._skip_stack: list[str] = []
        # pre 缓冲
        self._in_pre = False
        self._pre_buf: list[str] = []
        # 列表栈
        self._list_stack: list[tuple[str, int]] = []
        # 表格
        self._in_table = False
        self._in_thead = False
        self._in_row = False
        self._cells: list[str] = []
        self._cell_buf: list[str] = []
        self._rows: list[list[str]] = []
        # 段落
        self._in_para = False
        self._para_buf: list[str] = []
        # 标题
        self._in_heading = False
        # 装饰 hr
        self._hr_pending = False

    # ---------- 工具 ----------
    @property
    def _in_skip(self) -> bool:
        return len(self._skip_stack) > 0

    def _flush(self, s: str):
        if self._in_pre:
            self._pre_buf.append(s)
        elif self._in_para:
            self._para_buf.append(s)
        elif self._in_table and self._in_row:
            self._cell_buf.append(s)
        else:
            self.parts.append(s)

    # ---------- starttag ----------
    def handle_starttag(self, tag, attrs):
        t = tag.lower()

        if t in SKIP_TAGS:
            self._skip_stack.append(t)
            return
        # void elements: 单次事件, 直接处理不push
        if t in VOID_TAGS:
            # hr 需要输出分隔线
            if t == "hr":
                self.parts.append("\n\n---\n\n")
            return
        if self._in_skip:
            return

        # 标题
        if t in self.HEADING_TAGS:
            level = int(t[1])
            self.parts.append("\n\n" + "#" * level + " ")
            self._in_heading = True
            return

        # 段落
        if t == "p":
            self._in_para = True
            self._para_buf = []
            return

        # pre
        if t == "pre":
            self._in_pre = True
            self._pre_buf = []
            return

        # 列表
        if t in self.LIST_TAGS:
            self._list_stack.append((t, 0))
            self.parts.append("\n")
            return

        if t == "li":
            if not self._list_stack:
                return
            list_type, _ = self._list_stack[-1]
            indent = "  " * (len(self._list_stack) - 1)
            bullet = "-" if list_type == "ul" else "1."
            self.parts.append(f"\n{indent}{bullet} ")
            return

        # 表格
        if t == "table":
            self._in_table = True
            self._rows = []
            return
        if t == "thead":
            self._in_thead = True
            return
        if t == "tbody":
            self._in_thead = False
            return
        if t == "tr":
            self._in_row = True
            self._cells = []
            return
        if t in ("th", "td"):
            self._cell_buf = []
            return

        # 块级容器: 忽略包装
        if t in self.BLOCK_TAGS:
            return

        # hr
        if t == "hr":
            self.parts.append("\n\n---\n\n")
            return

        # 行内
        if t in ("strong", "b"):
            self._flush("**")
            return
        if t in ("em", "i"):
            self._flush("*")
            return
        if t == "code":
            self._flush("`")
            return
        if t == "br":
            self._flush("  \n")
            return
        if t == "span":
            return

    def handle_startendtag(self, tag, attrs):
        # 自闭合标签 (例如 <br/>, <hr/>, <meta />) - 走 starttag + endtag
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        t = tag.lower()

        # 通用策略: 任何 endtag 都尝试弹出栈顶匹配项
        # (应对 void element 如 <meta charset> 被写成 starttag+endtag 形式)
        if self._skip_stack and self._skip_stack[-1] == t:
            self._skip_stack.pop()
            return
        if self._skip_stack:
            # 栈非空但栈顶不匹配, 容忍并继续
            return
        # 栈空, 继续正常处理

        if t in self.HEADING_TAGS:
            self.parts.append("\n")
            self._in_heading = False
            return

        if t == "p":
            if self._para_buf:
                self.parts.append("".join(self._para_buf).strip())
                self.parts.append("\n\n")
            self._in_para = False
            self._para_buf = []
            return

        if t == "pre":
            code = "".join(self._pre_buf)
            lang = self._sniff_lang(code)
            self.parts.append(f"\n```{lang}\n")
            self.parts.append(code.rstrip("\n"))
            self.parts.append("\n```\n\n")
            self._in_pre = False
            self._pre_buf = []
            return

        if t in self.LIST_TAGS:
            if self._list_stack:
                self._list_stack.pop()
            self.parts.append("\n")
            return

        if t == "li":
            return

        if t in ("th", "td"):
            cell_text = "".join(self._cell_buf).strip()
            cell_text = re.sub(r"\s+", " ", cell_text)
            self._cells.append(cell_text)
            self._cell_buf = []
            return

        if t == "tr":
            if self._in_row:
                self._rows.append(self._cells)
            self._in_row = False
            self._cells = []
            return

        if t in ("thead", "tbody"):
            self._in_thead = (t == "thead")
            return

        if t == "table":
            self._render_table()
            self._in_table = False
            self._rows = []
            return

        if t in ("strong", "b"):
            self._flush("**")
            return
        if t in ("em", "i"):
            self._flush("*")
            return
        if t == "code":
            self._flush("`")
            return

    def _sniff_lang(self, code: str) -> str:
        """根据代码首行特征推断 Markdown 围栏语言标签。"""
        first_line = code.lstrip("\n").split("\n", 1)[0].strip()
        lower = first_line.lower()
        # 路径注释提示
        if first_line.startswith("#") and ("/" in first_line or any(ext in first_line for ext in [".py", ".sh", ".ts", ".js", ".vue"])):
            if ".sh" in first_line or ".bash" in first_line:
                return "bash"
            if ".ts" in first_line or ".tsx" in first_line:
                return "typescript"
            if ".js" in first_line or ".jsx" in first_line:
                return "javascript"
            if ".vue" in first_line:
                return "vue"
            if ".yaml" in first_line or ".yml" in first_line:
                return "yaml"
            if ".json" in first_line:
                return "json"
            if ".toml" in first_line:
                return "toml"
            if ".md" in first_line:
                return "markdown"
            return "python"
        # box-drawing 字符 - 文本/架构图
        if any(c in code[:200] for c in "┌┐└┘├┤┬┴┼─│"):
            return "text"
        # shell 提示符
        if lower.startswith("$ "):
            return "bash"
        # yaml / toml
        if first_line.startswith("---") or (first_line.startswith("[") and "]" in first_line[:30]):
            return "yaml"
        # sql
        if lower.startswith(("select ", "insert ", "create ", "alter ", "update ")):
            return "sql"
        # python 特征
        if first_line.startswith(("from ", "import ", "def ", "class ", "async def ", "@", "if __name__")):
            return "python"
        if re.search(r":\s*$", first_line) and ("def " in first_line or "class " in first_line):
            return "python"
        # typescript / javascript 特征
        if first_line.startswith(("import ", "export ", "const ", "let ", "var ", "function ", "interface ", "type ")):
            if "<" in first_line and ">" in first_line:
                return "typescript"
            if "interface " in first_line or "type " in first_line:
                return "typescript"
            return "javascript"
        # html / vue
        if first_line.startswith("<") and ">" in first_line[:50]:
            if "<template>" in code[:500] or "<script" in code[:500]:
                return "vue"
            return "html"
        # json
        if first_line.startswith("{") or first_line.startswith("["):
            return "json"
        return "text"

    def handle_data(self, data):
        if self._in_skip:
            return
        if self._in_pre:
            self._pre_buf.append(data)
            return
        # 段落/标题/表格 cell 内: 多空白压成单空格
        if self._in_para or self._in_table or self._in_row or self._in_heading:
            text = re.sub(r"\s+", " ", data)
            self._flush(text)
            return
        # 顶层纯文本: 如果是 li 内的(没套 p), 也压空白
        if self._list_stack:
            text = re.sub(r"\s+", " ", data)
            self._flush(text)
            return
        # 顶层/装饰位置: 跳过(通常是导航)

    # ---------- 表格渲染 ----------
    def _render_table(self):
        if not self._rows:
            return
        # 列数取最长
        ncols = max(len(r) for r in self._rows)
        norm = [r + [""] * (ncols - len(r)) for r in self._rows]
        header = norm[0]
        body = norm[1:]

        def esc(s: str) -> str:
            return s.replace("|", "\\|").replace("\n", " ").strip()

        self.parts.append("\n| " + " | ".join(esc(c) for c in header) + " |\n")
        self.parts.append("| " + " | ".join("---" for _ in header) + " |\n")
        for r in body:
            self.parts.append("| " + " | ".join(esc(c) for c in r) + " |\n")
        self.parts.append("\n")

    def get_markdown(self) -> str:
        text = "".join(self.parts)
        # 多个空行压成最多 2 个
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


def convert_file(html_path: Path) -> str:
    content = html_path.read_text(encoding="utf-8")
    parser = DocHtmlToMarkdown()
    parser.feed(content)
    return parser.get_markdown()


def main():
    if len(sys.argv) < 2:
        print("Usage: html_to_md.py <input.html> [output.md]")
        sys.exit(1)
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"ERROR: {src} not found")
        sys.exit(1)
    md = convert_file(src)
    if len(sys.argv) >= 3:
        dst = Path(sys.argv[2])
        dst.write_text(md, encoding="utf-8")
        print(f"✓ {src.name} -> {dst.name}  ({len(md)} chars, {md.count(chr(10))} lines)")
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
