"""Two interface languages. The Chinese text in the code is the key; EN holds its English.
tr("共 {n} 页", n=3) -> "共 3 页" or "3 pages".

tests\\t_i18n.py fails when a text on screen skips tr() or has no English here."""

LANG = "zh"
LANGS = ("zh", "en")


def set_lang(lang):
    global LANG
    LANG = lang if lang in LANGS else "zh"


def lang():
    return LANG


def tr(text, **kw):
    s = EN.get(text, text) if LANG == "en" else text
    return s.format(**kw) if kw else s


EN = {
    # ---- names ----
    "PDF工具箱": "PDF Toolkit",
    "微软雅黑": "Microsoft YaHei", "宋体": "SimSun", "黑体": "SimHei", "楷体": "KaiTi", "仿宋": "FangSong",
    "内置字体": "Built-in font",
    "行楷": "Xingkai", "华文楷体": "STKaiti", "雅黑": "YaHei", "英文手写": "Handwriting",
    "黑色": "Black", "蓝黑": "Blue-black", "蓝色": "Blue", "红色": "Red",

    # ---- buttons shared by many windows ----
    "确定": "OK", "取消": "Cancel", "是": "Yes", "否": "No", "关闭": "Close", "打开": "Open",
    "保存": "Save", "不保存": "Don't save", "删除": "Delete", "浏览…": "Browse…", "清空": "Clear",
    "颜色": "Colour", "选择颜色": "Choose a colour", "字体": "Font", "字号": "Size", "更多": "More",

    # ---- messages shared by many windows ----
    "{what}失败。\n\n{why}": "\"{what}\" could not be completed.\n\n{why}",
    "密码不正确，无法打开这个文件。": "Wrong password; this file cannot be opened.",
    "文件正被其他程序占用，或没有写入权限。\n请关闭正在打开它的程序（如浏览器、PDF阅读器）后再试，或换一个保存位置。":
        "The file is in use by another program, or you have no permission to write there.\n"
        "Close the program that has it open (a browser or PDF reader, for example) and try again, "
        "or save somewhere else.",
    "找不到文件：{path}": "File not found: {path}",
    "找不到文件：\n{path}": "File not found:\n{path}",
    "“{name}” 有密码保护，请输入打开密码：": "\"{name}\" is password-protected. Enter the password to open it:",
    "密码不正确，请重新输入。\n": "Wrong password, please try again.\n",
    "程序遇到了一个意外问题，当前操作没有完成。":
        "The program ran into an unexpected problem; the current action was not completed.",
    "PDF 文件 (*.pdf)": "PDF files (*.pdf)",
    "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)":
        "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)",
    "PDF 和图片 (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)":
        "PDFs and images (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)",
    "文本文件 (*.txt)": "Text files (*.txt)",

    # ---- page ranges ----
    "看不懂的页码：“{part}”": "Cannot read this page number: \"{part}\"",
    "页码 {v} 超出范围（本文件共 {n} 页）": "Page {v} is out of range (this file has {n} pages)",
    "请填写页码范围": "Enter a page range",
    "{name}：{why}": "{name}: {why}",

    # ---- names of files the app writes ----
    "未命名": "Untitled", "未命名.pdf": "Untitled.pdf", "前置页": "Front pages",
    "第{n}页": "p{n}", "第{a}-{b}页": "p{a}-{b}", "部分{n}": "part{n}",
    "{stem}_第{pages}页.pdf": "{stem}_p{pages}.pdf",
    "合并结果.pdf": "Merged.pdf", "_拆分": "_split", "_压缩.pdf": "_compressed.pdf", "_图片": "_images",
    "第 {n} 页": "Page {n}",
    "第 {n} 页 共 {total} 页": "Page {n} of {total}",
    "机密文件": "CONFIDENTIAL",

    # ---- start page ----
    "想做什么？": "What would you like to do?",
    "打开并编辑": "Open and edit",
    "加文字、改字、插图、批注\n页面旋转/删除/排序": "Text, images, markup; rotate, delete, reorder pages",
    "合并 PDF": "Merge PDF",
    "多个 PDF 和图片\n合成一个文件": "Several PDFs and images into one file",
    "拆分 PDF": "Split PDF",
    "按范围、按页数、\n按书签拆成多个文件": "By page range, page count or bookmarks",
    "签名": "Signature",
    "手写、照片或输入姓名\n生成签名盖到文件上": "Draw, import or type a signature and put it on the page",
    "图片转 PDF": "Images to PDF",
    "把照片、扫描件\n拼成一个 PDF": "Turn photos and scans into one PDF",
    "新建空白文档": "New blank PDF",
    "从一张 A4 白纸开始": "Start from an empty A4 sheet",
    "版本 {ver} · 绿色免安装": "Version {ver} · portable, no install",
    "✓  拆分 / 合并 / 页面整理": "✓  Split / merge / organise pages",
    "✓  加文字、改字、图片、批注": "✓  Add and edit text, images, markup",
    "✓  手写签名、图片签名": "✓  Hand-drawn or photographed signature",
    "✓  水印、页码、加密、压缩": "✓  Watermarks, page numbers, passwords",
    "✓  全部在本机处理，不上传文件": "✓  Everything stays on this PC",
    "也可以把 PDF 或图片直接拖进这个窗口：拖一个文件打开，拖多个文件合并":
        "You can also drop PDFs or images onto this window: one file is opened, several are merged",
    "最近打开": "Recent files",
    "打开文件…": "Open file…",
    "还没有打开过文件": "No files opened yet",

    # ---- main window: top bar ----
    "另存为": "Save as", "打印": "Print", "撤销": "Undo", "重做": "Redo", "合并": "Merge", "拆分": "Split",
    "插入": "Insert", "左转": "Rotate left", "右转": "Rotate right", "删除页": "Delete", "提取": "Extract",
    "水印": "Watermark", "页码": "Page no.", "加密": "Encrypt", "压缩": "Compress", "导出": "Export",
    "设置": "Settings", "帮助": "Help",
    "（{key}）": " ({key})",
    "关闭当前文档，回到首页": "Close this document and go back to the start page",
    "把多个 PDF / 图片合并成一个": "Merge several PDFs / images into one",
    "把 PDF 拆成多个文件": "Split a PDF into several files",
    "从文件插入页面…": "Insert pages from a file…",
    "插入空白页": "Insert blank page",
    "选中的页面逆时针旋转 90°": "Rotate the selected pages 90° anticlockwise",
    "选中的页面顺时针旋转 90°": "Rotate the selected pages 90° clockwise",
    "删除选中的页面": "Delete the selected pages",
    "把选中的页面另存为一个新 PDF": "Save the selected pages as a new PDF",
    "设置或移除打开密码": "Set or remove the password to open",
    "缩小文件体积": "Make the file smaller",
    "导出为图片…": "Export as images…",
    "导出文字 (.txt)…": "Export text (.txt)…",

    # ---- main window: editing tools ----
    "浏览": "Browse", "浏览 / 拖动页面（Esc）": "Browse / drag the page (Esc)",
    "加文字": "Add text", "在页面上点击，输入新的文字": "Click on the page and type new text",
    "改文字": "Edit text", "点击页面上已有的一行文字进行修改或删除": "Click a line of existing text to change or delete it",
    "图片": "Image", "插入图片": "Insert an image",
    "手写 / 图片 / 输入姓名生成签名，放到页面上": "Draw, import or type a signature and place it on the page",
    "日期": "Date", "插入今天的日期": "Insert today's date",
    "高亮": "Highlight", "拖过文字加高亮": "Drag across text to highlight it",
    "下划线": "Underline", "拖过文字加下划线": "Drag across text to underline it",
    "删除线": "Strikeout", "拖过文字加删除线": "Drag across text to strike it out",
    "画笔": "Pen", "自由涂画": "Draw freehand",
    "直线": "Line", "画直线（按住 Shift 画水平/垂直线）": "Draw a line (hold Shift for horizontal / vertical)",
    "箭头": "Arrow", "画箭头": "Draw an arrow",
    "方框": "Box", "画方框（按住 Shift 画正方形）": "Draw a box (hold Shift for a square)",
    "圆圈": "Ellipse", "画椭圆（按住 Shift 画正圆）": "Draw an ellipse (hold Shift for a circle)",
    "擦除": "Erase", "框选区域，彻底擦掉其中的内容并涂白": "Drag a box: its content is really removed and painted white",
    "涂黑": "Redact",
    "框选区域，彻底删除其中的内容并涂黑（用于遮盖敏感信息）":
        "Drag a box: its content is really removed and painted black (for hiding sensitive information)",
    "线宽": "Line width",
    "在页面上点击要加文字的位置": "Click on the page where the text should go",
    "把鼠标移到文字上，出现蓝框后点击修改": "Move the mouse over text and click when the blue frame appears",
    "按住鼠标拖过要高亮的文字": "Drag across the text to highlight",
    "按住鼠标拖过要加下划线的文字": "Drag across the text to underline",
    "按住鼠标拖过要加删除线的文字": "Drag across the text to strike out",
    "框选要擦除的区域（内容会被真正删除并涂白）":
        "Drag a box around the area to erase (its content is really removed and painted white)",
    "框选要涂黑的区域（内容会被真正删除）": "Drag a box around the area to black out (its content is really removed)",
    "按住鼠标自由涂画": "Hold the mouse button and draw",
    "按住鼠标拖动绘制；按住 Shift 可画水平线 / 正方形 / 正圆":
        "Drag to draw; hold Shift for a horizontal line / square / circle",
    "在页面上点击要放置的位置；放好后可拖动、拖四角缩放，点击空白处或按回车确认，Esc 取消":
        "Click on the page to place it; drag to move, drag a corner to resize. "
        "Click elsewhere or press Enter to confirm, Esc to cancel",
    "输入文字；拖左上角蓝色手柄移动，点击空白处或 Ctrl+回车 确认，Esc 取消":
        "Type the text; drag the blue handle at its top left to move it. "
        "Click elsewhere or press Ctrl+Enter to confirm, Esc to cancel",
    "这里没有可修改的文字（扫描件或图片中的字无法直接修改，可用“擦除”后再加文字）":
        "No editable text here (text in a scan or picture cannot be edited; use Erase, then Add text)",
    "在此输入文字": "Type here",
    "写入页面": "Write to the page",
    "编辑": "Edit",

    # ---- main window: side panel and status bar ----
    "页面": "Pages",
    "页面　共 {n} 页": "Pages ({n})",
    " · 已选 {n}": " · {n} selected",
    "Ctrl/Shift 多选 · 拖动排序 · 右键更多": "Ctrl/Shift to select several · drag to reorder · right-click for more",
    "第": "Page",
    "/ 0 页": "/ 0",
    "/ {n} 页": "/ {n}",
    "缩小": "Zoom out", "放大": "Zoom in", "适合宽度": "Fit width", "整页": "Fit page",
    "已加密 · ": "Encrypted · ",
    "尚未保存到文件": "Not saved to a file yet",
    "全部在本机处理，文件不会上传": "Everything is processed on this PC; no file is uploaded",

    # ---- main window: actions ----
    "选择要插入的图片": "Choose the image to insert",
    "无法读取这张图片。": "This picture cannot be read.",
    "无法读取这个签名。": "This signature cannot be read.",
    "修改文字": "Edit text",
    "打开 PDF 或图片": "Open a PDF or image",
    "打开文件": "Open file",
    "这个文件里没有页面。": "This file has no pages.",
    "“{name}” 有尚未保存的修改，要保存吗？": "\"{name}\" has unsaved changes. Save them?",
    "已保存：{path}": "Saved: {path}",
    "无法开始打印。": "Printing could not be started.",
    "正在打印…": "Printing…",
    "旋转页面": "Rotate pages",
    "不能删除全部页面": "Cannot delete every page",
    "不能删除全部页面，至少要保留一页。": "You cannot delete every page; at least one must remain.",
    "删除选中的 {n} 页？（可以撤销）": "Delete the {n} selected pages? (You can undo this.)",
    "删除页面": "Delete pages",
    "把 {n} 页另存为": "Save {n} page(s) as",
    "提取页面": "Extract pages",
    "已提取 {n} 页到：{path}": "{n} page(s) extracted to: {path}",
    "选择要插入的 PDF 或图片": "Choose the PDFs or images to insert",
    "读取 {name}": "Read {name}",
    "插入页面": "Insert pages",
    "已在第 {at} 页之后插入 {n} 页": "{n} page(s) inserted after page {at}",
    "调整页面顺序": "Reorder pages",
    "页面顺序已调整（Ctrl+Z 可撤销）": "Page order changed (Ctrl+Z to undo)",
    "第 {pages} 页": "Page {pages}",
    "已选 {n} 页": "{n} pages selected",
    "向左旋转 90°": "Rotate left 90°",
    "向右旋转 90°": "Rotate right 90°",
    "提取为新文件…": "Extract to a new file…",
    "在前面插入文件…": "Insert a file before…",
    "在后面插入文件…": "Insert a file after…",
    "在前面插入空白页": "Insert a blank page before",
    "在后面插入空白页": "Insert a blank page after",
    "移到最前": "Move to the front",
    "移到最后": "Move to the end",
    "全选": "Select all",
    "移动页面": "Move pages",
    "已设置密码，保存文件后生效。\n现在保存吗？": "Password set. It takes effect when the file is saved.\nSave now?",
    "已移除密码，保存文件后生效。\n现在保存吗？": "Password removed. This takes effect when the file is saved.\nSave now?",
    "请保存为另一个文件名，不要覆盖当前文档。": "Please save under another file name, not over the open document.",
    "压缩完成：{before} → {after}": "Compressed: {before} → {after}",
    "（减小 {pct}%）": " ({pct}% smaller)",
    "（这个文件已经很紧凑，几乎没有可压缩的空间）": " (this file is already compact; there is almost nothing left to save)",
    "打开所在文件夹吗？": "Open the folder it is in?",
    "正在导出图片…": "Exporting images…",
    "导出图片": "Export images",
    "已导出 {n} 张图片。\n{folder}\n\n打开这个文件夹吗？": "{n} image(s) exported.\n{folder}\n\nOpen this folder?",
    "导出文字": "Export text",
    "已导出，但这个文件里没有可提取的文字（可能是扫描件）。":
        "Exported, but this file has no text that can be extracted (it may be a scan).",
    "文字已导出：{path}": "Text exported: {path}",

    # ---- settings ----
    "界面语言": "Language",
    "点“确定”后整个界面立即切换，正在编辑的文档和撤销记录都会保留。":
        "The whole interface switches as soon as you click OK. The document you are editing and its undo steps are kept.",
    "数据文件夹": "Data folder",
    "设置和保存的签名都放在这里，换电脑时把它一起拷走即可。":
        "Settings and saved signatures are kept here. Copy it along when you move to another PC.",
    "打开文件夹": "Open folder",

    # ---- which pages ----
    "全部页面（共 {n} 页）": "All pages ({n})",
    "当前页（第 {n} 页）": "Current page ({n})",
    "左侧选中的 {n} 页": "The {n} pages selected on the left",
    "自定义范围": "Custom range",
    "例如 1-3,5,8-": "e.g. 1-3,5,8-",

    # ---- merge ----
    "合并 PDF / 图片转 PDF": "Merge PDF / images to PDF",
    "把要合并的 PDF 或图片加进来（也可以直接拖进窗口），按从上到下的顺序合成一个 PDF。"
    "“页码范围”留空表示整个文件，可填 <b>1-3,5,8-</b> 这样的写法。":
        "Add the PDFs or images to merge (or drop them onto this window); they are joined from top to bottom "
        "into one PDF. Leave \"Page range\" empty for the whole file, or type something like <b>1-3,5,8-</b>.",
    "文件名": "File name", "页数": "Pages", "页码范围（留空=全部）": "Page range (empty = all)", "所在文件夹": "Folder",
    "添加文件…": "Add files…", "上移": "Move up", "下移": "Move down", "按文件名排序": "Sort by name", "移除": "Remove",
    "用文件名生成书签（目录）": "Make bookmarks from the file names",
    "图片页面大小": "Page size for images",
    "与图片相同": "Same as the image",
    "A4 纸（居中）": "A4 (centred)",
    "保存为": "Save as",
    "开始合并": "Merge",
    "选择要合并的文件": "Choose the files to merge",
    "共 {n} 个文件，{pages} 页": "{n} files, {pages} pages",
    "还没有添加文件": "No files added yet",
    "合并后保存为": "Save the merged file as",
    "请先选择合并后文件的保存位置。": "Choose where to save the merged file first.",
    "保存位置不能是正在合并的源文件之一，请换一个文件名。":
        "The result cannot be saved over one of the files being merged. Please pick another file name.",
    "{name} 已存在，要覆盖吗？": "{name} already exists. Replace it?",
    "正在合并…": "Merging…",
    "合并完成，共 {n} 页。\n{out}\n\n现在打开合并后的文件吗？": "Merged: {n} pages.\n{out}\n\nOpen the merged file now?",
    "没有可合并的页面": "There are no pages to merge",

    # ---- split ----
    "要拆分的文件": "File to split",
    "选择其他文件…": "Choose another file…",
    "拆分方式": "How to split",
    "按页码范围": "By page ranges",
    "例如 1-3,4-10,11-   （每个逗号隔开的部分生成一个文件）": "e.g. 1-3,4-10,11-   (one file per comma-separated part)",
    "每隔固定页数": "Every N pages",
    " 页一个文件": " page(s) per file",
    "每页拆成一个文件": "One file per page",
    "按一级书签（章节）": "By top-level bookmarks (chapters)",
    "提取成一个文件": "Extract into one file",
    "例如 2,5-8   （把这些页按顺序放进同一个新文件）": "e.g. 2,5-8   (these pages, in this order, into one new file)",
    "保存到": "Save to",
    "文件夹": "Folder",
    "文件名前缀": "File name prefix",
    "开始拆分": "Split",
    "当前打开的文档：{name}": "The open document: {name}",
    "共 {n} 页": "{n} pages",
    "请先选择文件": "Choose a file first",
    "选择要拆分的 PDF": "Choose the PDF to split",
    "读取文件": "Read file",
    "保存到哪个文件夹": "Save to which folder",
    "请先选择要拆分的文件。": "Choose the file to split first.",
    "请选择保存的文件夹。": "Choose the folder to save to.",
    "这个文件没有书签，无法按章节拆分。请换一种拆分方式。":
        "This file has no bookmarks, so it cannot be split by chapter. Please choose another way.",
    "请填写要提取的页码。": "Enter the pages to extract.",
    "将生成 {n} 个文件，继续吗？": "This will create {n} files. Continue?",
    "正在拆分…": "Splitting…",
    "拆分完成，生成了 {n} 个文件。\n{folder}\n\n打开这个文件夹吗？": "Split into {n} files.\n{folder}\n\nOpen this folder?",

    # ---- watermark and page numbers ----
    "添加水印": "Add watermark",
    "水印文字": "Watermark text",
    "不透明度": "Opacity",
    "倾斜角度": "Angle",
    "铺满整页（重复平铺）": "Repeat across the whole page",
    "应用到": "Apply to",
    "请输入水印文字。": "Enter the watermark text.",
    "添加页码": "Add page numbers",
    "样式": "Style",
    "{n} 代表页码，{total} 代表总页数，可以自己改写":
        "{n} is the page number and {total} the number of pages; edit it as you like",
    "位置": "Position",
    "页脚居中": "Footer, centre", "页脚靠右": "Footer, right", "页脚靠左": "Footer, left",
    "页眉居中": "Header, centre", "页眉靠右": "Header, right", "页眉靠左": "Header, left",
    "起始页码": "Start at",
    "距页边": "Distance from edge",
    "样式里需要包含 {n}（代表页码）。": "The style must contain {n} (the page number).",

    # ---- password ----
    "密码保护": "Password protection",
    "当前状态：<b>已设置密码</b>": "Status: <b>password set</b>",
    "当前状态：未加密": "Status: not encrypted",
    "打开密码": "Password to open",
    "再输一次": "Type it again",
    "显示密码": "Show passwords",
    "可不填；填了则用它才能解除下面的限制": "Optional; if set, it is needed to lift the limits below",
    "权限密码": "Permissions password",
    "打开后允许": "Allowed after opening",
    "复制内容": "Copy content", "修改页面": "Change pages", "批注和填表": "Annotate and fill forms",
    "密码在“保存”时写入文件（AES-256 加密）。请牢记密码，忘记后无法找回。":
        "The password is written into the file when you save (AES-256). Remember it: "
        "a forgotten password cannot be recovered.",
    "移除密码": "Remove password",
    "设置密码": "Set password",
    "请输入密码。": "Enter a password.",
    "两次输入的打开密码不一样。": "The two passwords to open do not match.",

    # ---- compress ----
    "压缩 PDF": "Compress PDF",
    "当前文档大小约 <b>{size}</b>。压缩结果另存为新文件，不改动当前文档。":
        "The document is about <b>{size}</b> now. The result is saved as a new file; the open document is not changed.",
    "压缩程度": "Compression level",
    "{name}　—　{tip}": "{name}  —  {tip}",
    "无损整理": "Lossless clean-up",
    "不改图片，只清理冗余数据，画质完全不变": "images untouched, only redundant data removed; quality unchanged",
    "高质量": "High quality",
    "图片降到 200 DPI，适合打印": "images down to 200 DPI, good for printing",
    "均衡（推荐）": "Balanced (recommended)",
    "图片降到 150 DPI，适合屏幕阅读和邮件发送": "images down to 150 DPI, good for screens and e-mail",
    "最小体积": "Smallest file",
    "图片降到 96 DPI，文件最小，图片会变模糊": "images down to 96 DPI; smallest file, images get blurry",
    "压缩后保存为": "Save the compressed file as",
    "开始压缩": "Compress",
    "请选择保存位置。": "Choose where to save.",

    # ---- export images ----
    "导出为图片": "Export as images",
    "PNG（清晰，文件较大）": "PNG (sharp, larger files)",
    "JPG（文件较小）": "JPG (smaller files)",
    "格式": "Format",
    "清晰度": "Resolution",
    "（{tip}）": " ({tip})",
    "屏幕": "screen", "常用": "standard", "超清": "extra sharp",

    # ---- edit text ----
    "把这一行文字改成（清空则删除这一行）：": "Change this line to (leave empty to delete the line):",
    "加粗": "Bold",
    "原字体：{font}。原文件的字体通常不完整，新文字会改用上面选的字体，"
    "外观可能与周围略有差别；改后文字变长时不会自动换行。":
        "Original font: {font}. The fonts inside a PDF are usually incomplete, so the new text uses the font "
        "chosen above and may look slightly different from the text around it. Longer text is not wrapped "
        "onto a new line.",
    "未知": "unknown",
    "修改": "Change",

    # ---- signature ----
    "<b>我的签名</b>（双击可直接使用）": "<b>My signatures</b> (double-click to use)",
    "使用这个签名": "Use this signature",
    "手写签名": "Draw",
    "从图片/照片导入": "From a picture or photo",
    "输入姓名生成": "Type a name",
    "删除这个签名？": "Delete this signature?",
    "还没有可保存的签名。": "There is no signature to save yet.",
    "保存到签名库": "Save to my signatures",
    "保存并使用": "Save and use",
    "按住鼠标左键在这里签名": "Hold the left mouse button and sign here",
    "墨水": "Ink",
    "粗细": "Thickness",
    "撤销一笔": "Undo stroke",
    "在白纸上签名后拍照或扫描，选择图片后会自动去掉纸张背景，只保留笔迹。":
        "Sign on white paper, then photograph or scan it. After you choose the picture the paper background "
        "is removed and only the ink is kept.",
    "尚未选择图片": "No picture chosen yet",
    "选择图片…": "Choose picture…",
    "去背景强度": "Background removal",
    "选择签名图片": "Choose the signature picture",
    "没有识别到笔迹，请调低“去背景强度”": "No ink found; lower \"Background removal\"",
    "输入姓名": "Type your name",
}
