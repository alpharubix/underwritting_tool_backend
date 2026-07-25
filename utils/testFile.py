import zipfile
from pathlib import Path

path = Path(r"controller\lender_eligibility\seed\data_inputs_lender.xlsx")

print("Exists:", path.exists())
print("Is ZIP:", zipfile.is_zipfile(path))

try:
    with zipfile.ZipFile(path, "r") as z:
        print("ZIP opened successfully")
        print("First 10 entries:")
        print(z.namelist()[:10])
except Exception as e:
    print(type(e).__name__, e)