# Day Name Utility

Small Python utility that prints the weekday name for a given date or for today.

Usage (PowerShell):

```powershell
python .\dayname.py            # prints today's weekday name
python .\dayname.py -d 2025-12-08
python .\dayname.py --date 08-12-2025
```

Notes:
- Accepts: `YYYY-MM-DD`, `YYYY/MM/DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, `YYYYMMDD`.
- If `--date` is omitted or set to `today`, the script prints today's weekday name.

Want next? I can add unit tests, package this as a module, or commit the changes.
