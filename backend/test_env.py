"""
Verify that backend/.env is found and parsed correctly.

Run:  python test_env.py

Prints only the first 20 characters of DATABASE_URL, so the password is never
exposed. Exit code 0 = loaded correctly, 1 = problem (with the fix printed).
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv is not installed - activate the venv first:")
    print("    .\\.venv\\Scripts\\Activate.ps1")
    sys.exit(1)

ENV_PATH = Path(__file__).resolve().parent / ".env"


def fail(message, *hints):
    print("\nRESULT: FAIL - " + message)
    for hint in hints:
        print("  " + hint)
    return 1


def main():
    print("looking for:", ENV_PATH)
    print("exists     :", ENV_PATH.exists())

    if not ENV_PATH.exists():
        for wrong in (".env.txt", "env.txt", ".env.bak", ".env .txt"):
            if ENV_PATH.with_name(wrong).exists():
                return fail(
                    "found '{}' but python-dotenv only reads '.env'".format(wrong),
                    'fix: Rename-Item "{}" .env'.format(wrong),
                )
        return fail("no .env file exists at {}".format(ENV_PATH),
                    "fix: create the file, one KEY=value per line")

    # A UTF-8 BOM silently corrupts the first key into '\ufeffDATABASE_URL'.
    if ENV_PATH.read_bytes().startswith(b"\xef\xbb\xbf"):
        return fail("the file starts with a UTF-8 BOM, so the first key is corrupted",
                    "fix: open .env in VS Code and press Save (no BOM)")

    print("\nlines as dotenv parses them:")
    for number, line in enumerate(ENV_PATH.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            print("  line {}: NO '=' SIGN - dotenv ignores this line".format(number))
            continue
        name, value = stripped.split("=", 1)
        print("  line {}: key='{}'  empty-value={}  starts-with-quote={}".format(
            number, name, not value.strip(), value.strip()[:1] in ('"', "'")))

    load_dotenv(ENV_PATH, override=True)

    url = os.getenv("DATABASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")

    print("\nDATABASE_URL   -> " + (url[:20] + "..." if url else "None"))
    print("OPENAI_API_KEY -> " + ("set ({} chars)".format(len(api_key)) if api_key else "None"))

    if not url:
        return fail("DATABASE_URL is None",
                    "most likely cause: the line is missing the 'DATABASE_URL=' prefix",
                    "correct form:  DATABASE_URL=postgresql://user:pass@host/db?sslmode=require")
    if not api_key:
        return fail("OPENAI_API_KEY is None",
                    "correct form:  OPENAI_API_KEY=sk-proj-...")

    if "YOUR_REAL_PASSWORD_HERE" in url or "YOUR_REAL_KEY_HERE" in api_key:
        return fail("placeholders are still in place - paste your real values",
                    "line 1: replace YOUR_REAL_PASSWORD_HERE",
                    "line 2: replace YOUR_REAL_KEY_HERE")

    print("\nRESULT: PASS - backend/.env loaded, both keys are set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
