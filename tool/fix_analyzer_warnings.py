from pathlib import Path
import re

path = Path("lib/main.dart")
text = path.read_text()


def replace_one(old: str, new: str, already_fixed: str, label: str) -> None:
    global text
    if old in text:
        text = text.replace(old, new, 1)
        print(f"fixed: {label}")
    elif already_fixed in text:
        print(f"already fixed: {label}")
    else:
        raise SystemExit(f"Could not locate expected source for: {label}")


media_name = "return 'Camera_$stamp$extension';"
media_name_braced = r"return 'Camera_${stamp}${extension}';"
media_name_concat = "return 'Camera_' + stamp + extension;"
if media_name_concat in text:
    text = text.replace(media_name_concat, media_name, 1)
    print("fixed: camera media filename interpolation")
elif media_name_braced in text:
    text = text.replace(media_name_braced, media_name, 1)
    print("fixed: remove unnecessary interpolation braces")
elif media_name not in text:
    raise SystemExit("Could not locate camera media filename expression")

timer_name = "return '$minutes:$seconds';"
timer_name_concat = "return minutes + ':' + seconds;"
if timer_name_concat in text:
    text = text.replace(timer_name_concat, timer_name, 1)
    print("fixed: recording timer interpolation")
elif timer_name not in text:
    raise SystemExit("Could not locate recording timer expression")

replace_one(
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
replace_one(
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

text, brace_count = re.subn(
    r"^(\s*)if \(mounted\) setState\(\(\) => (.+)\);$",
    lambda match: (
        f"{match.group(1)}if (mounted) {{\n"
        f"{match.group(1)}  setState(() => {match.group(2)});\n"
        f"{match.group(1)}}}"
    ),
    text,
    flags=re.MULTILINE,
)
path.write_text(text)
print(f"wrapped mounted setState statements: {brace_count}")

for stale in (
    media_name_concat,
    media_name_braced,
    timer_name_concat,
    "if (saved == null)",
):
    if stale in text:
        raise SystemExit(f"Analyzer fix incomplete; stale pattern remains: {stale}")

print("Dart analyzer fix verification passed")
