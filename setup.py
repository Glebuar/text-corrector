from cx_Freeze import setup, Executable

executables = [
    Executable(
        script="main.py",
        base="Win32GUI",
        target_name="TextCorrector.exe",
        shortcut_name="Text Corrector",
        icon="icon.ico"
    )
]

setup(
    name="TextCorrector",
    version="1.0",
    options={"build_exe": {"include_files": [('icon.ico', 'icon.ico')], "includes": ["pydantic.deprecated.decorator"]}},
    executables=executables
)