"""The Help window's text, one whole page per language (kept out of the tr() table because it is long)."""

HELP = {
    "zh": """<h3>{name} {ver}</h3>
<p><b>页面整理</b>：左侧缩略图可多选（Ctrl / Shift），拖动调整顺序，右键或用上方按钮旋转、删除、提取、插入。</p>
<p><b>加文字 / 图片 / 签名</b>：放到页面上后可以拖动（文字拖左上角的蓝色手柄），图片和签名拖四角缩放；
点击空白处确认，Esc 取消。</p>
<p><b>改文字</b>：鼠标移到文字上会出现蓝框，点击即可修改。扫描件里的字是图片，请用“擦除”后再“加文字”。</p>
<p><b>擦除 / 涂黑</b>：会真正删除框内的内容，不只是盖住。</p>
<p><b>快捷键</b>：Ctrl+O 打开　Ctrl+S 保存　Ctrl+Shift+S 另存为　Ctrl+Z 撤销　Ctrl+Y 重做　Ctrl+P 打印<br>
Ctrl+滚轮 缩放　Ctrl+0 适合宽度　Delete 删除选中的页面</p>
<p><b>界面语言</b>：在右上角的“设置”里切换中文和英文。</p>
<p>所有处理都在本机完成，文件不会上传。</p>""",

    "en": """<h3>{name} {ver}</h3>
<p><b>Organising pages</b>: select several thumbnails on the left (Ctrl / Shift), drag them to reorder,
right-click or use the buttons above to rotate, delete, extract or insert.</p>
<p><b>Add text / Image / Signature</b>: once on the page it can be dragged (text by the blue handle at its
top left); images and signatures are resized by their corners. Click elsewhere to confirm, Esc to cancel.</p>
<p><b>Edit text</b>: a blue frame appears when the mouse is over text; click to change that line. Text in a
scan is a picture: use Erase, then Add text.</p>
<p><b>Erase / Redact</b>: the content inside the box is really removed, not just covered.</p>
<p><b>Shortcuts</b>: Ctrl+O open &nbsp; Ctrl+S save &nbsp; Ctrl+Shift+S save as &nbsp; Ctrl+Z undo &nbsp;
Ctrl+Y redo &nbsp; Ctrl+P print<br>
Ctrl+wheel zoom &nbsp; Ctrl+0 fit width &nbsp; Delete removes the selected pages</p>
<p><b>Language</b>: switch between Chinese and English under Settings, top right.</p>
<p>Everything is processed on this PC; no file is uploaded.</p>""",
}
