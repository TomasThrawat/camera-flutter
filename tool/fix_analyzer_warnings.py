from pathlib import Path
import re

path = Path("lib/main.dart")
text = path.read_text()

def replace_block(old, new, already_fixed, label):
    global text
    if old in text:
        text = text.replace(old, new, 1)
        print("fixed:", label)
    elif already_fixed in text:
        print("already fixed:", label)
    else:
        raise SystemExit("Could not locate expected source for: " + label)

replace_block(
    "return 'Camera_' + stamp + extension;",
    "return 'Camera_" + chr(36) + "{stamp}" + chr(36) + "{extension}';",
    "return 'Camera_" + chr(36) + "{stamp}" + chr(36) + "{extension}';",
    "camera media filename interpolation",
)
replace_block(
    "return minutes + ':' + seconds;",
    "return '" + chr(36) + "minutes:" + chr(36) + "seconds';",
    "return '" + chr(36) + "minutes:" + chr(36) + "seconds';",
    "recording timer interpolation",
)
replace_block(
    """      final saved = await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
      );
      if (saved == null) {
        _message('Photo captured, but could not save it to Gallery.');
        return;
      }
""",
    """      await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
      );
""",
    "await PhotoManager.editor.saveImageWithPath(",
    "remove impossible nullable result check for saved photo",
)
replace_block(
    """      final saved = await PhotoManager.editor.saveVideo(
        File(video.path),
        title: _mediaTitle('.mp4'),
      );
      if (saved == null) {
        _message('Video recorded, but could not save it to Gallery.');
        return;
      }
""",
    """      await PhotoManager.editor.saveVideo(
        File(video.path),
        title: _mediaTitle('.mp4'),
      );
""",
    "await PhotoManager.editor.saveVideo(",
    "remove impossible nullable result check for saved video",
)

text, braces_added = re.subn(
    r"^(\s*)if \(mounted\) setState\(\(\) => (.+)\);$",
    lambda m: (
        f"{m.group(1)}if (mounted) {{\n"
        f"{m.group(1)}  setState(() => {m.group(2)});\n"
        f"{m.group(1)}}}"
    ),
    text,
    flags=re.MULTILINE,
)
path.write_text(text)
print("mounted setState statements wrapped:", braces_added)

invalid_patterns = [
    "return 'Camera_' + stamp + extension;",
    "return minutes + ':' + seconds;",
    "if (saved == null)",
]
for pattern in invalid_patterns:
    if pattern in text:
        raise SystemExit("Analyzer fix incomplete; old pattern remains: " + pattern)
print("analyzer fix checks passed")
