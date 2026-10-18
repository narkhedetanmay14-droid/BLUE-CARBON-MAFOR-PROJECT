from pathlib import Path
from datetime import datetime
import shutil
root=Path(__file__).resolve().parents[1]
source=root/"database"
target=root/"backups"/datetime.now().strftime("%Y%m%d-%H%M%S")
target.parent.mkdir(exist_ok=True)
shutil.copytree(source,target)
print(f"Backup created: {target}")
